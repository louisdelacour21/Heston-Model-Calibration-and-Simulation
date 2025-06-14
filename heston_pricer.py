import QuantLib as ql
import numpy as np
import scipy.optimize as opt


class HestonPricer:
    """
    A comprehensive class for pricing autocallable structured products using the Heston stochastic volatility model.
    """

    def __init__(self, valuation_date, spot_price, strike_price, risk_free_rate, dividend_yield):
        """
        Initialize the Heston pricer with market data.

        Args:
            valuation_date: QuantLib Date object for valuation
            spot_price: Current underlying asset price
            strike_price: Strike price for the product
            risk_free_rate: Risk-free interest rate
            dividend_yield: Dividend yield of the underlying
        """
        self.valuation_date = valuation_date
        self.spot_price = spot_price
        self.strike_price = strike_price
        self.calendar = ql.TARGET()
        self.day_counter = ql.Actual360()

        # Set up QuantLib environment
        ql.Settings.instance().evaluationDate = valuation_date

        # Create yield curves
        self.risk_free_curve = ql.YieldTermStructureHandle(
            ql.FlatForward(valuation_date, risk_free_rate, self.day_counter)
        )
        self.dividend_curve = ql.YieldTermStructureHandle(
            ql.FlatForward(valuation_date, dividend_yield, self.day_counter)
        )

    def generate_paths(self, observation_dates, heston_process, num_paths):
        """
        Generate Monte Carlo paths using the Heston model.

        Args:
            observation_dates: List of dates for path observations
            heston_process: Calibrated Heston process
            num_paths: Number of Monte Carlo paths to generate

        Returns:
            Array of simulated paths
        """
        time_grid = np.array([
            self.day_counter.yearFraction(observation_dates[0], date)
            for date in observation_dates
        ])

        grid_steps = (time_grid.shape[0] - 1) * 2
        uniform_generator = ql.UniformRandomSequenceGenerator(
            grid_steps, ql.UniformRandomGenerator()
        )
        gaussian_generator = ql.GaussianRandomSequenceGenerator(uniform_generator)
        path_generator = ql.GaussianMultiPathGenerator(
            heston_process, time_grid, gaussian_generator, False
        )

        paths = np.zeros(shape=(num_paths, time_grid.shape[0]))

        for i in range(num_paths):
            multi_path = path_generator.next().value()
            paths[i, :] = np.array(list(multi_path[0]))

        return paths

    def calibrate_heston_model(self, market_data, initial_params, parameter_bounds, optimizer=opt.differential_evolution):
        """
        Calibrate the Heston model to market volatility data.

        Args:
            market_data: Dictionary with 'expiration_dates', 'strikes', and 'volatilities'
            initial_params: Initial guess for Heston parameters [v0, kappa, theta, sigma, rho]
            parameter_bounds: Bounds for optimization
            optimizer: Optimization algorithm to use

        Returns:
            Tuple of (calibrated_process, calibrated_model)
        """
        v0, kappa, theta, sigma, rho = initial_params

        # Create initial Heston process and model
        heston_process = ql.HestonProcess(
            self.risk_free_curve, self.dividend_curve,
            ql.QuoteHandle(ql.SimpleQuote(self.spot_price)),
            v0, kappa, theta, sigma, rho
        )
        heston_model = ql.HestonModel(heston_process)
        pricing_engine = ql.AnalyticHestonEngine(heston_model)

        # Create calibration helpers
        calibration_helpers = []

        for i, expiration_date in enumerate(market_data['expiration_dates']):
            for j, strike in enumerate(market_data['strikes']):
                days_to_expiry = expiration_date - self.valuation_date
                period = ql.Period(days_to_expiry, ql.Days)
                market_vol = market_data['volatilities'][i][j]

                helper = ql.HestonModelHelper(
                    period, self.calendar, self.spot_price, strike,
                    ql.QuoteHandle(ql.SimpleQuote(market_vol)),
                    self.risk_free_curve, self.dividend_curve
                )
                helper.setPricingEngine(pricing_engine)
                calibration_helpers.append(helper)

        def objective_function(params):
            """Objective function for calibration optimization."""
            parameters = ql.Array(list(params))
            heston_model.setParams(parameters)
            errors = [helper.calibrationError() for helper in calibration_helpers]
            return np.sqrt(np.sum(np.abs(errors)))

        # Run optimization
        optimizer(objective_function, parameter_bounds)

        return heston_process, heston_model

    def price_autocallable_note(self, product_specs, heston_process, num_paths=10000):
        """
        Price an autocallable note using Monte Carlo simulation.

        Args:
            product_specs: Dictionary containing product specifications
            heston_process: Calibrated Heston process
            num_paths: Number of Monte Carlo paths

        Returns:
            Present value of the autocallable note
        """
        coupon_dates = product_specs['coupon_dates']
        notional = product_specs['notional']
        autocall_barrier = product_specs['autocall_barrier']
        coupon_barrier = product_specs['coupon_barrier']
        protection_barrier = product_specs['protection_barrier']
        coupon_rate = product_specs['coupon_rate']
        has_memory = product_specs['has_memory']
        past_fixings = product_specs.get('past_fixings', {})
        final_payoff_formula = product_specs.get('final_payoff_formula', lambda x: x / self.strike_price)

        # Check if product has already been called
        if self.valuation_date >= coupon_dates[-1]:
            return 0.0

        if self.valuation_date >= coupon_dates[0]:
            if max(past_fixings.values()) >= (autocall_barrier * self.strike_price):
                return 0.0

        # Set up observation dates
        future_dates = coupon_dates[coupon_dates > self.valuation_date]
        observation_dates = np.hstack((np.array([self.valuation_date]), future_dates))

        # Generate Monte Carlo paths
        paths = self.generate_paths(observation_dates, heston_process, num_paths)[:, 1:]

        # Include past fixings if any
        past_dates = coupon_dates[coupon_dates <= self.valuation_date]
        if past_dates.shape[0] > 0:
            past_fixings_array = np.array([past_fixings[date] for date in past_dates])
            past_fixings_array = np.tile(past_fixings_array, (paths.shape[0], 1))
            paths = np.hstack((past_fixings_array, paths))

        # Calculate payoffs for each path
        payoff_pvs = []
        expiration_date = coupon_dates[-1]
        memory_factor = int(has_memory)

        for path in paths:
            total_pv = 0.0
            unpaid_coupons = 0
            has_been_called = False

            for observation_date, underlying_level in zip(coupon_dates, (path / self.strike_price)):
                if has_been_called:
                    break

                payoff = 0.0

                # Final observation date logic
                if observation_date == expiration_date:
                    if underlying_level >= coupon_barrier:
                        payoff = notional * (1 + (coupon_rate * (1 + unpaid_coupons * memory_factor)))
                    elif underlying_level >= protection_barrier:
                        payoff = notional
                    else:
                        actual_level = underlying_level * self.strike_price
                        payoff = notional * final_payoff_formula(actual_level)

                # Intermediate observation dates
                else:
                    if underlying_level >= autocall_barrier:
                        payoff = notional * (1 + (coupon_rate * (1 + unpaid_coupons * memory_factor)))
                        has_been_called = True
                    elif underlying_level >= coupon_barrier:
                        payoff = notional * (coupon_rate * (1 + unpaid_coupons * memory_factor))
                        unpaid_coupons = 0
                    else:
                        unpaid_coupons += 1

                # Discount payoff to present value
                if observation_date > self.valuation_date:
                    discount_factor = self.risk_free_curve.discount(observation_date)
                    total_pv += payoff * discount_factor

            payoff_pvs.append(total_pv)

        return np.mean(np.array(payoff_pvs))


