# Heston Autocallable Notes Pricer

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![QuantLib](https://img.shields.io/badge/QuantLib-1.25+-green.svg)](https://www.quantlib.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive pricing engine for autocallable structured products using the Heston stochastic volatility model with Monte Carlo simulation.

## Overview

This project implements a robust `HestonPricer` class that enables pricing of complex autocallable notes by:
- Calibrating the Heston model to market implied volatility data
- Generating Monte Carlo paths with stochastic volatility
- Pricing various autocallable structures (Athena, Phoenix, etc.)
- Supporting advanced features like memory effect, protection barriers, and conditional coupons

## Features

- **Heston Model Calibration**: Automatic calibration to market implied volatility surfaces
- **Monte Carlo Simulation**: Efficient path generation with the Heston stochastic volatility process
- **Flexible Product Structures**: Support for various autocallable note types
- **Advanced Features**: Memory effect, protection barriers, conditional coupons, custom payoff formulas
- **Past Fixings Support**: Handle products that are already live in the market
- **Professional Implementation**: Built on QuantLib for production-grade accuracy

## Quick Start

### Installation

```bash
pip install quantlib-python numpy scipy
```

### Basic Usage

```python
import QuantLib as ql
import numpy as np
from heston_pricer import HestonPricer

# Market setup
valuation_date = ql.Date(20, 7, 2024)
spot_price = 79.98
strike_price = 79.98
risk_free_rate = 0.02
dividend_yield = 0.028

# Initialize pricer
pricer = HestonPricer(valuation_date, spot_price, strike_price, 
                     risk_free_rate, dividend_yield)

# Market data for calibration
market_data = {
    'expiration_dates': [ql.Date(20, 1, 2025), ql.Date(20, 7, 2025)],
    'strikes': [71.98, 79.98, 87.98],
    'volatilities': [[0.35, 0.30, 0.28], [0.38, 0.33, 0.31]]
}

# Calibrate Heston model
initial_params = [0.01, 0.5, 0.01, 0.2, -0.5]  # [v0, kappa, theta, sigma, rho]
bounds = [(0.01, 1.0), (0.01, 10.0), (0.01, 1.0), (-1.0, 1.0), (0.01, 1.0)]

heston_process, heston_model = pricer.calibrate_heston_model(
    market_data, initial_params, bounds
)

# Product specifications
product_specs = {
    'coupon_dates': coupon_dates,
    'notional': 1000000.0,
    'autocall_barrier': 1.0,        # 100% of strike
    'coupon_barrier': 0.7,          # 70% of strike  
    'protection_barrier': 0.6,      # 60% of strike
    'coupon_rate': 0.05,            # 5% coupon
    'has_memory': True,             # Memory feature enabled
    'past_fixings': {},
    'final_payoff_formula': lambda x: x / strike_price
}

# Price the note
price = pricer.price_autocallable_note(product_specs, heston_process, num_paths=10000)
print(f"Note Price: ${price:,.0f}")
```

## Supported Product Types

### Athena Notes
- Autocall and coupon triggered at the same level (typically 100%)
- Conservative structure with less frequent but more predictable payments

### Phoenix Notes  
- Autocall at one level (e.g., 100%)
- Coupon at a lower level (e.g., 70%)
- Higher probability of receiving coupons throughout the life

### Key Features
- **Memory Effect**: Accumulates unpaid coupons when barriers aren't breached
- **Protection Barrier**: Provides partial capital protection at maturity
- **Flexible Observation**: Quarterly, semi-annual, or custom observation schedules

## Architecture

### HestonPricer Class

#### Core Methods

```python
class HestonPricer:
    def __init__(self, valuation_date, spot_price, strike_price, risk_free_rate, dividend_yield)
    def calibrate_heston_model(self, market_data, initial_params, parameter_bounds, optimizer)
    def generate_paths(self, observation_dates, heston_process, num_paths)
    def price_autocallable_note(self, product_specs, heston_process, num_paths=10000)
```

#### Heston Model Parameters

- **v0**: Initial instantaneous volatility
- **kappa**: Mean reversion speed
- **theta**: Long-term volatility level
- **sigma**: Volatility of volatility
- **rho**: Correlation between price and volatility processes

## ⚙️ Configuration

### Product Specification Schema

```python
product_specs = {
    'coupon_dates': np.array([...]),         # Array of observation dates
    'notional': 1000000.0,                   # Notional amount
    'autocall_barrier': 1.0,                 # Autocall barrier (% of strike)
    'coupon_barrier': 0.7,                   # Coupon barrier (% of strike)
    'protection_barrier': 0.6,               # Protection barrier (% of strike)
    'coupon_rate': 0.05,                     # Coupon rate
    'has_memory': True,                      # Enable memory feature
    'past_fixings': {},                      # Past fixings for live products
    'final_payoff_formula': lambda x: x/K   # Custom final payoff function
}
```

### Custom Optimization

```python
from scipy.optimize import minimize

# Use different optimizer
heston_process, heston_model = pricer.calibrate_heston_model(
    market_data, initial_params, bounds, optimizer=minimize
)
```

### Custom Payoff Functions

```python
# Example: Capped upside participation
def capped_payoff(final_level):
    return min(final_level / strike_price, 1.2)  # Cap at 120%

# Example: Leveraged participation
def leveraged_payoff(final_level):
    participation = 1.5  # 150% participation
    return (final_level / strike_price) * participation

product_specs['final_payoff_formula'] = capped_payoff
```

## Example Output

```
=== Heston Model Autocallable Notes Pricing Example ===

Valuation Date: July 20th, 2024
Spot Price: $79.98
Strike Price: $79.98
Risk-free Rate: 2.0%
Dividend Yield: 2.8%

Calibrating Heston model to market data...
Calibrated Heston parameters: [0.0156, 2.1432, 0.0234, 0.3891, -0.4567]

Product Details:
Notional: $1,000,000
Coupon Rate: 5.0%
Protection Barrier: 60%
Memory Feature: Yes
Number of Observations: 10

=== PRICING RESULTS ===
Athena Note:
  Present Value: $887,342
  Purchase Percentage: 88.73%

Phoenix Note:
  Present Value: $923,156  
  Purchase Percentage: 92.32%

=== PRODUCT COMPARISON ===
Athena: Autocall=100%, Coupon=100%
Phoenix: Autocall=100%, Coupon=70%
Phoenix offers more frequent coupons but same autocall protection.
```

## Advanced Usage

### Handling Live Products

```python
# For products already in the market with past observations
past_fixings = {
    ql.Date(20, 1, 2024): 75.50,  # Historical fixing
    ql.Date(20, 4, 2024): 82.30   # Historical fixing
}

product_specs['past_fixings'] = past_fixings
```

### Performance Tuning

```python
# Balance accuracy vs speed
num_paths = 50000   # Higher for final pricing
num_paths = 5000    # Lower for scenario analysis

# Multi-threading consideration
# QuantLib's random number generation is thread-safe
# Consider parallel pricing for portfolio-level calculations
```

## Requirements

- Python 3.7+
- quantlib-python >= 1.25
- numpy >= 1.19.0
- scipy >= 1.5.0

##  Important Notes

- **Monte Carlo Convergence**: Increase `num_paths` for higher accuracy (computation time trade-off)
- **Model Calibration**: Quality depends on the provided implied volatility surface
- **Date Conventions**: Uses TARGET calendar for consistency with QuantLib
- **Validation**: Always validate results against market benchmarks before production use

## Testing

```python
# Run the main example
python heston_pricer.py

# Expected output: Pricing results for both Athena and Phoenix structures
```

## References

- Heston, S. L. (1993). "A Closed-Form Solution for Options with Stochastic Volatility"
- Gatheral, J. (2006). "The Volatility Surface: A Practitioner's Guide"
- QuantLib Documentation: https://www.quantlib.org/

## Contributing

Contributions are welcome! Please feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add unit tests for new features
- Update documentation for API changes
- Ensure backward compatibility when possible

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [QuantLib](https://www.quantlib.org/) - The premier open-source library for quantitative finance
- Inspired by industry-standard structured products pricing methodologies
- Thanks to the open-source quantitative finance community

## Support

-  **Bug Reports**: Open an issue with detailed reproduction steps
-  **Feature Requests**: Open an issue with your enhancement proposal  
-  **Documentation**: Contributions to improve documentation are always welcome
-  **Questions**: Use GitHub Discussions for general questions

---

 **Star this repository if you find it useful!**

*Professional-grade structured products pricing with Python and QuantLib*
