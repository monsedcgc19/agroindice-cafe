"""
Inicio.py — Portada del dashboard AgroÍndice Café. Es el punto de entrada
de la app (el archivo que recibe `streamlit run`) -- Streamlit siempre lo muestra 
como la primera entrada del menú lateral, y se muestra un resumen de qué es el
proyecto y accesos a las 3 pantallas del mockup del Prototipo Fachada.
"""

import streamlit as st

from utils.data_loader import model_artifact_calibration_date
from utils.ui import configure_page, style_nav_links

configure_page("AgroÍndice Café")
style_nav_links()

st.title("AgroÍndice Café")
st.subheader("Seguro agrícola indexado para caficultores de Cauca y Nariño")

st.write(
    "Dashboard analítico (no comercial) que valida si variables climáticas y satelitales pueden "
    "reducir el riesgo base de un seguro agrícola indexado para caficultores de Cauca y Nariño. "
    "Compara modelos candidatos y valida un índice climático propuesto -- proyecto del curso "
    "Proyecto Aplicado de Analítica de Datos, MIAD, Universidad de los Andes."
)

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Qué sí hace este prototipo**")
    st.markdown(
        "- Compara 3 modelos candidatos (Random Forest, XGBoost, Ridge + Gradient Boosting) para "
        "predecir NDVI a partir de variables climáticas.\n"
        "- Valida el modelo recomendado contra las metas de la Tabla de Requerimientos.\n"
        "- Propone un índice climático interpretable y umbrales de activación por zona (borrador, no "
        "validado actuarialmente)."
    )
with col2:
    st.markdown("**Qué no hace este prototipo**")
    st.markdown(
        "- No calcula primas ni indemnizaciones reales.\n"
        "- No es una plataforma operativa ni emite pólizas.\n"
        "- No tiene actualización automática de datos climáticos y satelitales"
    )

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
st.markdown("### Ir a una pantalla")

nav1, nav2, nav3 = st.columns(3)
with nav1:
    st.page_link(
        "pages/1_Resumen_Ejecutivo.py",
        label="Resumen ejecutivo",
        icon=":material/bar_chart:",
        use_container_width=True,
    )
    st.caption("KPIs de negocio, riesgo base vs. meta, y estado frente a la Tabla de Requerimientos.")
with nav2:
    st.page_link(
        "pages/2_Validación_Analítica.py",
        label="Validación analítica",
        icon=":material/query_stats:",
        use_container_width=True,
    )
    st.caption("Comparación de modelos candidatos, variables relevantes y comparativo de observado vs. estimado.")
with nav3:
    st.page_link(
        "pages/3_Índice_y_Activaciones.py",
        label="Índice y activaciones",
        icon=":material/flag:",
        use_container_width=True,
    )
    st.caption("Propuesta de índice climático, umbral por zona, historial de activaciones y sección interactiva de predicción NDVI")

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
fecha_modelo = model_artifact_calibration_date()
st.caption(
    f"Modelo vigente: Random Forest (NDVI), calibrado {fecha_modelo:%Y-%m-%d}. Equipo: Daniel Santana, "
    "Martin Cufiño, José Gabriel Paredes y Monserrat Da Costa -- MIAD, Universidad de los Andes."
)