def main_example():
    """
    Example usage of the HestonPricer class for pricing two different autocallable products.
    """
    print("=== Heston Model Autocallable Notes Pricing Example ===\n")

    # Market setup
    valuation_date = ql.Date(20, 7, 2024)
    spot_price = 79.98
    strike_price = 79.98
    risk_free_rate = 0.02
    dividend_yield = 0.028

    # Initialize pricer
    pricer = HestonPricer(valuation_date, spot_price, strike_price, risk_free_rate, dividend_yield)
    print(f"Valuation Date: {valuation_date}")
    print(f"Spot Price: ${spot_price}")
    print(f"Strike Price: ${strike_price}")
    print(f"Risk-free Rate: {risk_free_rate*100:.1f}%")
    print(f"Dividend Yield: {dividend_yield*100:.1f}%\n")

    # Market volatility data for calibration
    expiration_dates = [
        ql.Date(20, 1, 2025), ql.Date(20, 7, 2025),
        ql.Date(20, 1, 2026), ql.Date(20, 7, 2026), ql.Date(20, 1, 2027)
    ]

    strike_levels = [strike_price * x for x in [0.7, 0.8, 0.9, 1.0, 1.1]]
    implied_volatilities = [[0.3565 for _ in strike_levels] for _ in expiration_dates]

    market_data = {
        'expiration_dates': expiration_dates,
        'strikes': strike_levels,
        'volatilities': implied_volatilities
    }

    # Initial Heston parameters and bounds
    initial_heston_params = [0.01, 0.5, 0.01, 0.2, -0.5]  # [v0, kappa, theta, sigma, rho]
    parameter_bounds = [(0.01, 1.0), (0.01, 10.0), (0.01, 1.0), (-1.0, 1.0), (0.01, 1.0)]

    print("Calibrating Heston model to market data...")
    heston_process, heston_model = pricer.calibrate_heston_model(
        market_data, initial_heston_params, parameter_bounds
    )
    print(f"Calibrated Heston parameters: {heston_model.params()}\n")

    # Product specifications
    notional = 1000000.0
    coupon_rate = 0.05
    protection_barrier = 0.6
    has_memory = True

    # Generate coupon dates (semi-annual for 5 years)
    start_date = valuation_date
    first_coupon = pricer.calendar.advance(start_date, ql.Period(6, ql.Months))
    last_coupon = pricer.calendar.advance(start_date, ql.Period(5, ql.Years))
    coupon_schedule = ql.Schedule(
        first_coupon, last_coupon, ql.Period(ql.Semiannual),
        pricer.calendar, ql.ModifiedFollowing, ql.ModifiedFollowing,
        ql.DateGeneration.Forward, False
    )
    coupon_dates = np.array(list(coupon_schedule))

    print(f"Product Details:")
    print(f"Notional: ${notional:,.0f}")
    print(f"Coupon Rate: {coupon_rate*100:.1f}%")
    print(f"Protection Barrier: {protection_barrier*100:.0f}%")
    print(f"Memory Feature: {'Yes' if has_memory else 'No'}")
    print(f"Number of Observations: {len(coupon_dates)}\n")

    # Product 1: Athena-style (autocall and coupon at 100%)
    athena_specs = {
        'coupon_dates': coupon_dates,
        'notional': notional,
        'autocall_barrier': 1.0,
        'coupon_barrier': 1.0,
        'protection_barrier': protection_barrier,
        'coupon_rate': coupon_rate,
        'has_memory': has_memory,
        'past_fixings': {},
        'final_payoff_formula': lambda x: x / strike_price
    }

    print("Pricing Athena-style Autocallable Note...")
    athena_pv = pricer.price_autocallable_note(athena_specs, heston_process, num_paths=10000)

    # Product 2: Phoenix-style (autocall at 100%, coupon at 70%)
    phoenix_specs = {
        'coupon_dates': coupon_dates,
        'notional': notional,
        'autocall_barrier': 1.0,
        'coupon_barrier': 0.7,
        'protection_barrier': protection_barrier,
        'coupon_rate': coupon_rate,
        'has_memory': has_memory,
        'past_fixings': {},
        'final_payoff_formula': lambda x: x / strike_price
    }

    print("Pricing Phoenix-style Autocallable Note...")
    phoenix_pv = pricer.price_autocallable_note(phoenix_specs, heston_process, num_paths=10000)

    # Calculate purchase percentages (discounted back)
    discount_rate = 0.045
    time_to_maturity = 5

    athena_discounted = athena_pv / ((1 + discount_rate) ** time_to_maturity)
    phoenix_discounted = phoenix_pv / ((1 + discount_rate) ** time_to_maturity)

    athena_percentage = (athena_discounted / notional) * 100
    phoenix_percentage = (phoenix_discounted / notional) * 100

    print(f"\n=== PRICING RESULTS ===")
    print(f"Athena Note:")
    print(f"  Present Value: ${athena_pv:,.0f}")
    print(f"  Purchase Percentage: {athena_percentage:.2f}%")
    print(f"\nPhoenix Note:")
    print(f"  Present Value: ${phoenix_pv:,.0f}")
    print(f"  Purchase Percentage: {phoenix_percentage:.2f}%")

    print(f"\n=== PRODUCT COMPARISON ===")
    print(f"Athena: Autocall={athena_specs['autocall_barrier']*100:.0f}%, Coupon={athena_specs['coupon_barrier']*100:.0f}%")
    print(f"Phoenix: Autocall={phoenix_specs['autocall_barrier']*100:.0f}%, Coupon={phoenix_specs['coupon_barrier']*100:.0f}%")
    print(f"Phoenix offers more frequent coupons but same autocall protection.")


if __name__ == "__main__":
    main_example()
