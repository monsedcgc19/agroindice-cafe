"""
xgboost_model.py — XGBoost para predecir NDVI y EVI (ventana MODIS actual) a
partir de clima ERA5/FLDAS rezagado. Segundo modelo candidato, formalizado a
partir del prototipo en notebooks/prototipo_xgboost.ipynb. Corre ambas
variables Y (`ndvi`, `evi`) en una sola ejecución.

Input:
  - data/processed/dataset_modelo.csv

Output:
  - results/experiment_log.csv (append: baseline y tuned, por y_variable)
  - results/model_comparison.csv (upsert: resultado tuned, por y_variable)
  - results/grid_search_raw/xgboost_ndvi.csv
  - results/grid_search_raw/xgboost_evi.csv

No requiere autenticación ni conexión externa.

Metodología (idéntica a random_forest.py, para que los resultados sean
directamente comparables):
  - Split cronológico único (no por y_variable): 85% train_val / 15%
    test_final más reciente. test_final se toca exactamente dos veces por
    y_variable (evaluación baseline y evaluación tuned) — nunca durante el
    GridSearchCV, que corre solo sobre train_val con TimeSeriesSplit como cv.
  - Valores NaN en features (p. ej. et_mm_lag1 en la primera ventana de cada
    región) no se imputan: XGBRegressor soporta NaN nativamente (verificado
    aparte, igual que se hizo con RandomForestRegressor).
"""

import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

from _experiment_utils import (
    RESULTS_DIR,
    compute_metrics,
    log_run,
    prepare_features,
    split_train_val_test,
    upsert_model_comparison,
)
from pathlib import Path

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "dataset_modelo.csv"
GRID_SEARCH_DIR = RESULTS_DIR / "grid_search_raw"

PARAM_GRID = {
    "n_estimators": [100, 200, 400],
    "max_depth": [3, 5, 7],
    "learning_rate": [0.05, 0.1],
}
GRID_KEYS = list(PARAM_GRID.keys())
N_CV_SPLITS = 5
RANDOM_STATE = 42
Y_VARIABLES = ["ndvi", "evi"]


def evaluate(model, X_test, y_test):
    y_pred = model.predict(X_test)
    return compute_metrics(y_test, y_pred)


def metrics_by_region(model, X_test, y_test, region_labels):
    resultados = {}
    y_pred = model.predict(X_test)
    for region in sorted(region_labels.unique()):
        mask = (region_labels == region).values
        r2, rmse, pearson = compute_metrics(y_test[mask], y_pred[mask])
        resultados[region] = {"r2": r2, "rmse": rmse, "pearson": pearson, "n": int(mask.sum())}
    return resultados


