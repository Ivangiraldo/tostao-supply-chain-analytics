import numpy as np
import pandas as pd
from src.tostao_supply_chain.forecasting import build_daily_panel, forecast_one_series
from src.tostao_supply_chain.uncertainty import simulate_demand

def test_build_daily_panel_fills_missing_days():
    sales = pd.DataFrame({
        "fecha": pd.to_datetime(["2024-01-01", "2024-01-03"]),
        "id_tienda": ["S1", "S1"],
        "id_producto": ["P1", "P1"],
        "unidades_vendidas": [2, 4]
    })
    panel = build_daily_panel(sales)
    assert len(panel) == 3
    assert panel.loc[panel["fecha"] == pd.Timestamp("2024-01-02"), "y"].iloc[0] == 0

def test_forecast_nonnegative_and_horizon():
    values = np.tile([2, 3, 4, 5, 6, 7, 8], 8)
    pred, model = forecast_one_series(values, steps=7)
    assert len(pred) == 7
    assert (pred >= 0).all()
    assert model in {"ETS_Aditivo_7", "Seasonal_Naive_7_fallback"}

def test_simulated_demand_nonnegative():
    scenarios = simulate_demand(100, np.array([-0.5, 0.0, 0.5]), 100, seed=7)
    assert len(scenarios) == 100
    assert (scenarios >= 0).all()
