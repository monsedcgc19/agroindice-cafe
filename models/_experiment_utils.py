"""
_experiment_utils.py — Utilidades compartidas por los scripts de modelado en
models/: split cronológico train/test, preparación de features (X, y) sin
fuga de información, y registro de resultados en results/.

No requiere autenticación ni conexión externa. Solo lee
data/processed/dataset_modelo.csv (vía el script que la importe) y escribe en
results/.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import r2_score, root_mean_squared_error

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
LOG_PATH = RESULTS_DIR / "experiment_log.csv"
COMPARISON_PATH = RESULTS_DIR / "model_comparison.csv"

LOG_COLUMNS = [
    "timestamp",
    "modelo",
    "tipo_run",
    "y_variable",
    "fecha_corte",
    "hiperparametros",
    "r2",
    "rmse",
    "pearson",
    "notas",
]

COMPARISON_COLUMNS = ["modelo", "y_variable", "r2", "rmse", "pearson", "actualizado"]

# Regiones fijas del proyecto (Cauca, Nariño) — se fuerzan como categorías al
# hacer one-hot de `region` para que train_val y test_final generen siempre
# las mismas columnas dummy, sin importar qué regiones aparezcan en cada split.
REGIONS = ["Cauca", "Narino"]

# Columnas que no son features de modelado: identificadores de fecha/ventana
# y metadatos constantes (et_resolution siempre vale "monthly", no aporta
# señal).
DATE_COLS = ["window_start", "window_end"]
NON_FEATURE_COLS = ["et_resolution"]


def split_train_val_test(df, fecha_col, frac_test_final=0.15):
    """Ordena por `fecha_col` y separa el tramo cronológicamente más reciente
    (~frac_test_final de las fechas únicas) como test_final — se usa una sola
    vez, al final, nunca durante tuning. El resto se devuelve como
    train_val. El corte es por fecha, no por y_variable: se llama una sola
    vez por script."""
    df_sorted = df.sort_values(fecha_col).reset_index(drop=True)
    fechas_unicas = sorted(df_sorted[fecha_col].unique())
    n = len(fechas_unicas)
    n_test = max(1, round(n * frac_test_final))
    fecha_corte = fechas_unicas[n - n_test]

    train_val = df_sorted[df_sorted[fecha_col] < fecha_corte].reset_index(drop=True)
    test_final = df_sorted[df_sorted[fecha_col] >= fecha_corte].reset_index(drop=True)

    print(f"split_train_val_test (fecha_col={fecha_col!r}, frac_test_final={frac_test_final}):")
    print(f"  train_val:  {fechas_unicas[0]} -> {fechas_unicas[n - n_test - 1]}  ({len(train_val)} filas)")
    print(f"  test_final: {fecha_corte} -> {fechas_unicas[-1]}  ({len(test_final)} filas)")

    return train_val, test_final


def prepare_features(df, target_col):
    """Devuelve (X, y) para predecir `target_col` ('ndvi' o 'evi').

    Excluye de X: el target actual, el otro índice de vegetación (NDVI y EVI
    son casi colineales entre sí — incluir uno al predecir el otro sería
    fuga de información), `region` cruda (se reemplaza por dummies fijas
    sobre REGIONS), `et_resolution` (metadato constante, no señal), y las
    columnas de fecha/identificador de ventana.
    """
    if target_col not in ("ndvi", "evi"):
        raise ValueError(f"target_col debe ser 'ndvi' o 'evi', recibido: {target_col!r}")
    other_target = "evi" if target_col == "ndvi" else "ndvi"

    y = df[target_col].copy()

    drop_cols = [target_col, other_target, *NON_FEATURE_COLS, *DATE_COLS]
    drop_cols = [c for c in drop_cols if c in df.columns]
    X = df.drop(columns=drop_cols).copy()

    X["region"] = pd.Categorical(X["region"], categories=REGIONS)
    region_dummies = pd.get_dummies(X["region"], prefix="region")
    X = pd.concat([X.drop(columns=["region"]), region_dummies], axis=1)

    return X, y


def compute_metrics(y_true, y_pred):
    """r2, rmse, pearson — las tres métricas que se registran en cada run."""
    r2 = r2_score(y_true, y_pred)
    rmse = root_mean_squared_error(y_true, y_pred)
    pearson = pearsonr(y_true, y_pred)[0]
    return r2, rmse, pearson


def log_run(modelo, tipo_run, y_variable, fecha_corte, hiperparametros, r2, rmse, pearson, notas=""):
    """Agrega una fila con timestamp a results/experiment_log.csv (crea el
    archivo con encabezados si no existe). No sobreescribe corridas previas."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "modelo": modelo,
        "tipo_run": tipo_run,
        "y_variable": y_variable,
        "fecha_corte": str(fecha_corte),
        "hiperparametros": json.dumps(hiperparametros, default=str) if hiperparametros is not None else "",
        "r2": r2,
        "rmse": rmse,
        "pearson": pearson,
        "notas": notas,
    }
    file_exists = LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def upsert_model_comparison(modelo, y_variable, r2, rmse, pearson):
    """En results/model_comparison.csv: reemplaza la fila de ese
    modelo+y_variable si ya existe, o la agrega si no. A diferencia de
    experiment_log.csv (histórico, se acumula), esta tabla siempre refleja
    el mejor/último resultado por combinación modelo+variable."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if COMPARISON_PATH.exists():
        df = pd.read_csv(COMPARISON_PATH)
    else:
        df = pd.DataFrame(columns=COMPARISON_COLUMNS)

    mask = (df["modelo"] == modelo) & (df["y_variable"] == y_variable)
    new_row = {
        "modelo": modelo,
        "y_variable": y_variable,
        "r2": r2,
        "rmse": rmse,
        "pearson": pearson,
        "actualizado": datetime.now().isoformat(timespec="seconds"),
    }
    if mask.any():
        for col, val in new_row.items():
            df.loc[mask, col] = val
    elif df.empty:
        df = pd.DataFrame([new_row])
    else:
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(COMPARISON_PATH, index=False)
