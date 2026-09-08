"""
serialize_winner.py — Serializa el modelo ganador (Random Forest + NDVI) para
que el dashboard lo cargue directamente, sin reentrenar.

Reentrena exactamente el mismo modelo que generó la fila ganadora de
results/model_comparison.csv (etiquetada allí como `random_forest_v4_features`
+ `ndvi`, R²=0.329, RMSE=2.87% de la media, Pearson=0.768 — ver
`## Resultados del modelado` en CONTEXT.md; internamente sigue siendo un
RandomForestRegressor, "v4_features" es solo la etiqueta de esa corrida de
experimento en results/, no un modelo distinto): mismo split cronológico
train_val/test_final (85/15, vía `split_train_val_test`), misma
`prepare_features`, y los hiperparámetros ganadores de esa fila de
experiment_log.csv (random_forest_v4_features, tuned, ndvi,
2026-08-30T18:43:46): max_depth=None, min_samples_leaf=10, n_estimators=400.

No reentrena sobre 100% de los datos -- usa exactamente `train_val`, igual que
la corrida original, para que las predicciones del dashboard coincidan con
las métricas ya reportadas.

Input:
  - data/processed/dataset_modelo.csv

Output:
  - models/artifacts/random_forest_ndvi.joblib

No requiere autenticación ni conexión externa.
"""

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from _experiment_utils import compute_metrics, prepare_features, split_train_val_test
from pathlib import Path

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "dataset_modelo.csv"
ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "random_forest_ndvi.joblib"

# Hiperparámetros ganadores -- copiados de la fila
# random_forest_v4_features/tuned/ndvi en results/experiment_log.csv
# (timestamp 2026-08-30T18:43:46), la misma que generó la fila ganadora
# vigente en results/model_comparison.csv.
WINNING_PARAMS = {"max_depth": None, "min_samples_leaf": 10, "n_estimators": 400}
RANDOM_STATE = 42
Y_VARIABLE = "ndvi"

# Métricas ya reportadas para esta corrida (results/model_comparison.csv,
# fila random_forest_v4_features/ndvi) -- se usan solo para verificar que el
# modelo serializado reproduce el resultado, no se recalculan como "nuevas".
EXPECTED_R2 = 0.32874222679516407
EXPECTED_RMSE = 0.02228218789602101
EXPECTED_PEARSON = 0.7675284519492803


def main():
    df = pd.read_csv(DATASET_PATH, parse_dates=["window_start", "window_end"])
    train_val, test_final = split_train_val_test(df, fecha_col="window_start", frac_test_final=0.15)

    X_train, y_train = prepare_features(train_val, Y_VARIABLE)
    X_test, y_test = prepare_features(test_final, Y_VARIABLE)

    model = RandomForestRegressor(random_state=RANDOM_STATE, **WINNING_PARAMS)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2, rmse, pearson = compute_metrics(y_test, y_pred)
    print(f"Verificación sobre test_final completo: R2={r2:.6f}  RMSE={rmse:.6f}  Pearson={pearson:.6f}")
    print(f"Esperado (model_comparison.csv):        R2={EXPECTED_R2:.6f}  RMSE={EXPECTED_RMSE:.6f}  Pearson={EXPECTED_PEARSON:.6f}")
    assert abs(r2 - EXPECTED_R2) < 1e-9, "R2 no coincide con el resultado ya reportado"
    assert abs(rmse - EXPECTED_RMSE) < 1e-9, "RMSE no coincide con el resultado ya reportado"
    assert abs(pearson - EXPECTED_PEARSON) < 1e-9, "Pearson no coincide con el resultado ya reportado"

    print("\nVerificación sobre 5 filas al azar de test_final:")
    muestra = X_test.sample(5, random_state=7)
    idx = muestra.index
    pred_muestra = model.predict(muestra)
    for i, pred in zip(idx, pred_muestra):
        print(f"  fila {i}: y_real={y_test.loc[i]:.6f}  y_pred={pred:.6f}")

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACT_PATH)
    print(f"\nModelo serializado en {ARTIFACT_PATH}")


if __name__ == "__main__":
    main()
