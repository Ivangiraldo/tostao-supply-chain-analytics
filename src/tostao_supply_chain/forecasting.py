import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from .data_validation import KEYS

def build_daily_panel(sales):
    dates = pd.date_range(sales["fecha"].min(), sales["fecha"].max(), freq="D")
    combinations = sales[KEYS].drop_duplicates()
    calendar = pd.DataFrame({"fecha": dates})
    panel = combinations.merge(calendar, how="cross")
    daily = (sales.groupby(KEYS + ["fecha"], as_index=False)["unidades_vendidas"]
                  .sum())
    panel = panel.merge(daily, on=KEYS + ["fecha"], how="left")
    panel["y"] = panel["unidades_vendidas"].fillna(0).clip(lower=0).astype(float)
    return panel.drop(columns="unidades_vendidas").sort_values(KEYS + ["fecha"]).reset_index(drop=True)

def forecast_one_series(values, steps=7):
    y = pd.Series(values, dtype=float).clip(lower=0).reset_index(drop=True)
    if len(y) < 28:
        raise ValueError(f"Se requieren al menos 28 días de historia; recibidos={len(y)}")
    try:
        fit = ExponentialSmoothing(
            y, trend="add", damped_trend=True, seasonal="add",
            seasonal_periods=7, initialization_method="estimated"
        ).fit(optimized=True, use_brute=False)
        prediction = np.asarray(fit.forecast(steps), dtype=float)
        if not np.isfinite(prediction).all():
            raise ValueError("ETS produjo valores no finitos.")
        return np.clip(prediction, 0, None), "ETS_Aditivo_7"
    except Exception:
        # Respaldo igual al utilizado en el experimento: Seasonal Naive 7.
        prediction = np.resize(y.iloc[-7:].to_numpy(), steps)
        return np.clip(prediction, 0, None), "Seasonal_Naive_7_fallback"

def forecast_all(panel, horizon_days=7):
    last_date = pd.Timestamp(panel["fecha"].max())
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")
    rows = []
    for (store, product), group in panel.groupby(KEYS):
        group = group.sort_values("fecha")
        prediction, model_used = forecast_one_series(group["y"], horizon_days)
        for date, value in zip(future_dates, prediction):
            rows.append({
                "id_tienda": store,
                "id_producto": product,
                "fecha": date,
                "demanda_pronosticada": float(value),
                "modelo": model_used
            })
    daily = pd.DataFrame(rows)
    weekly = (daily.groupby(KEYS, as_index=False)
                   .agg(demanda_pronosticada_7d=("demanda_pronosticada", "sum")))
    return daily, weekly
