from pathlib import Path
import pandas as pd
from .config import PipelineConfig
from .data_validation import read_inputs, validate_inputs
from .forecasting import build_daily_panel, forecast_all
from .uncertainty import build_weekly_errors, create_demand_scenarios
from .inventory_policy import recommend_inventory

def run_pipeline(data_dir, output_dir, config=None):
    config = config or PipelineConfig()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = validate_inputs(read_inputs(data_dir))
    panel = build_daily_panel(data["sales"])
    forecast_daily, forecast_weekly = forecast_all(panel, config.horizon_days)
    weekly_errors = build_weekly_errors(data["backtest"], config.model_name)
    distribution, scenario_cache = create_demand_scenarios(
        forecast_weekly, weekly_errors,
        n_simulations=config.n_simulations,
        min_product_errors=config.min_product_errors,
        seed=config.random_seed
    )
    recommendations, policy_comparison, policy_summary = recommend_inventory(
        forecast_weekly, data["inventory"], data["products"], scenario_cache,
        horizon_days=config.horizon_days,
        safety_days=config.safety_days,
        service_levels=config.service_levels,
        default_service_level=config.default_service_level
    )

    outputs = {
        "forecast_ets_diario_7d.csv": forecast_daily,
        "forecast_ets_semanal_sku_tienda.csv": forecast_weekly,
        "errores_semanales_backtesting_ets.csv": weekly_errors,
        "distribucion_demanda_escenarios.csv": distribution,
        "recomendacion_abastecimiento_Q90.csv": recommendations,
        "comparacion_politicas_Q85_Q90_Q95.csv": policy_comparison,
        "resumen_politicas_abastecimiento.csv": policy_summary
    }
    for filename, frame in outputs.items():
        frame.to_csv(output_dir / filename, index=False)

    run_summary = {
        "fecha_ultimo_dato": str(panel["fecha"].max().date()),
        "horizonte_inicio": str(forecast_daily["fecha"].min().date()),
        "horizonte_fin": str(forecast_daily["fecha"].max().date()),
        "combinaciones_sku_tienda": int(forecast_weekly.shape[0]),
        "observaciones_ventas": int(data["sales"].shape[0]),
        "residuos_backtesting": int(weekly_errors.shape[0]),
        "combinaciones_con_pedido": int((recommendations["pedido_sugerido"] > 0).sum()),
        "unidades_pedido_Q90": int(recommendations["pedido_sugerido"].sum()),
        "fallbacks_forecast": int((forecast_daily["modelo"] != config.model_name).sum())
    }
    pd.Series(run_summary, name="valor").to_csv(output_dir / "resumen_ejecucion.csv", header=True)
    return run_summary, outputs
