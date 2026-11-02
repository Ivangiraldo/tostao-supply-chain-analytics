# Tostao — Forecasting & Supply Chain Replenishment

Proyecto modular para pronosticar demanda diaria por SKU–Tienda a siete días y generar recomendaciones de inventario mediante escenarios de incertidumbre y una política Q90 con tope inicial de cobertura de ocho días.

> **Alcance:** prototipo técnico reproducible para la prueba. No es un sistema productivo conectado a ERP/WMS. El costo de faltante/exceso es un proxy y la política debe validarse con Abastecimiento.

## Arquitectura

```text
CSV de entrada
   │
   ▼
data_validation.py ── validación de esquema, tipos, llaves y maestros
   │
   ▼
forecasting.py ─────── panel diario + ETS aditivo (fallback Seasonal Naive 7)
   │
   ▼
uncertainty.py ─────── errores semanales ETS fuera de muestra + escenarios
   │
   ▼
inventory_policy.py ─ Q85/Q90/Q95 + límite de cobertura + pedido sugerido
   │
   ▼
pipeline.py ───────── orquestación y exportación de resultados
```

## Datos requeridos

Coloca estos archivos en una carpeta `data/`:
- `ventas_historicas.csv`
- `inventario_actual.csv`
- `catalogo_productos.csv`
- `maestro_tiendas.csv`
- `backtesting_modelos_base.csv` (exportado por el Notebook 03 final)

El archivo `ground_truth_trends.csv` no se utiliza como variable del modelo.

## Instalación

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

## Ejecución

```bash
python -m tostao_supply_chain.cli --data-dir data --output-dir outputs
```

Parámetros disponibles:

```bash
python -m tostao_supply_chain.cli --data-dir data --output-dir outputs --horizon-days 7 --safety-days 1 --service-level 0.90
```

También puedes ejecutar el Notebook `07_Industrializacion_Pipeline_Tostao.ipynb`, que explica y ejecuta el pipeline paso a paso. Luego ejecuta `08_Auditoria_Reconciliacion_Tostao.ipynb` para auditar las salidas, validar llaves y cálculos y documentar la conciliación de corridas.

## Archivos de salida

- `forecast_ets_diario_7d.csv`
- `forecast_ets_semanal_sku_tienda.csv`
- `errores_semanales_backtesting_ets.csv`
- `distribucion_demanda_escenarios.csv`
- `recomendacion_abastecimiento_Q90.csv`
- `comparacion_politicas_Q85_Q90_Q95.csv`
- `resumen_politicas_abastecimiento.csv`
- `resumen_ejecucion.csv`

## Decisiones metodológicas

- Granularidad: SKU–Tienda.
- Pronóstico: diario, agregado a siete días para la decisión de abastecimiento.
- Modelo: ETS aditivo con tendencia amortiguada y estacionalidad semanal.
- Respaldo: Seasonal Naive 7 cuando falla ETS.
- Incertidumbre: remuestreo de errores relativos semanales ETS fuera de muestra, agrupados por producto; pool global cuando hay menos de 30 errores por producto.
- Política: Q90 por defecto, con Q85/Q90/Q95 para sensibilidad.
- Cobertura máxima inicial: 8 días (7 de horizonte + 1 día de protección).

## Limitaciones conocidas

1. El histórico es corto y no representa estacionalidad anual.
2. Ventas observadas pueden estar censuradas por quiebres de inventario.
3. No hay inventario histórico diario, pedidos en tránsito, lead time, MOQ, capacidad, vida útil ni merma.
4. El maestro incluye tamaño de tienda, pero no se interpreta como capacidad física de almacenamiento.
5. El costo proxy usa margen unitario como aproximación del costo de faltante y costo de almacenamiento semanal como aproximación de exceso. No es un costo total validado.
6. La simulación de escenarios no reemplaza un backtesting operativo con inventario y recepciones reales.

## Próximas mejoras para un piloto

- Integrar inventario disponible, comprometido y en tránsito.
- Incorporar lead time por proveedor y frecuencia de despacho.
- Restringir por múltiplos mínimos, empaque y capacidad.
- Medir fill rate, quiebres, días de inventario, merma y costo real.
- Monitorear error de pronóstico y recalibrar la política con datos recientes.

## Estado de auditoría (Notebook 08)

La reconciliación se ejecutó con los cinco archivos de entrada, incluido `backtesting_modelos_base.csv`. La reproducción independiente de la lógica del Notebook 04 y el pipeline modular del Notebook 07 coinciden en **13,981 unidades Q90** (160 combinaciones, 156 con pedido positivo).

Los totales anteriores de 13.805 y 13.972 no se reproducen con esta versión de los insumos y el código. No se atribuye una causa exacta porque no se conservaron los artefactos completos de aquellas ejecuciones. Los hashes SHA-256 de los cinco insumos quedan en `outputs/hashes_insumos_08.csv`.

Ejecuta `08_Auditoria_Reconciliacion_Tostao.ipynb` desde la raíz del repositorio para volver a correr los controles. El pedido Q90 es una recomendación bajo supuestos simplificados, no una orden de compra real.


## Aplicación Streamlit

La interfaz permite consultar el resumen ejecutivo, recomendaciones por tienda y producto, pronóstico diario, comparación Q85/Q90/Q95 y metodología.

### Ejecutar localmente

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

También puedes ejecutar `run_app_windows.bat` en Windows o `./run_app.sh` en macOS/Linux.

La aplicación utiliza los CSV versionados en `data/` y `outputs/`; no vuelve a entrenar ni recalcular el pipeline al abrirse. Esto mantiene la interfaz consistente con los artefactos auditados. Para actualizar las recomendaciones, primero ejecuta el pipeline y la auditoría, y luego reinicia la aplicación.

**Advertencia:** el corte de datos es 31/03/2024 y el pronóstico es 01/04/2024–07/04/2024. La app es una demostración retrospectiva de la prueba, no una herramienta de compra en tiempo real.
