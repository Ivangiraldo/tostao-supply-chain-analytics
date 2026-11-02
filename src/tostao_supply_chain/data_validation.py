from pathlib import Path
import pandas as pd

KEYS = ["id_tienda", "id_producto"]

def read_inputs(data_dir):
    data_dir = Path(data_dir)
    names = {
        "sales": "ventas_historicas.csv",
        "inventory": "inventario_actual.csv",
        "products": "catalogo_productos.csv",
        "stores": "maestro_tiendas.csv",
        "backtest": "backtesting_modelos_base.csv",
    }
    missing = [filename for filename in names.values() if not (data_dir / filename).exists()]
    if missing:
        raise FileNotFoundError(f"Faltan archivos de entrada en {data_dir}: {missing}")
    return {key: pd.read_csv(data_dir / filename) for key, filename in names.items()}

def _require_columns(df, columns, label):
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en {label}: {sorted(missing)}")

def validate_inputs(data):
    sales = data["sales"].copy()
    inventory = data["inventory"].copy()
    products = data["products"].copy()
    stores = data["stores"].copy()
    backtest = data["backtest"].copy()

    _require_columns(sales, ["fecha", "id_tienda", "id_producto", "unidades_vendidas"], "ventas")
    _require_columns(inventory, KEYS + ["stock_actual"], "inventario")
    _require_columns(products, ["id_producto", "costo_unitario", "precio_venta",
                                "costo_almacenamiento_semanal"], "catálogo")
    _require_columns(stores, ["id_tienda", "ciudad", "tamaño_m2"], "maestro de tiendas")
    _require_columns(backtest, KEYS + ["fecha", "y", "pred", "modelo", "fold"], "backtesting")

    for frame, cols, label in [
        (inventory, KEYS, "inventario"),
        (products, ["id_producto"], "catálogo"),
        (stores, ["id_tienda"], "maestro de tiendas"),
    ]:
        if frame.duplicated(cols).any():
            raise ValueError(f"Hay llaves duplicadas en {label}: {cols}")

    sales["fecha"] = pd.to_datetime(sales["fecha"], errors="coerce")
    backtest["fecha"] = pd.to_datetime(backtest["fecha"], errors="coerce")
    if sales["fecha"].isna().any():
        raise ValueError("Hay fechas inválidas en ventas.")
    if backtest["fecha"].isna().any():
        raise ValueError("Hay fechas inválidas en backtesting.")

    for col in ["unidades_vendidas"]:
        sales[col] = pd.to_numeric(sales[col], errors="coerce")
    inventory["stock_actual"] = pd.to_numeric(inventory["stock_actual"], errors="coerce")
    for col in ["costo_unitario", "precio_venta", "costo_almacenamiento_semanal"]:
        products[col] = pd.to_numeric(products[col], errors="coerce")
    for col in ["y", "pred", "fold"]:
        backtest[col] = pd.to_numeric(backtest[col], errors="coerce")

    if sales["unidades_vendidas"].isna().any() or (sales["unidades_vendidas"] < 0).any():
        raise ValueError("Ventas contiene valores nulos o negativos; revisar antes de modelar.")
    if inventory["stock_actual"].isna().any() or (inventory["stock_actual"] < 0).any():
        raise ValueError("Inventario contiene valores nulos o negativos.")
    if products[["costo_unitario", "precio_venta", "costo_almacenamiento_semanal"]].isna().any().any():
        raise ValueError("El catálogo contiene costos/precios nulos o no numéricos.")
    if products[["costo_unitario", "precio_venta", "costo_almacenamiento_semanal"]].lt(0).any().any():
        raise ValueError("El catálogo contiene costos/precios negativos.")

    for df in [sales, inventory, products, stores, backtest]:
        for col in ["id_tienda", "id_producto"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

    # Se agregan duplicados transaccionales a nivel día–tienda–producto.
    sales = (sales.groupby(["fecha"] + KEYS, as_index=False)["unidades_vendidas"]
                  .sum())

    # La cobertura de inventario debe coincidir con las combinaciones presentes en ventas.
    sales_keys = set(map(tuple, sales[KEYS].drop_duplicates().to_numpy()))
    inventory_keys = set(map(tuple, inventory[KEYS].drop_duplicates().to_numpy()))
    if sales_keys != inventory_keys:
        raise ValueError(
            f"Las llaves ventas/inventario no coinciden. "
            f"Solo ventas={len(sales_keys-inventory_keys)}, solo inventario={len(inventory_keys-sales_keys)}."
        )

    unknown_products = set(sales["id_producto"]) - set(products["id_producto"])
    unknown_stores = set(sales["id_tienda"]) - set(stores["id_tienda"])
    if unknown_products or unknown_stores:
        raise ValueError(f"Maestros incompletos. Productos={sorted(unknown_products)}, tiendas={sorted(unknown_stores)}")

    data = dict(data)
    data.update(sales=sales, inventory=inventory, products=products, stores=stores, backtest=backtest)
    return data
