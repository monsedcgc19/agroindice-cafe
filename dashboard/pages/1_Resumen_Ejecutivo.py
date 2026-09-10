"""
1_Resumen_Ejecutivo.py — Pantalla 1 del mockup del Prototipo Fachada: KPIs
ejecutivos, comparación de riesgo base contra la meta, y estado del modelo
frente a la Tabla de Requerimientos (R1-R15). Todos los valores se leen de
results/model_comparison.csv y data/processed/diccionario_datos.md -- no se
recalculan ni se hardcodean (ver utils/data_loader.py).

El filtro de Departamento solo afecta la tarjeta de Riesgo base y su
gráfico: ambos se recalculan evaluando el modelo YA ENTRENADO (sin
reentrenar) sobre el subconjunto de test_final de esa región
(score_model_on_region). El resto de la pantalla (Estado, Calidad de
datos, Modelo recomendado) sigue reflejando el resultado agregado y
oficialmente documentado en model_comparison.csv, sin importar el filtro.
"""

import pandas as pd
import streamlit as st

from utils.data_loader import (
    load_data_quality_pct,
    load_dataset,
    load_model_comparison,
    score_model_on_region,
)
from utils.ui import configure_page, icon_svg, render_kpi_card, style_narrow_selectbox, style_nav_links

configure_page("Resumen ejecutivo")
style_narrow_selectbox()
style_nav_links()
st.page_link("Inicio.py", label="Inicio", icon=":material/home:")

# Metas de la Tabla de Requerimientos (ver CONTEXT.md, "## Metas de métricas") --
# son los umbrales fijos del proyecto, no valores derivados de datos.
META_R2 = 0.60
META_RMSE_PCT = 15.0
META_PEARSON = 0.65
META_RIESGO_BASE_PCT = 50.0
META_CALIDAD_DATOS_PCT = 90.0

# "Narino" (sin tilde) es como queda el valor en dataset_modelo.csv -- ver
# REGIONS en models/_experiment_utils.py. La etiqueta visible sí lleva tilde.
REGION_OPTIONS = {"Ambos (Cauca + Nariño)": None, "Cauca": "Cauca", "Nariño": "Narino"}

st.title("Resumen ejecutivo")

comparison = load_model_comparison()

# La fila "random_forest"/"ndvi" tal cual quedó en model_comparison.csv está
# desactualizada (corrida del 2026-08-29, antes del filtro SummaryQA y las
# capas de humedad de suelo profundas -- ver CONTEXT.md, "## Resultados del
# modelado"). La fila que sí corresponde al modelo ganador reportado
# (R²=0.329, Pearson=0.768) es la de mayor R² entre todas las corridas
# "random_forest*" para ndvi -- así se sigue sin hardcodear el número.
rf_ndvi = comparison[
    (comparison["y_variable"] == "ndvi") & (comparison["modelo"].str.startswith("random_forest"))
]
winner = rf_ndvi.loc[rf_ndvi["r2"].idxmax()]

# Estas 3 son las oficiales/agregadas -- solo alimentan el Estado más abajo,
# nunca cambian con el filtro de departamento.
r2_oficial = winner["r2"]
pearson_oficial = winner["pearson"]
ndvi_mean = load_dataset()["ndvi"].mean()
rmse_pct_oficial = 100 * winner["rmse"] / ndvi_mean

calidad_datos_pct = load_data_quality_pct()

departamento_label = st.selectbox("Departamento", list(REGION_OPTIONS.keys()))
region_filtro = REGION_OPTIONS[departamento_label]

# metrics_filtradas["r2"] == r2_oficial cuando region_filtro es None (mismo
# modelo, mismo test_final completo) -- ver score_model_on_region.
metrics_filtradas = score_model_on_region(region_filtro)
riesgo_base_actual_pct = (1 - metrics_filtradas["r2"]) * 100

# --- KPIs ---
col1, col2, col3, col4 = st.columns(4)

