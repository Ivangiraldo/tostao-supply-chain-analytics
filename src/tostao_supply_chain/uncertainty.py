import numpy as np
import pandas as pd
from .data_validation import KEYS

def build_weekly_errors(backtest, model_name="ETS_Aditivo_7"):
    bt = backtest[backtest["modelo"] == model_name].copy()
    if bt.empty:
        raise ValueError(f"No hay observaciones de backtesting para {model_name}.")
    weekly = (bt.groupby(KEYS + ["fold"], as_index=False)
                .agg(demanda_real=("y", "sum"),
                     demanda_predicha=("pred", "sum"),
                     dias_evaluados=("fecha", "nunique")))
    weekly["error"] = weekly["demanda_real"] - weekly["demanda_predicha"]
    weekly["error_relativo"] = weekly["error"] / weekly["demanda_predicha"].clip(lower=1)
    weekly = weekly.replace([np.inf, -np.inf], np.nan).dropna(subset=["error_relativo"])
    return weekly

def simulate_demand(point_forecast, residuals, n_simulations=10_000, seed=42):
    rng = np.random.default_rng(seed)
    residuals = np.asarray(residuals, dtype=float)
    if len(residuals) < 1:
        raise ValueError("No hay residuos suficientes para generar escenarios.")
    sampled = rng.choice(residuals, size=n_simulations, replace=True)
    return np.maximum(0, float(point_forecast) * (1 + sampled))

def create_demand_scenarios(weekly_forecast, weekly_errors, n_simulations=10_000,
                            min_product_errors=30, seed=42):
    global_pool = weekly_errors["error_relativo"].dropna().to_numpy()
    if len(global_pool) < 10:
        raise ValueError(f"Se requieren al menos 10 errores; disponibles={len(global_pool)}")
    product_pools = {
        product: group["error_relativo"].dropna().to_numpy()
        for product, group in weekly_errors.groupby("id_producto")
    }
    rows = []
    cache = {}
    # Un único generador secuencial replica el orden de muestreo del Notebook 04
    # y mantiene una secuencia reproducible entre ejecuciones.
    rng = np.random.default_rng(seed)
    for _, row in weekly_forecast.iterrows():
        product = row["id_producto"]
        pool = product_pools.get(product, np.array([]))
        source = "producto" if len(pool) >= min_product_errors else "global"
        if source == "global":
            pool = global_pool
        sampled = rng.choice(pool, size=n_simulations, replace=True)
        scenarios = np.maximum(
            0, float(row["demanda_pronosticada_7d"]) * (1 + sampled)
        )
        cache[(row["id_tienda"], product)] = scenarios
        rows.append({
            **{k: row[k] for k in KEYS},
            "demanda_puntual": float(row["demanda_pronosticada_7d"]),
            "n_residuos": int(len(pool)),
            "fuente_residuos": source,
            "q05": float(np.quantile(scenarios, 0.05)),
            "q50": float(np.quantile(scenarios, 0.50)),
            "q90": float(np.quantile(scenarios, 0.90)),
            "q95": float(np.quantile(scenarios, 0.95))
        })
    return pd.DataFrame(rows), cache
