import QuantLib as ql
import numpy as np
import scipy.optimize as opt
import json

def load_market_data(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)
    return data

def calibrate_heston_model(valuation_date, calendar, spot, curve_handle, dividend_handle,
                            initial_params, expirations, strikes, market_vols,
                            optimizer=opt.differential_evolution):
    """
    Calibrates the Heston model using market data.

    Parameters:
    - valuation_date: QuantLib.Date
    - calendar: QuantLib.Calendar
    - spot: float
    - curve_handle: QuantLib.YieldTermStructureHandle
    - dividend_handle: QuantLib.YieldTermStructureHandle
    - initial_params: tuple of (v0, kappa, theta, sigma, rho)
    - expirations: list of QuantLib.Date
    - strikes: list of float
    - market_vols: 2D list of float
    - optimizer: callable, default is scipy.optimize.differential_evolution

    Returns:
    - Calibrated QuantLib.HestonModel
    - List of calibrated parameters
    """
    ql.Settings.instance().evaluationDate = valuation_date

    v0, kappa, theta, sigma, rho = initial_params

    process = ql.HestonProcess(curve_handle, dividend_handle,
                               ql.QuoteHandle(ql.SimpleQuote(spot)),
                               v0, kappa, theta, sigma, rho)
    model = ql.HestonModel(process)
    engine = ql.AnalyticHestonEngine(model)

    helpers = []
    for i, expiry in enumerate(expirations):
        maturity = ql.Period((expiry - valuation_date), ql.Days)
        for j, strike in enumerate(strikes):
            vol = market_vols[i][j]
            helper = ql.HestonModelHelper(maturity, calendar, spot, strike,
                                          ql.QuoteHandle(ql.SimpleQuote(vol)),
                                          curve_handle, dividend_handle)
            helper.setPricingEngine(engine)
            helpers.append(helper)

    def cost_function(params):
        model.setParams(ql.Array(params))
        errors = [h.calibrationError() for h in helpers]
        return np.sqrt(np.sum(np.square(errors)))

    bounds = [(0.001, 2.0), (0.01, 5.0), (0.001, 1.0), (0.01, 1.0), (-0.99, 0.99)]
    result = optimizer(cost_function, bounds)
    calibrated_params = result.x

    model.setParams(ql.Array(calibrated_params))

    return model, calibrated_params
