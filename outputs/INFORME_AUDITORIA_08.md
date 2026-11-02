# Auditoría y reconciliación — Tostao Supply Chain (Notebook 08)

## Estado

**Reconciliación reproducible completada con los archivos de entrada recibidos.**

- Pedido Q90 canónico: **13,981 unidades**
- Combinaciones SKU–tienda: **160**
- Combinaciones con pedido positivo: **156**
- Pronóstico: **2024-04-01 a 2024-04-07**
- Último día de ventas: **2024-03-31**
- Errores ETS semanales fuera de muestra: **480**

## Qué se hizo

1. Se incorporó `backtesting_modelos_base.csv` al conjunto de datos del proyecto.
2. Se ejecutó el pipeline modular del Notebook 07 con los cinco CSV requeridos.
3. Se reprodujo por separado la lógica de muestreo y política del Notebook 04 usando la misma semilla (`42`), los mismos errores ETS y el mismo pronóstico semanal.
4. Se comparó el total Q90 de ambos cálculos.

**Resultado:** la reproducción directa de Notebook 04 y el pipeline de Notebook 07 producen ambos **13,981 unidades**. Esta es la cifra canónica de esta versión de los insumos y el código.

## Reconciliación de cifras anteriores

| Ejecución | Pedido Q90 | Estado |
|---|---:|---|
| Notebook 04, resumen compartido anteriormente | 13.805 | No reproducible con el archivo de backtesting recibido |
| Snapshot anterior del proyecto 07 | 13.972 | Snapshot previo; difiere de la ejecución reproducible actual |
| Notebook 04 reproducido con los insumos actuales | 13,981 | Reproducido |
| Pipeline 07 ejecutado con los insumos actuales | 13,981 | Reproducido |

La diferencia de 13.805 y 13.972 no puede atribuirse con certeza a una causa específica sin conservar el archivo de backtesting, el pronóstico y el código exactos de aquellas ejecuciones. Con los archivos actuales, los dos caminos de cálculo coinciden.

## Controles

| control                                         | aprobado   | detalle                             |
|:------------------------------------------------|:-----------|:------------------------------------|
| Entradas requeridas presentes                   | True       | 5 de 5 CSV disponibles              |
| Ventas con 14.560 filas                         | True       | filas=14560                         |
| Pronóstico con 160 combinaciones                | True       | filas=160                           |
| Backtesting ETS con 480 errores semanales       | True       | errores=480                         |
| Recomendación Q90 con 160 combinaciones         | True       | filas=160                           |
| Combinaciones con pedido positivo               | True       | positivas=156                       |
| Pedido calculado por Notebook 04 = pipeline     | True       | directo=13981; pipeline=13981       |
| Sin pronósticos negativos                       | True       | mínimo=2.056640                     |
| Pronóstico diario suma pronóstico semanal       | True       | diferencia máxima=5.68434188608e-14 |
| Stock de recomendación coincide con inventario  | True       | filas=160                           |
| Pedido = max(0, objetivo - stock)               | True       | 160 combinaciones revisadas         |
| Comparación incluye 3 políticas por combinación | True       | filas=480                           |
| Sin fallback del modelo ETS                     | True       | modelos={'ETS_Aditivo_7': 1120}     |

## Huellas digitales de los insumos

Se guardan hashes SHA-256 para identificar exactamente los archivos usados en esta ejecución:

| Archivo | SHA-256 |
|---|---|
| `ventas_historicas.csv` | `375749b680875d27987150abdcc4deb91dc32fd584f16e672ee5d35c2f11608e` |
| `inventario_actual.csv` | `181d33a98f5a0e614c162120f33151eeaa6b355b3c89ea2b9f6002f0c70b0b0a` |
| `catalogo_productos.csv` | `ee9ef3dc586e99c8890c063c44c08281ed3ea2012017228e4b9ccf17c0dcac3d` |
| `maestro_tiendas.csv` | `127e3a3b05d72e2ce7dda4b3e7af861ce4b59d4908475d3e06a4753c717a854d` |
| `backtesting_modelos_base.csv` | `ce5fb8c635f94f781f873bef2824ca8baa28121ff71626016447fe7fd37786d3` |

## Interpretación y límites

- 13.981 es el pedido sugerido agregado por la política Q90 de esta corrida; no es una orden de compra emitida.
- El horizonte es de siete días y el inventario objetivo tiene un tope de cobertura de ocho días.
- El día adicional es un supuesto de política, no una capacidad física validada.
- No se dispone de lead time, pedidos en tránsito, recepciones, múltiplos de compra, vida útil ni capacidad física de almacenamiento.
- Los escenarios de error se estiman con 60 residuos por producto (20 tiendas × 3 folds), agrupados por producto.
- Q90 es un cuantil empírico de los escenarios; no garantiza un nivel de servicio real del 90%.

## Decisión para el proyecto

**Se puede continuar con Streamlit usando los resultados del pipeline ejecutado y versionado aquí.** La aplicación debe mostrar el sello de ejecución y la fecha de corte, y debe describir la recomendación como apoyo a la decisión, no como orden automática.
