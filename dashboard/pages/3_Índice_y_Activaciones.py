"""
3_Índice_y_Activaciones.py — Pantalla 3 del mockup del Prototipo Fachada:
índice climático, umbral de activación por zona, e historial de
activaciones históricas/simuladas.

A diferencia de las pantallas 1 y 2 (que solo visualizan resultados ya
validados por el equipo), esta pantalla propone una metodología para 
el índice y el umbral

Metodología propuesta:
- Índice climático = NDVI PREDICHO por el modelo Random Forest ya
  entrenado (estimación derivada solo de clima rezagado, sin usar el NDVI
  observado de la ventana actual) -- consistente con la definición de
  riesgo base de R1 ("1-r² entre el índice climático y la variable de
  pérdida/proxy NDVI").
- Umbral = percentil bajo (ajustable) de la distribución HISTÓRICA de NDVI
  OBSERVADO en esa región (dataset completo, no solo test_final) --
  caracteriza qué tan bajo es "anormalmente bajo" para el régimen normal
  de cada zona.
- Activación = SI índice climático (predicho) < umbral ENTONCES marcar
  ventana como evento potencial.
- Todo se evalúa sobre test_final (nunca visto en el ajuste del modelo),
  igual que en la pantalla de Validación analítica.
"""

import pandas as pd
import streamlit as st

from utils.data_loader import (
    compute_ndvi_threshold,
    load_data_quality_pct,
    model_artifact_calibration_date,
    predict_test_final,
)
from utils.ui import configure_page, icon_svg, render_kpi_card, style_narrow_selectbox

configure_page("Índice y activaciones")
style_narrow_selectbox()

REGION_OPTIONS = {"Ambos (Cauca + Nariño)": None, "Cauca": "Cauca", "Nariño": "Narino"}

st.title("Índice y activaciones")
st.warning(
    "**Esta pantalla es una propuesta de primera iteración, no una calibración actuarial.** El índice, "
    "el umbral y las activaciones que se muestran abajo son ilustrativos/simulados.  "
    "La regla definitiva dependerá de una "
    "validación actuarial futura con datos de pérdida real."
)

# --- Filtros ---
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    departamento_label = st.selectbox("Departamento", list(REGION_OPTIONS.keys()))
with col_f2:
    percentil = st.slider("Percentil del umbral", min_value=5, max_value=40, value=20, step=5)
with col_f3:
    evento_filtro = st.selectbox("Evento", ["Todos", "Solo activaciones"])

region_filtro = REGION_OPTIONS[departamento_label]

# --- Índice, umbral y activaciones sobre test_final ---
pred_df = predict_test_final(region_filtro)
if region_filtro is None:
    umbral_por_region = {r: compute_ndvi_threshold(r, percentil) for r in ("Cauca", "Narino")}
    pred_df["umbral"] = pred_df["region"].map(umbral_por_region)
    umbral_texto = " · ".join(f"{r}: {v:.3f}" for r, v in umbral_por_region.items())
else:
    umbral_unico = compute_ndvi_threshold(region_filtro, percentil)
    pred_df["umbral"] = umbral_unico
    umbral_texto = f"{umbral_unico:.3f}"

pred_df["activacion"] = pred_df["ndvi_predicho"] < pred_df["umbral"]

ultimo = pred_df.sort_values("window_start").iloc[-1]
n_activaciones = int(pred_df["activacion"].sum())
pct_activaciones = 100 * n_activaciones / len(pred_df)
fecha_modelo = model_artifact_calibration_date()

# --- KPIs ---
col1, col2, col3, col4 = st.columns(4)

estado_ultimo = "Bajo umbral (posible activación)" if ultimo["activacion"] else "Por encima del umbral"
render_kpi_card(
    col1,
    icon=icon_svg("chart", "#0284c7"),
    label=f"Índice climático — {ultimo['window_start']:%Y-%m}",
    value=f"{ultimo['ndvi_predicho']:.3f}",
    bg_color="#eff6ff",
    border_color="#bfdbfe",
    delta_text=estado_ultimo,
    delta_good=not bool(ultimo["activacion"]),
)
render_kpi_card(
    col2,
    icon=icon_svg("flag", "#d97706"),
    label=f"Umbral (percentil {percentil}%)",
    value=umbral_texto,
    bg_color="#fff7ed",
    border_color="#fed7aa",
)
render_kpi_card(
    col3,
    icon=icon_svg("bell", "#b42318"),
    label="Activaciones (test_final)",
    value=str(n_activaciones),
    bg_color="#fef3f2",
    border_color="#fecdca",
    delta_text=f"{pct_activaciones:.1f}% de {len(pred_df)} ventanas",
    delta_good=False,
)
render_kpi_card(
    col4,
    icon=icon_svg("clock", "#2563eb"),
    label="Modelo",
    value="Random Forest (NDVI)",
    bg_color="#eef2ff",
    border_color="#c7d2fe",
    delta_text=f"calibrado {fecha_modelo:%Y-%m-%d}",
    delta_good=True,
)

