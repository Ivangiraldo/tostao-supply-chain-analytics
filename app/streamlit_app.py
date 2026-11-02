from pathlib import Path
import sys
import io
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"

st.set_page_config(
    page_title="Tostao | Supply Chain Intelligence",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root {
    --tostao-yellow: #F2B600;
    --tostao-yellow-soft: #FFF4CC;
    --tostao-charcoal: #171717;
    --tostao-cream: #F8F6F0;
    --tostao-white: #FFFFFF;
}
.stApp { background: var(--tostao-cream); }
.block-container {padding-top: 1.6rem; padding-bottom: 2.2rem;}
[data-testid="stSidebar"] {
    background: var(--tostao-charcoal);
}
[data-testid="stSidebar"] * {
    color: #FFFFFF;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    color: #FFFFFF;
}
[data-testid="stMetric"] {
    background: var(--tostao-white);
    border: 1px solid #E8E2D5;
    border-left: 4px solid var(--tostao-yellow);
    padding: 14px 16px;
    border-radius: 10px;
}
div[data-testid="stMetricValue"] {font-size: 1.65rem; color: var(--tostao-charcoal);}
h1, h2, h3 { color: var(--tostao-charcoal); }
.stButton > button, .stDownloadButton > button {
    background: var(--tostao-yellow);
    color: var(--tostao-charcoal);
    border: 1px solid var(--tostao-yellow);
    border-radius: 8px;
    font-weight: 650;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: #DDA600;
    color: #111111;
    border-color: #DDA600;
}
[data-testid="stDataFrame"] {
    border: 1px solid #E8E2D5;
    border-radius: 10px;
}
.small-muted {color: #6b7280; font-size: .88rem;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_csv(path):
    return pd.read_csv(path)

@st.cache_data
def load_all():
    sales = load_csv(DATA / "ventas_historicas.csv")
    inventory = load_csv(DATA / "inventario_actual.csv")
    products = load_csv(DATA / "catalogo_productos.csv")
    stores = load_csv(DATA / "maestro_tiendas.csv")
    daily = load_csv(OUT / "forecast_ets_diario_7d.csv")
    weekly = load_csv(OUT / "forecast_ets_semanal_sku_tienda.csv")
    rec90 = load_csv(OUT / "recomendacion_abastecimiento_Q90.csv")
    policies = load_csv(OUT / "comparacion_politicas_Q85_Q90_Q95.csv")
    summary = load_csv(OUT / "resumen_politicas_abastecimiento.csv")
    run = load_csv(OUT / "resumen_ejecucion.csv")
    for df, col in [(sales, "fecha"), (daily, "fecha")]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return sales, inventory, products, stores, daily, weekly, rec90, policies, summary, run

try:
    sales, inventory, products, stores, daily, weekly, rec90, policies, policy_summary, run_summary = load_all()
except Exception as exc:
    st.error("No fue posible cargar los datos del proyecto.")
    st.exception(exc)
    st.stop()

# Enrichment for readable labels
product_labels = products.set_index("id_producto")["nombre"].to_dict()
store_city = stores.set_index("id_tienda")["ciudad"].to_dict()
store_labels = {
    row.id_tienda: f"{row.id_tienda} · {row.ciudad}"
    for row in stores.itertuples(index=False)
}
sales = sales.merge(stores[["id_tienda", "ciudad"]], on="id_tienda", how="left")
sales = sales.merge(products[["id_producto", "nombre", "categoria"]], on="id_producto", how="left")
daily = daily.merge(products[["id_producto", "nombre", "categoria"]], on="id_producto", how="left")
weekly = weekly.merge(products[["id_producto", "nombre", "categoria"]], on="id_producto", how="left")
weekly = weekly.merge(stores[["id_tienda", "ciudad"]], on="id_tienda", how="left")
rec90 = rec90.merge(products[["id_producto", "nombre", "categoria", "precio_venta", "costo_unitario"]], on="id_producto", how="left")
rec90 = rec90.merge(stores[["id_tienda", "ciudad"]], on="id_tienda", how="left")
policies = policies.merge(products[["id_producto", "nombre", "categoria"]], on="id_producto", how="left")
policies = policies.merge(stores[["id_tienda", "ciudad"]], on="id_tienda", how="left")

last_date = pd.to_datetime(sales["fecha"]).max()
forecast_start = pd.to_datetime(daily["fecha"]).min()
forecast_end = pd.to_datetime(daily["fecha"]).max()
units_q90 = int(rec90["pedido_sugerido"].sum())
combos_order = int((rec90["pedido_sugerido"] > 0).sum())
total_combos = int(rec90[["id_tienda", "id_producto"]].drop_duplicates().shape[0])
demand_forecast = float(weekly["demanda_pronosticada_7d"].sum())
stock_total = float(inventory["stock_actual"].sum())
expected_cost = float(rec90["costo_esperado_estimado"].sum())

logo_path = ROOT / "app" / "assets" / "logo_tostao.jpg"
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)
st.sidebar.markdown(
    "<div style='text-align:center;color:#F2B600;font-weight:700;"
    "letter-spacing:.08em;margin:0.2rem 0 1rem 0;'>SUPPLY CHAIN INTELLIGENCE</div>",
    unsafe_allow_html=True,
)
page = st.sidebar.radio(
    "Navegación",
    ["Resumen ejecutivo", "Recomendaciones", "Pronóstico de demanda", "Comparador de políticas", "Datos y metodología"],
)
st.sidebar.divider()
st.sidebar.caption("Corte histórico")
st.sidebar.write(last_date.strftime("%d/%m/%Y"))
st.sidebar.caption("Horizonte pronosticado")
st.sidebar.write(f"{forecast_start:%d/%m/%Y} – {forecast_end:%d/%m/%Y}")
st.sidebar.caption("Versión analítica · Q90 · cobertura máxima 8 días")

def fmt_int(x):
    return f"{x:,.0f}".replace(",", ".")

def fmt_cop(x):
    return "$ " + fmt_int(x)

def filters(df, key_prefix):
    c1, c2, c3 = st.columns(3)
    cities = ["Todas"] + sorted(df["ciudad"].dropna().unique().tolist())
    city = c1.selectbox("Ciudad", cities, key=f"{key_prefix}_city")
    dff = df if city == "Todas" else df[df["ciudad"] == city]
    stores_opts = ["Todas"] + sorted(dff["id_tienda"].dropna().unique().tolist())
    store = c2.selectbox("Tienda", stores_opts, key=f"{key_prefix}_store")
    if store != "Todas":
        dff = dff[dff["id_tienda"] == store]
    products_opts = ["Todos"] + sorted(dff["nombre"].dropna().unique().tolist())
    product = c3.selectbox("Producto", products_opts, key=f"{key_prefix}_product")
    if product != "Todos":
        dff = dff[dff["nombre"] == product]
    return dff

def download_buttons(df, stem):
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Descargar CSV", csv, file_name=f"{stem}.csv", mime="text/csv")
    try:
        buff = io.BytesIO()
        with pd.ExcelWriter(buff, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Datos")
        st.download_button("Descargar Excel", buff.getvalue(), file_name=f"{stem}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception:
        st.caption("Exportación Excel no disponible en este entorno; puedes descargar CSV.")

if page == "Resumen ejecutivo":
    st.title("Resumen ejecutivo")
    st.write("Planeación de abastecimiento basada en pronóstico de demanda e incertidumbre.")
    st.info(
        f"Los datos históricos llegan hasta el **{last_date:%d/%m/%Y}**. "
        f"El pronóstico corresponde al **{forecast_start:%d/%m/%Y}–{forecast_end:%d/%m/%Y}**. "
        "Es una demostración retrospectiva sobre el corte disponible, no una recomendación vigente para comprar hoy."
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pedido sugerido Q90", f"{fmt_int(units_q90)} und.")
    m2.metric("SKU–tienda con pedido", f"{combos_order} / {total_combos}")
    m3.metric("Demanda pronosticada", f"{fmt_int(demand_forecast)} und.")
    m4.metric("Inventario actual", f"{fmt_int(stock_total)} und.")
    st.divider()
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Pedido recomendado por ciudad")
        city_orders = rec90.groupby("ciudad", as_index=False)["pedido_sugerido"].sum().sort_values("pedido_sugerido", ascending=False)
        fig = px.bar(city_orders, x="ciudad", y="pedido_sugerido", text_auto=".0f",
                     labels={"ciudad": "Ciudad", "pedido_sugerido": "Unidades sugeridas"})
        fig.update_layout(margin=dict(l=10,r=10,t=20,b=10), xaxis_title=None, yaxis_title="Unidades")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Distribución del pedido")
        cat_orders = rec90.groupby("categoria", as_index=False)["pedido_sugerido"].sum().sort_values("pedido_sugerido", ascending=False)
        fig = px.pie(cat_orders, names="categoria", values="pedido_sugerido", hole=.55)
        fig.update_layout(margin=dict(l=10,r=10,t=20,b=10), legend_title=None)
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("Productos con mayor pedido sugerido")
    top = rec90.groupby("nombre", as_index=False)["pedido_sugerido"].sum().nlargest(8, "pedido_sugerido")
    fig = px.bar(top.sort_values("pedido_sugerido"), x="pedido_sugerido", y="nombre", orientation="h",
                 labels={"pedido_sugerido":"Unidades", "nombre":"Producto"}, text_auto=".0f")
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), yaxis_title=None, xaxis_title="Unidades sugeridas")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Costo esperado estimado (proxy): {fmt_cop(expected_cost)}. No representa ahorro ni costo financiero real.")

elif page == "Recomendaciones":
    st.title("Recomendaciones de abastecimiento")
    st.write("Consulta el pedido sugerido por tienda y producto bajo la política Q90.")
    filtered = filters(rec90, "rec")
    sort_col = st.selectbox("Ordenar por", ["pedido_sugerido", "demanda_pronosticada_7d", "stock_actual", "costo_esperado_estimado"], format_func=lambda x: {
        "pedido_sugerido":"Pedido sugerido", "demanda_pronosticada_7d":"Demanda pronosticada", "stock_actual":"Stock actual", "costo_esperado_estimado":"Costo proxy"
    }[x])
    filtered = filtered.sort_values(sort_col, ascending=False)
    c1,c2,c3 = st.columns(3)
    c1.metric("Unidades sugeridas", fmt_int(filtered["pedido_sugerido"].sum()))
    c2.metric("Combinaciones con pedido", int((filtered["pedido_sugerido"]>0).sum()))
    c3.metric("Stock disponible", fmt_int(filtered["stock_actual"].sum()))
    view_cols = ["ciudad","id_tienda","id_producto","nombre","categoria","demanda_pronosticada_7d","stock_actual","inventario_objetivo","pedido_sugerido","costo_esperado_estimado"]
    display = filtered[view_cols].rename(columns={
        "ciudad":"Ciudad","id_tienda":"Tienda","id_producto":"SKU","nombre":"Producto","categoria":"Categoría",
        "demanda_pronosticada_7d":"Pronóstico 7d","stock_actual":"Stock actual",
        "inventario_objetivo":"Inventario objetivo","pedido_sugerido":"Pedido sugerido","costo_esperado_estimado":"Costo proxy"
    })
    st.dataframe(display, use_container_width=True, hide_index=True,
                 column_config={
                     "Pronóstico 7d": st.column_config.NumberColumn(format="%.1f"),
                     "Costo proxy": st.column_config.NumberColumn(format="$ %.0f"),
                 })
    st.subheader("Detalle de una combinación")
    choices = filtered.copy()
    choices["label"] = choices["id_tienda"] + " · " + choices["nombre"] + " (" + choices["id_producto"] + ")"
    if len(choices):
        selected = st.selectbox("Selecciona tienda y producto", choices["label"].tolist())
        row = choices.loc[choices["label"] == selected].iloc[0]
        a,b,c,d = st.columns(4)
        a.metric("Demanda 7 días", f"{row.demanda_pronosticada_7d:,.1f}")
        b.metric("Stock actual", fmt_int(row.stock_actual))
        c.metric("Inventario objetivo", fmt_int(row.inventario_objetivo))
        d.metric("Pedido sugerido", fmt_int(row.pedido_sugerido))
        st.caption("El inventario objetivo incorpora el cuantil de demanda con el tope de cobertura configurado. El pedido sugerido descuenta el stock actual; no incluye inventario en tránsito.")
    download_buttons(display, "recomendaciones_abastecimiento_Q90")

elif page == "Pronóstico de demanda":
    st.title("Pronóstico de demanda")
    st.write("Histórico diario y proyección de siete días para una combinación tienda–producto.")
    f1, f2, f3 = st.columns(3)
    city = f1.selectbox("Ciudad", ["Todas"] + sorted(stores["ciudad"].unique().tolist()), key="fcity")
    store_options = stores if city == "Todas" else stores[stores["ciudad"] == city]
    store = f2.selectbox("Tienda", sorted(store_options["id_tienda"].tolist()), key="fstore")
    prod = f3.selectbox("Producto", sorted(products["id_producto"].tolist()),
                        format_func=lambda x: f"{x} · {product_labels.get(x,x)}", key="fprod")
    hist = sales[(sales["id_tienda"] == store) & (sales["id_producto"] == prod)].copy()
    pred = daily[(daily["id_tienda"] == store) & (daily["id_producto"] == prod)].copy()
    hist = hist.groupby("fecha", as_index=False)["unidades_vendidas"].sum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["fecha"], y=hist["unidades_vendidas"], mode="lines",
                             name="Ventas históricas", line=dict(width=2)))
    fig.add_trace(go.Scatter(x=pred["fecha"], y=pred["demanda_pronosticada"], mode="lines+markers",
                             name="Pronóstico 7 días", line=dict(width=3, dash="dash")))
    fig.add_vline(x=forecast_start, line_dash="dot", annotation_text="Inicio pronóstico")
    fig.update_layout(xaxis_title="Fecha", yaxis_title="Unidades", hovermode="x unified",
                      legend=dict(orientation="h", y=1.1), margin=dict(l=10,r=10,t=35,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Modelo aplicado: {', '.join(sorted(pred['modelo'].dropna().unique())) if len(pred) else 'Sin datos'}.")
    if len(pred):
        st.metric("Demanda pronosticada 7 días", f"{pred['demanda_pronosticada'].sum():,.1f} unidades")
        st.dataframe(pred[["fecha","demanda_pronosticada","modelo"]].rename(columns={
            "fecha":"Fecha","demanda_pronosticada":"Pronóstico","modelo":"Modelo"
        }), use_container_width=True, hide_index=True)

elif page == "Comparador de políticas":
    st.title("Comparador de políticas de inventario")
    st.write("Compara los resultados agregados de los cuantiles Q85, Q90 y Q95 bajo el tope inicial de cobertura de ocho días.")
    summary = policy_summary.copy()
    summary["politica"] = pd.Categorical(summary["politica"], ["Q85","Q90","Q95"], ordered=True)
    summary = summary.sort_values("politica")
    c1,c2,c3 = st.columns(3)
    for col, (_, row) in zip([c1,c2,c3], summary.iterrows()):
        col.metric(f"Pedido total {row.politica}", f"{fmt_int(row.pedido_total_unidades)} und.")
        col.caption(f"Costo proxy: {fmt_cop(row.costo_esperado_estimado)}")
    fig = px.bar(summary, x="politica", y="pedido_total_unidades", color="politica", text_auto=".0f",
                 labels={"politica":"Política","pedido_total_unidades":"Pedido total (unidades)"})
    fig.update_layout(showlegend=False, margin=dict(l=10,r=10,t=20,b=10), xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    fig2 = px.bar(summary, x="politica", y="costo_esperado_estimado", color="politica", text_auto=".0f",
                  labels={"politica":"Política","costo_esperado_estimado":"Costo esperado estimado (proxy)"})
    fig2.update_layout(showlegend=False, margin=dict(l=10,r=10,t=20,b=10), xaxis_title=None)
    st.plotly_chart(fig2, use_container_width=True)
    st.subheader("Explorar políticas por tienda y producto")
    selected_policy = st.selectbox("Política", ["Q85","Q90","Q95"], index=1)
    filtered = policies[policies["politica"] == selected_policy].copy()
    filtered = filters(filtered, f"pol_{selected_policy}")
    show = filtered[["ciudad","id_tienda","id_producto","nombre","demanda_pronosticada_7d","stock_actual","inventario_objetivo","pedido_sugerido","costo_esperado_estimado"]].rename(columns={
        "ciudad":"Ciudad","id_tienda":"Tienda","id_producto":"SKU","nombre":"Producto",
        "demanda_pronosticada_7d":"Demanda 7d","stock_actual":"Stock actual",
        "inventario_objetivo":"Inventario objetivo","pedido_sugerido":"Pedido sugerido","costo_esperado_estimado":"Costo proxy"
    })
    st.dataframe(show, use_container_width=True, hide_index=True)
    download_buttons(show, f"comparacion_{selected_policy}")

elif page == "Datos y metodología":
    st.title("Datos, metodología y límites")
    st.subheader("Cobertura de los datos")
    d1,d2,d3,d4 = st.columns(4)
    d1.metric("Registros históricos", fmt_int(len(sales)))
    d2.metric("Tiendas", stores["id_tienda"].nunique())
    d3.metric("Productos", products["id_producto"].nunique())
    d4.metric("Combinaciones SKU–tienda", total_combos)
    st.write(f"Periodo histórico: **{sales['fecha'].min():%d/%m/%Y} – {last_date:%d/%m/%Y}**.")
    st.write(f"Pronóstico: **{forecast_start:%d/%m/%Y} – {forecast_end:%d/%m/%Y}**.")
    st.subheader("Flujo metodológico")
    st.markdown("""
    1. Validación de datos, tipos y llaves.
    2. Construcción del panel diario por SKU–tienda.
    3. Pronóstico ETS aditivo a siete días, con Seasonal Naive 7 como respaldo.
    4. Estimación de incertidumbre a partir de errores semanales fuera de muestra.
    5. Construcción de escenarios y cuantiles Q85, Q90 y Q95.
    6. Cálculo de inventario objetivo y pedido sugerido, con cobertura máxima inicial de ocho días.
    """)
    st.subheader("Limitaciones importantes")
    st.warning("""
    - El histórico disponible es corto y no permite validar estacionalidad anual.
    - Las ventas observadas pueden estar censuradas por quiebres de inventario.
    - No se dispone de lead time, órdenes en tránsito, recepciones, MOQ, capacidad física, vida útil ni merma.
    - El tamaño de tienda no se interpreta como capacidad de almacenamiento.
    - El costo esperado es un proxy, no un costo financiero validado.
    - El pronóstico está anclado al corte histórico del 31/03/2024; no debe usarse como orden vigente.
    """)
    st.subheader("Parámetros de la versión")
    st.table(pd.DataFrame({
        "Parámetro":["Horizonte","Nivel predeterminado","Cobertura máxima inicial","Modelo","Escenarios"],
        "Valor":["7 días","Q90","8 días","ETS aditivo semanal","10.000"]
    }))
    st.caption("Aplicación demostrativa. Las recomendaciones deben ser revisadas por Abastecimiento antes de cualquier decisión operativa.")
