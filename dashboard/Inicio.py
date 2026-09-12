"""
Inicio.py — Portada del dashboard AgroÍndice Café. Es el punto de entrada
de la app (el archivo que recibe `streamlit run`) -- Streamlit siempre lo muestra
como la primera entrada del menú lateral, y se muestra un resumen de qué es el
proyecto y accesos a las 3 pantallas del mockup del Prototipo Fachada.
"""

import streamlit as st

from utils.data_loader import model_artifact_calibration_date
from utils.ui import configure_page, icon_svg, render_info_card, style_nav_links

configure_page("AgroÍndice Café")
style_nav_links()

# --- Portada: título, subtítulo y descripción en una sola franja de marca ---
st.markdown(
    """
    <div style="background-color:#faf6f1; border:1px solid #e7dcc9; border-radius:16px;
                padding:32px 36px; margin-bottom:28px;">
        <h1 style="margin:0 0 6px 0; color:#101828;">AgroÍndice Café</h1>
        <div style="font-size:18px; font-weight:600; color:#6b4423; margin-bottom:14px;">
            Seguro agrícola indexado para caficultores de Cauca y Nariño
        </div>
        <div style="font-size:15px; color:#475467; line-height:1.65; max-width:900px;">
            Dashboard analítico (no comercial) que valida si variables climáticas y satelitales pueden
            reducir el riesgo base de un seguro agrícola indexado para caficultores de Cauca y Nariño.
            Compara modelos candidatos y valida un índice climático propuesto -- proyecto del curso
            Proyecto Aplicado de Analítica de Datos, MIAD, Universidad de los Andes.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
render_info_card(
    col1,
    icon=icon_svg("check", "#16a34a", size=24, margin_bottom=0),
    title="Qué sí hace este prototipo",
    items=[
        "Compara 3 modelos candidatos (Random Forest, XGBoost, Ridge + Gradient Boosting) "
        "para predecir NDVI a partir de variables climáticas.",
        "Valida el modelo recomendado contra las metas de la Tabla de Requerimientos.",
        "Propone un índice climático interpretable y umbrales de activación por zona "
        "(borrador, no validado actuarialmente).",
    ],
    bg_color="#f0fdf4",
    border_color="#bbf7d0",
    height=225,
)
render_info_card(
    col2,
    icon=icon_svg("x_circle", "#dc2626", size=24, margin_bottom=0),
    title="Qué no hace este prototipo",
    items=[
        "No calcula primas ni indemnizaciones reales.",
        "No es una plataforma operativa ni emite pólizas.",
        "No tiene actualización automática de datos climáticos y satelitales.",
    ],
    bg_color="#fef3f2",
    border_color="#fecdca",
    height=225,
)

st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
st.markdown("### Ir a una pantalla")

nav1, nav2, nav3 = st.columns(3)
with nav1:
    with st.container(border=True):
        st.page_link(
            "pages/1_Resumen_Ejecutivo.py",
            label="Resumen ejecutivo",
            icon=":material/bar_chart:",
            use_container_width=True,
        )
        st.caption("KPIs de negocio, riesgo base vs. meta, y estado frente a la Tabla de Requerimientos.")
with nav2:
    with st.container(border=True):
        st.page_link(
            "pages/2_Validación_Analítica.py",
            label="Validación analítica",
            icon=":material/query_stats:",
            use_container_width=True,
        )
        st.caption("Comparación de modelos candidatos, variables relevantes y comparativo de observado vs. estimado.")
with nav3:
    with st.container(border=True):
        st.page_link(
            "pages/3_Índice_y_Activaciones.py",
            label="Índice y activaciones",
            icon=":material/flag:",
            use_container_width=True,
        )
        st.caption("Propuesta de índice climático, umbral por zona, historial de activaciones y sección interactiva de predicción NDVI")

st.divider()
fecha_modelo = model_artifact_calibration_date()
st.caption(
    f"Modelo vigente: Random Forest (NDVI), calibrado {fecha_modelo:%Y-%m-%d}. Equipo: Daniel Santana, "
    "Martin Cufiño, José Gabriel Paredes y Monserrat Da Costa -- MIAD, Universidad de los Andes."
)
