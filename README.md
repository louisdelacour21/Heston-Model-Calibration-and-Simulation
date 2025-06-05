# Heston Model Calibration and Simulation

This repository is dedicated to exploring the Heston stochastic volatility model, with clean and modular Python code focused on calibration, simulation, and visualization. Only the Heston model is covered here. Other models like Black-Scholes or SABR may be explored in future repositories.

## Project Structure

```
.
├── main.py                    # Main script for calibration and path generation
├── src
│   ├── calibration.py         # Calibration of the Heston model
│   └── simulation.py          # Simulation of asset paths using Heston
├── visualizations
│   └── plot_paths.py          # Plotting sample Heston trajectories
└── data
    └── market_data.json       # Volatility surface and strikes for calibration
```

---

## Calibration (src/calibration.py)

Performs calibration of the Heston model to a given volatility surface. Uses QuantLib's `HestonModelHelper` and `AnalyticHestonEngine`.

### Sample Data Used:
- Valuation Date: 2024-12-30
- Spot Price: 100
- Risk-Free Rate: 2%
- Dividend Yield: 1.5%
- Initial Parameters:
  - \( v_0 = 0.04 \)
  - \( \kappa = 1.5 \)
  - \( \theta = 0.04 \)
  - \( \sigma = 0.3 \)
  - \( \rho = -0.6 \)

Market data is simulated and stored in a structured JSON format.

---

## Simulation (src/simulation.py)

Generates asset price paths using QuantLib's `GaussianMultiPathGenerator` under the calibrated Heston process.

### Features:
- Choose number of paths and time grid resolution
- Uses QuantLib stochastic process structure

---

## Visualization (visualizations/plot_paths.py)

- Generates and plots multiple paths of the underlying asset
- Uses matplotlib for visualization
- Easy to adapt to streamlit or plotly for web interface

---

## Future Improvements

- Add interactive interface via Streamlit
- Introduce notebook explanation of the model
- Add support for pricing exotic derivatives under Heston

---

## Requirements

```
pip install numpy scipy matplotlib QuantLib-Python
```

---

## Author

Louis Delacour  
[GitHub Profile](https://github.com/your-profile)  
2025
