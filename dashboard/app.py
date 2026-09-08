"""
app.py — Punto de entrada mínimo del dashboard. Solo valida que las tres
fuentes cacheadas en utils/data_loader.py cargan correctamente (rutas y
cacheo); todavía no construye ninguna de las 3 pantallas del mockup del
Prototipo Fachada.
"""

import streamlit as st

from utils.data_loader import load_dataset, load_model_comparison, load_winning_model
from utils.ui import configure_page

configure_page("AgroÍndice Café")

st.title("AgroÍndice Café — validación de carga")

st.header("Dataset final (data/processed/dataset_modelo.csv)")
dataset = load_dataset()
st.dataframe(dataset.head())

st.header("Comparación de modelos (results/model_comparison.csv)")
comparison = load_model_comparison()
st.dataframe(comparison)

st.header("Modelo ganador (models/artifacts/random_forest_ndvi.joblib)")
model = load_winning_model()
st.write(f"Modelo cargado correctamente: `{type(model).__name__}`")
st.json(model.get_params())
