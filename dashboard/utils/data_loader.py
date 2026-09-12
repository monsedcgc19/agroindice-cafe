"""
data_loader.py — Carga cacheada de los artefactos que consume el dashboard:
dataset final, tabla de comparación de modelos, y el modelo ganador
serializado. Ninguna de estas fuentes se recalcula ni reentrena aquí -- solo
se leen tal cual las dejó la fase de modelado (ver CONTEXT.md).
"""

import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BASE_DIR / "data" / "processed" / "dataset_modelo.csv"
MODEL_COMPARISON_PATH = BASE_DIR / "results" / "model_comparison.csv"
MODEL_ARTIFACT_PATH = BASE_DIR / "models" / "artifacts" / "random_forest_ndvi.joblib"
DATA_DICTIONARY_PATH = BASE_DIR / "data" / "processed" / "diccionario_datos.md"
MODELS_DIR = BASE_DIR / "models"


def _ensure_models_on_path():
    """models/_experiment_utils.py no es un paquete importable normalmente
    (sin __init__.py, pensado para correr scripts dentro de models/) --
    agregar su carpeta a sys.path deja reusar exactamente la misma función
    de split y de preparación de features que generó el modelo, en vez de
    reimplementarla en el dashboard y arriesgar que se desincronice."""
    models_dir = str(MODELS_DIR)
    if models_dir not in sys.path:
        sys.path.insert(0, models_dir)


@st.cache_data
def load_dataset():
    return pd.read_csv(DATASET_PATH, parse_dates=["window_start", "window_end"])


@st.cache_data
def load_model_comparison():
    return pd.read_csv(MODEL_COMPARISON_PATH)


@st.cache_resource
def load_winning_model():
    return joblib.load(MODEL_ARTIFACT_PATH)


@st.cache_data
def load_data_quality_pct():
    """% de registros válidos = 100 - promedio de '% nulos' por columna,
    tal como quedó documentado en diccionario_datos.md (05_build_dataset.py).
    No re-lee dataset_modelo.csv ni recalcula nulos -- toma la cifra ya
    reportada por columna en la tabla del diccionario."""
    text = DATA_DICTIONARY_PATH.read_text(encoding="utf-8")
    null_pcts = []
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 4:
            continue
        try:
            null_pcts.append(float(cells[3].rstrip("%")))
        except ValueError:
            continue  # fila de encabezado o separador de la tabla markdown
    return 100 - (sum(null_pcts) / len(null_pcts))


@st.cache_data
def load_test_final():
    """test_final tal como lo usó random_forest.py para las métricas ya
    reportadas: mismo split cronológico (85/15 por fecha, ver
    _experiment_utils.split_train_val_test) que generó el modelo -- no es
    una partición nueva calculada en el dashboard."""
    _ensure_models_on_path()
    from _experiment_utils import split_train_val_test

    _, test_final = split_train_val_test(load_dataset(), fecha_col="window_start", frac_test_final=0.15)
    return test_final


@st.cache_data
def score_model_on_region(region=None):
    """R², RMSE y Pearson del modelo YA ENTRENADO (sin reentrenar) sobre
    test_final, opcionalmente filtrado a una región ("Cauca" o "Narino").
    region=None evalúa sobre Cauca+Nariño juntos, lo que coincide
    exactamente con la fila ganadora de results/model_comparison.csv."""
    _ensure_models_on_path()
    from _experiment_utils import compute_metrics, prepare_features

    test_final = load_test_final()
    subset = test_final if region is None else test_final[test_final["region"] == region]
    X, y = prepare_features(subset, "ndvi")
    y_pred = load_winning_model().predict(X)
    r2, rmse, pearson = compute_metrics(y, y_pred)
    return {"r2": r2, "rmse": rmse, "pearson": pearson, "n": len(y)}


@st.cache_data
def predict_test_final(region=None):
    """Predicciones del modelo YA ENTRENADO (sin reentrenar) sobre
    test_final, con fecha y región -- para graficar observado vs. estimado
    en el tiempo. Mismo filtro de región que score_model_on_region."""
    _ensure_models_on_path()
    from _experiment_utils import prepare_features

    test_final = load_test_final()
    subset = test_final if region is None else test_final[test_final["region"] == region]
    X, y = prepare_features(subset, "ndvi")
    y_pred = load_winning_model().predict(X)

    out = subset[["window_start", "region"]].reset_index(drop=True).copy()
    out["ndvi_real"] = y.reset_index(drop=True)
    out["ndvi_predicho"] = y_pred
    out["error_abs"] = (out["ndvi_real"] - out["ndvi_predicho"]).abs()
    return out.sort_values("window_start").reset_index(drop=True)


@st.cache_data
def load_feature_importances(top_n=10):
    """Importancia de features del modelo ganador YA ENTRENADO (sin
    reentrenar) -- lee feature_importances_/feature_names_in_ directamente
    del RandomForestRegressor serializado, no recalcula nada."""
    model = load_winning_model()
    importances = pd.Series(model.feature_importances_, index=model.feature_names_in_)
    return importances.sort_values(ascending=False).head(top_n)


@st.cache_data
def load_feature_matrix():
    """Matriz de features (X) del dataset COMPLETO, ya con las mismas
    dummies de región que ve el modelo (prepare_features) -- fuente única
    de promedios y rangos históricos para la predicción interactiva, así
    los nombres/orden de columnas quedan garantizados idénticos a
    model.feature_names_in_ sin repetir la lógica de dummy-encoding."""
    _ensure_models_on_path()
    from _experiment_utils import prepare_features

    X, _ = prepare_features(load_dataset(), "ndvi")
    return X


@st.cache_data
def compute_ndvi_threshold(region, percentile):
    """Umbral de activación = percentil `percentile` (0-100) de la
    distribución HISTÓRICA de NDVI observado (dataset_modelo.csv completo,
    no solo test_final) para una región puntual ("Cauca" o "Narino").

    Es una calibración descriptiva -- caracteriza qué tan bajo es "bajo"
    para el NDVI normal de esa zona -- no una predicción, así que se apoya
    en todo el histórico disponible (train_val + test_final) sin que eso
    sea fuga de información hacia el modelo. Ver la pantalla de Índice y
    Activaciones para la regla completa; es una propuesta de primera
    iteración, no un umbral actuarialmente validado."""
    df = load_dataset()
    serie = df.loc[df["region"] == region, "ndvi"]
    return serie.quantile(percentile / 100)


def model_artifact_calibration_date():
    """Fecha de modificación del .joblib serializado -- versión/fecha
    visible junto al resultado (R10), sin inventar un número de versión."""
    return datetime.fromtimestamp(MODEL_ARTIFACT_PATH.stat().st_mtime)