def run_for_target(y_variable, train_val, test_final, fecha_corte):
    X_train, y_train = prepare_features(train_val, y_variable)
    X_test, y_test = prepare_features(test_final, y_variable)
    region_test = test_final["region"]

    resumen = {"y_variable": y_variable}

    # --- Baseline (hiperparámetros por defecto) ---
    baseline = XGBRegressor(random_state=RANDOM_STATE, n_jobs=1)
    baseline.fit(X_train, y_train)
    r2_b, rmse_b, pearson_b = evaluate(baseline, X_test, y_test)

    baseline_params = {k: v for k, v in baseline.get_params().items() if k in GRID_KEYS}
    log_run(
        modelo="xgboost",
        tipo_run="baseline",
        y_variable=y_variable,
        fecha_corte=fecha_corte,
        hiperparametros=baseline_params,
        r2=r2_b,
        rmse=rmse_b,
        pearson=pearson_b,
        notas="XGBRegressor con hiperparámetros por defecto",
    )
    resumen["baseline"] = {"r2": r2_b, "rmse": rmse_b, "pearson": pearson_b}
    print(f"[{y_variable}] baseline  -> R2={r2_b:.4f}  RMSE={rmse_b:.4f}  Pearson={pearson_b:.4f}")

    # --- GridSearchCV (solo sobre train_val, cv temporal) ---
    grid = GridSearchCV(
        estimator=XGBRegressor(random_state=RANDOM_STATE, n_jobs=1),
        param_grid=PARAM_GRID,
        cv=TimeSeriesSplit(n_splits=N_CV_SPLITS),
        scoring="r2",
        n_jobs=-1,
    )
    grid.fit(X_train, y_train)

    GRID_SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    cv_results_path = GRID_SEARCH_DIR / f"xgboost_{y_variable}.csv"
    pd.DataFrame(grid.cv_results_).to_csv(cv_results_path, index=False)

    # --- Tuned: reentrenado con mejores hiperparámetros sobre train_val ---
    tuned = grid.best_estimator_  # GridSearchCV ya lo reentrena sobre todo train_val (refit=True por defecto)
    r2_t, rmse_t, pearson_t = evaluate(tuned, X_test, y_test)  # primer y único toque de test_final para tuning

    log_run(
        modelo="xgboost",
        tipo_run="tuned",
        y_variable=y_variable,
        fecha_corte=fecha_corte,
        hiperparametros=grid.best_params_,
        r2=r2_t,
        rmse=rmse_t,
        pearson=pearson_t,
        notas=f"GridSearchCV, TimeSeriesSplit(n_splits={N_CV_SPLITS}), scoring=r2",
    )
    resumen["tuned"] = {"r2": r2_t, "rmse": rmse_t, "pearson": pearson_t}
    print(f"[{y_variable}] tuned     -> R2={r2_t:.4f}  RMSE={rmse_t:.4f}  Pearson={pearson_t:.4f}  best_params={grid.best_params_}")

    # --- Importancia de features (top 10) ---
    importancias = pd.Series(tuned.feature_importances_, index=X_train.columns).sort_values(ascending=False)
    print(f"[{y_variable}] top 10 features más importantes:")
    for feat, val in importancias.head(10).items():
        print(f"    {feat}: {val:.4f}")
    resumen["top_features"] = importancias.head(10)

    # --- Métricas del modelo tuned por región, dentro de test_final ---
    por_region = metrics_by_region(tuned, X_test, y_test, region_test)
    print(f"[{y_variable}] métricas tuned por región (test_final):")
    for region, m in por_region.items():
        print(f"    {region} (n={m['n']}): R2={m['r2']:.4f}  RMSE={m['rmse']:.4f}  Pearson={m['pearson']:.4f}")
    resumen["por_region"] = por_region

    # --- Comparación de modelos (siempre el resultado tuned) ---
    upsert_model_comparison(modelo="xgboost", y_variable=y_variable, r2=r2_t, rmse=rmse_t, pearson=pearson_t)

    return resumen


def print_side_by_side(resumenes):
    print("\n" + "=" * 60)
    print("Comparación lado a lado: ndvi vs. evi (xgboost)")
    print("=" * 60)
    header = f"{'':10s} {'ndvi':>18s} {'evi':>18s}"
    print(header)
    for tipo_run in ("baseline", "tuned"):
        for metrica in ("r2", "rmse", "pearson"):
            v_ndvi = resumenes["ndvi"][tipo_run][metrica]
            v_evi = resumenes["evi"][tipo_run][metrica]
            etiqueta = f"{tipo_run}_{metrica}"
            print(f"{etiqueta:10s} {v_ndvi:18.4f} {v_evi:18.4f}")


def main():
    df = pd.read_csv(DATASET_PATH, parse_dates=["window_start", "window_end"])

    train_val, test_final = split_train_val_test(df, fecha_col="window_start", frac_test_final=0.15)
    fecha_corte = test_final["window_start"].min()

    resumenes = {}
    for y_variable in Y_VARIABLES:
        resumenes[y_variable] = run_for_target(y_variable, train_val, test_final, fecha_corte)

    print_side_by_side(resumenes)


if __name__ == "__main__":
    main()