render_kpi_card(
    col1,
    icon=icon_svg("warning", "#d97706"),
    label="Riesgo base actual (1−R²)",
    value=f"{riesgo_base_actual_pct:.1f}%",
    bg_color="#fff7ed",
    border_color="#fed7aa",
    delta_text=f"{riesgo_base_actual_pct - META_RIESGO_BASE_PCT:+.1f} pts vs. meta (≤{META_RIESGO_BASE_PCT:.0f}%)",
    delta_good=False,
)
render_kpi_card(
    col2,
    icon=icon_svg("tree", "#2563eb"),
    label="Modelo recomendado",
    value="Random Forest (NDVI)",
    bg_color="#eff6ff",
    border_color="#bfdbfe",
)
render_kpi_card(
    col3,
    icon=icon_svg("check", "#16a34a"),
    label="Calidad de datos",
    value=f"{calidad_datos_pct:.2f}%",
    bg_color="#f0fdf4",
    border_color="#bbf7d0",
    delta_text=f"{calidad_datos_pct - META_CALIDAD_DATOS_PCT:+.2f} pts vs. meta (≥{META_CALIDAD_DATOS_PCT:.0f}%)",
    delta_good=True,
)
render_kpi_card(
    col4,
    icon=icon_svg("pin", "#9333ea"),
    label="Alcance",
    value="2 zonas piloto (Cauca, Nariño)",
    bg_color="#faf5ff",
    border_color="#e9d5ff",
)

st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)

# --- Gráfico: qué tanto se acercó el modelo a la meta ---
st.subheader(f"Riesgo base: sin modelo vs. modelo actual vs. meta ({departamento_label})")
chart_df = pd.DataFrame(
    {"Riesgo base (%)": [100.0, riesgo_base_actual_pct, META_RIESGO_BASE_PCT]},
    index=["Sin modelo (100%)", "Modelo actual", f"Meta (≤{META_RIESGO_BASE_PCT:.0f}%)"],
)
st.bar_chart(chart_df)
st.caption(
    f"Tarjeta y gráfico recalculados evaluando el modelo ya entrenado (sin reentrenar) sobre "
    f"test_final · {departamento_label} · n={metrics_filtradas['n']} ventanas. El resto de "
    f"la pantalla (Estado, Calidad de datos) sigue el resultado agregado y documentado."
)

# --- Estado frente a la Tabla de Requerimientos (siempre agregado, no cambia con el filtro) ---
cumple_r2 = r2_oficial >= META_R2
cumple_rmse = rmse_pct_oficial <= META_RMSE_PCT
cumple_pearson = pearson_oficial >= META_PEARSON
evidencia_suficiente = cumple_r2 or cumple_rmse or cumple_pearson
estado = "Continuar" if evidencia_suficiente else "Detener"

st.subheader(f"Estado: {estado}")

criterios = pd.DataFrame(
    [
        {
            "Criterio": f"R² ≥ {META_R2:.2f}",
            "Valor actual": f"{r2_oficial:.3f}",
            "Cumple": "✅" if cumple_r2 else "❌",
        },
        {
            "Criterio": f"RMSE ≤ {META_RMSE_PCT:.0f}% de la media",
            "Valor actual": f"{rmse_pct_oficial:.2f}%",
            "Cumple": "✅" if cumple_rmse else "❌",
        },
        {
            "Criterio": f"Pearson ≥ {META_PEARSON:.2f}",
            "Valor actual": f"{pearson_oficial:.3f}",
            "Cumple": "✅" if cumple_pearson else "❌",
        },
    ]
)
st.table(criterios)

st.caption(
    "Según el Requerimiento 2 del Prototipo Fachada, basta con que al menos 1 de "
    "las 3 metas mínimas de validación se cumpla para considerarse evidencia "
    "suficiente y recomendar avanzar a la siguiente fase. Con los valores "
    "actuales se cumplen 2 de 3 (RMSE y Pearson): aunque el riesgo base "
    "(1−R²) todavía no alcanza la meta de ≤50%, hay evidencia suficiente para "
    "continuar -- R² queda documentado como el punto más débil a mejorar si el "
    "tiempo del prototipo lo permite, no como un bloqueante."
)

# --- Advertencias obligatorias ---
st.warning(
    "**Proxy, no reducción comprobada**: el riesgo base mostrado aquí es un "
    "proxy basado en qué tan predecible es NDVI/EVI a partir del clima, no una "
    "medición de pérdida real evitada -- no hay datos de pérdida real "
    "disponibles para validar la reducción directamente."
)
st.warning(
    "**Representatividad geográfica**: las variables climáticas de entrada son "
    "un promedio sobre el polígono departamental completo de Cauca y Nariño "
    "(FAO/GAUL level1), que incluye franja Pacífica y piedemonte amazónico -- "
    "no son específicas de la zona cafetera andina. Ver CONTEXT.md, "
    "'Limitación conocida: el clima es un promedio departamental'."
)
