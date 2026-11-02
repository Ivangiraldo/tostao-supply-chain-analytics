import numpy as np
import pandas as pd
from .data_validation import KEYS

def recommend_inventory(weekly_forecast, inventory, products, scenario_cache,
                       horizon_days=7, safety_days=1,
                       service_levels=(0.85, 0.90, 0.95),
                       default_service_level=0.90):
    decision = (weekly_forecast
        .merge(inventory[KEYS + ["stock_actual"]], on=KEYS, how="left", validate="one_to_one")
        .merge(products[["id_producto", "costo_unitario", "precio_venta",
                         "costo_almacenamiento_semanal"]],
               on="id_producto", how="left", validate="many_to_one"))
    if decision[["stock_actual", "costo_unitario", "precio_venta",
                 "costo_almacenamiento_semanal"]].isna().any().any():
        raise ValueError("Hay combinaciones sin inventario o atributos económicos.")

    decision["margen_unitario_proxy"] = (
        decision["precio_venta"] - decision["costo_unitario"]
    ).clip(lower=0)

    rows = []
    max_days = horizon_days + safety_days
    for _, row in decision.iterrows():
        key = (row["id_tienda"], row["id_producto"])
        scenarios = scenario_cache[key]
        daily_mean = max(0.0, float(row["demanda_pronosticada_7d"])) / horizon_days
        cap = int(np.ceil(daily_mean * max_days))
        for level in service_levels:
            raw_quantile = float(np.quantile(scenarios, level))
            target = min(int(np.ceil(raw_quantile)), cap)
            order = max(0, int(np.ceil(target - row["stock_actual"])))
            shortage = np.maximum(scenarios - target, 0)
            excess = np.maximum(target - scenarios, 0)
            cu = max(0.0, float(row["margen_unitario_proxy"]))
            co = max(0.0, float(row["costo_almacenamiento_semanal"]))
            expected_cost = float(np.mean(cu * shortage + co * excess))
            rows.append({
                **{k: row[k] for k in KEYS},
                "politica": f"Q{int(level*100)}",
                "nivel_cuantil": level,
                "demanda_pronosticada_7d": float(row["demanda_pronosticada_7d"]),
                "cuantil_sin_tope": raw_quantile,
                "tope_cobertura": cap,
                "stock_actual": float(row["stock_actual"]),
                "inventario_objetivo": target,
                "pedido_sugerido": order,
                "costo_esperado_estimado": expected_cost
            })
    comparison = pd.DataFrame(rows)
    default_name = f"Q{int(default_service_level*100)}"
    recommendations = comparison[comparison["politica"] == default_name].copy()
    recommendations = recommendations.sort_values(
        ["pedido_sugerido", "costo_esperado_estimado"], ascending=[False, False]
    )
    summary = (comparison.groupby("politica", as_index=False)
        .agg(pedido_total_unidades=("pedido_sugerido", "sum"),
             inventario_objetivo_total=("inventario_objetivo", "sum"),
             combinaciones_con_pedido=("pedido_sugerido", lambda s: int((s > 0).sum())),
             costo_esperado_estimado=("costo_esperado_estimado", "sum")))
    return recommendations, comparison, summary
