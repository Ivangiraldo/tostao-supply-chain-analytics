# Arquitectura

- `data_validation.py`: contratos de entrada, tipos, llaves y consistencia entre ventas e inventario.
- `forecasting.py`: panel diario y pronóstico ETS con fallback Seasonal Naive 7.
- `uncertainty.py`: errores semanales fuera de muestra y escenarios de demanda.
- `inventory_policy.py`: cuantiles de protección, tope de cobertura y cálculo del pedido.
- `pipeline.py`: orquestación y exportación.
- `cli.py`: interfaz de línea de comandos.
- `config.py`: parámetros centralizados.
- `tests/`: pruebas unitarias básicas.
