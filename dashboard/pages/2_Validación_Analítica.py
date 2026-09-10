"""
2_Validacion_Analitica.py — Pantalla 2 del mockup del Prototipo Fachada:
comparación de modelos candidatos, variables más relevantes, y observado
vs. estimado en el tiempo para el modelo ganador. Ver CONTEXT.md,
"## Resultados del modelado".

Adaptaciones respecto al mockup original (docs/Entrega Prototipo
Fachada.pdf, sección 10, Pantalla 2), ahora que el modelado ya se hizo:
- Los modelos candidatos reales fueron Random Forest, XGBoost y un
  ensemble Ridge + Gradient Boosting -- no SVM ni redes neuronales, que
  nunca se probaron (ver CONTEXT.md).
- La columna "Recall" del mockup no aplica a un problema de regresión; se
  reemplaza por Pearson, una de las 3 métricas oficiales de validación
  (R3-R5 de la Tabla de Requerimientos).
- La variable Y ya se decidió (NDVI, no EVI) -- ver "Decisión de equipo
  (2026-09-05)" en CONTEXT.md -- así que esta pantalla no repite el filtro
  "Objetivo" del mockup como una elección todavía abierta; el resultado de
  EVI queda solo como referencia en el pie de la tabla.
"""

import altair as alt
import pandas as pd
import streamlit as st

from utils.data_loader import (
    load_dataset,
    load_feature_importances,
    load_model_comparison,
    predict_test_final,
)
from utils.ui import configure_page, style_narrow_selectbox, style_nav_links

configure_page("Validación analítica")
style_narrow_selectbox()
style_nav_links()
st.page_link("Inicio.py", label="Inicio", icon=":material/home:")

REGION_OPTIONS = {"Ambos (Cauca + Nariño)": None, "Cauca": "Cauca", "Nariño": "Narino"}
# Familias de modelo realmente probadas -> etiqueta de despliegue.
# Cada una puede tener varias corridas versionadas en model_comparison.csv
# (p. ej. random_forest_v2/v3/v4_features); se toma la de mayor R² de cada
# familia, igual que en la pantalla de Resumen ejecutivo.
FAMILIES = {
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "ridge_gradient_boosting": "Ridge + Gradient Boosting",
}

st.title("Validación analítica")

ndvi_mean = load_dataset()["ndvi"].mean()
comparison = load_model_comparison()

# --- Comparación de modelos candidatos ---
st.subheader("Comparación de modelos candidatos (NDVI)")

ndvi_rows = comparison[comparison["y_variable"] == "ndvi"]
filas = []
for prefix, display_name in FAMILIES.items():
    subset = ndvi_rows[ndvi_rows["modelo"].str.startswith(prefix)]
    if subset.empty:
        continue
    best = subset.loc[subset["r2"].idxmax()]
    filas.append({"Modelo": display_name, "r2": best["r2"], "rmse": best["rmse"], "pearson": best["pearson"]})

tabla = pd.DataFrame(filas)
mejor_idx = tabla["r2"].idxmax()
tabla["Estado"] = "Evaluado"
tabla.loc[mejor_idx, "Estado"] = "✅ Recomendado"

tabla_mostrar = pd.DataFrame(
    {
        "Modelo": tabla["Modelo"],
        "R²": tabla["r2"].map(lambda v: f"{v:.3f}"),
        "RMSE (% de la media)": (100 * tabla["rmse"] / ndvi_mean).map(lambda v: f"{v:.2f}%"),
        "Pearson": tabla["pearson"].map(lambda v: f"{v:.3f}"),
        "Estado": tabla["Estado"],
    }
)
st.table(tabla_mostrar)

# Referencia de EVI (variable Y descartada) -- solo entre random_forest y
# xgboost, el ensemble nunca se evaluó para EVI (ver CONTEXT.md).
evi_rows = comparison[
    (comparison["y_variable"] == "evi") & (comparison["modelo"].str.startswith(("random_forest", "xgboost")))
]
mejor_evi = evi_rows.loc[evi_rows["r2"].idxmax()]
mejor_evi_familia = "Random Forest" if mejor_evi["modelo"].startswith("random_forest") else "XGBoost"
st.caption(
    f"Validación con separación temporal (85% train_val / 15% test_final, corte cronológico) para las 3 "
    f"familias. La variable Y ya se decidió como NDVI -- el mismo ejercicio con EVI (descartado) alcanzó "
    f"como máximo R²={mejor_evi['r2']:.3f} ({mejor_evi_familia}), peor que las 3 familias con NDVI en esta "
    f"tabla. Ver CONTEXT.md, '## Resultados del modelado'."
)

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# --- Variables más relevantes ---
st.subheader("Variables más relevantes (Random Forest, NDVI)")
importancias = load_feature_importances(top_n=10)
# st.bar_chart ordena el eje categórico alfabéticamente sin importar el
# orden del DataFrame -- se usa Altair directamente para fijar el orden por
# importancia (más relevante arriba) y darle un color distinto a cada barra.
chart_df = importancias.rename(lambda c: c.replace("_", " ")).reset_index()
chart_df.columns = ["variable", "importancia"]

chart = (
    alt.Chart(chart_df)
    .mark_bar()
    .encode(
        x=alt.X("importancia:Q", title="Importancia"),
        y=alt.Y("variable:N", title=None, sort="-x"),
        color=alt.Color("variable:N", legend=None, scale=alt.Scale(scheme="tableau10")),
        tooltip=["variable", "importancia"],
    )
)
st.altair_chart(chart, use_container_width=True)
st.caption(
    "Importancia de features (impureza/Gini) del modelo ya entrenado -- no se recalcula. Nombres de "
    "columna tal como aparecen en data/processed/diccionario_datos.md (ahí está la unidad y fuente de "
    "cada una)."
)

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# --- Observado vs. estimado en el tiempo ---
st.subheader("Observado vs. estimado en el tiempo (Random Forest, NDVI)")
departamento_label = st.selectbox("Departamento", list(REGION_OPTIONS.keys()), key="depto_pantalla2")
region_filtro = REGION_OPTIONS[departamento_label]

pred_df = predict_test_final(region_filtro)
if region_filtro is None:
    wide = pred_df.pivot(index="window_start", columns="region", values=["ndvi_real", "ndvi_predicho"])
    wide.columns = [f"{'Real' if metrica == 'ndvi_real' else 'Predicho'} — {region}" for metrica, region in wide.columns]
else:
    wide = pred_df.set_index("window_start")[["ndvi_real", "ndvi_predicho"]].rename(
        columns={"ndvi_real": "Real", "ndvi_predicho": "Predicho"}
    )
st.line_chart(wide)
st.caption(
    f"test_final · {departamento_label} · n={len(pred_df)} ventanas · predicciones del modelo ya "
    f"entrenado (sin reentrenar) sobre datos que nunca vio durante el ajuste ni el tuning."
)

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# --- Advertencia obligatoria de cobertura geográfica (R9: presente en el 100% de las vistas con resultados) ---
st.warning(
    "**Representatividad geográfica**: las variables climáticas de entrada son un promedio sobre el "
    "polígono departamental completo de Cauca y Nariño (FAO/GAUL level1), que incluye franja Pacífica y "
    "piedemonte amazónico -- no son específicas de la zona cafetera andina. Ver CONTEXT.md, "
    "'Limitación conocida: el clima es un promedio departamental'."
)