st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)

# --- Regla de activación (borrador) ---
st.subheader("Regla de activación")
st.info(
    f"**SI** índice climático (NDVI predicho por el modelo) < umbral (percentil {percentil}% histórico "
    "de NDVI observado en esa región)\n\n"
    "**Entonces** marcar la ventana como evento potencial de estrés hídrico/vegetativo.\n\n"
    "El percentil, la variable de índice y la ventana temporal son ajustables arriba para explorar "
    "sensibilidad -- esta es una propuesta de primera iteración, no un umbral calibrado con datos de "
    "pérdida real."
)


st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# --- Historial de activaciones ---
st.subheader("Historial de activaciones (test_final)")
tabla_hist = pred_df if evento_filtro == "Todos" else pred_df[pred_df["activacion"]]
tabla_hist = tabla_hist.sort_values("window_start", ascending=False)

tabla_mostrar = pd.DataFrame(
    {
        "Periodo": tabla_hist["window_start"].dt.strftime("%Y-%m"),
        "Zona": tabla_hist["region"],
        "Índice (NDVI predicho)": tabla_hist["ndvi_predicho"].map(lambda v: f"{v:.3f}"),
        "Umbral": tabla_hist["umbral"].map(lambda v: f"{v:.3f}"),
        "Estado": tabla_hist["activacion"].map(lambda a: "🔴 Activación" if a else "— Normal"),
    }
)
st.dataframe(tabla_mostrar, use_container_width=True, hide_index=True)
st.caption(f"{len(tabla_hist)} de {len(pred_df)} ventanas mostradas · test_final · {departamento_label}.")


st.info(
    "**Nota metodológica**: se eligió NDVI predicho por el modelo como índice climático porque es "
    "funcionalmente equivalente a lo que R1 y R5 ya validan (riesgo base = 1−r² contra el proxy de "
    "pérdida; correlación de Pearson del modelo) y conserva la latencia de una variable climática -- no "
    "depende de la lectura satelital ni de su enmascarado por nubes. Una alternativa más simple y "
    "auditable -- usar una variable climática cruda (p. ej. déficit hídrico) directamente como índice, "
    "sin pasar por el modelo -- queda como posible iteración futura a evaluar con el equipo, sobre todo "
    "si se prioriza la explicabilidad frente a directivos no técnicos por encima de aprovechar toda la "
    "señal multivariada que ya capturó el modelo."
)

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# --- Cobertura, calidad y trazabilidad ---
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("**Cobertura geográfica**")
    st.caption(
        "Resultados limitados a Cauca y Nariño, como promedio departamental completo -- ver "
        "advertencia de representatividad geográfica más abajo."
    )
with col_b:
    st.markdown("**Calidad de datos**")
    st.caption(
        f"{load_data_quality_pct():.2f}% de registros válidos -- ver "
        "data/processed/diccionario_datos.md para el detalle de nulos por variable."
    )
with col_c:
    st.markdown("**Trazabilidad**")
    st.caption(
        f"Modelo Random Forest (NDVI), calibrado {fecha_modelo:%Y-%m-%d}. Metodología del índice y el "
        "umbral: ver el docstring de esta página y CONTEXT.md."
    )

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# --- Advertencia obligatoria de cobertura geográfica (R9) ---
st.warning(
    "**Representatividad geográfica**: las variables climáticas de entrada son un promedio sobre el "
    "polígono departamental completo de Cauca y Nariño (FAO/GAUL level1), que incluye franja Pacífica y "
    "piedemonte amazónico -- no son específicas de la zona cafetera andina. "
    "'Limitación conocida: el clima es un promedio departamental'."
)
