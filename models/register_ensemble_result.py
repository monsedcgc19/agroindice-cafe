"""
register_ensemble_result.py — Persiste en results/model_comparison.csv el
resultado ya evaluado del ensemble Ridge + Gradient Boosting (NDVI), que
hasta ahora solo vivía como celda de salida en
notebooks/calibracion_ensemble_ridge_gradient_boosting_ndvi.ipynb, sección
"14. evaluación definitiva en test_final" (no se guardaba a ningún CSV de
results/, a diferencia de random_forest.py y xgboost_model.py que sí
llaman upsert_model_comparison automáticamente).

No reentrena ni recalcula nada -- los 3 números (r2, rmse, pearson) son los
mismos ya reportados en CONTEXT.md ("## Resultados del modelado", fila
Ridge + Gradient Boosting) y verificados contra la celda de esa notebook.
Se agregan aquí solo para que el dashboard (pantalla de validación
analítica) pueda leer la comparación completa de las 3 familias de modelo
desde results/model_comparison.csv, sin hardcodear estos 3 números en el
código del dashboard.

El ensemble solo se evaluó para NDVI (no para EVI) -- ver CONTEXT.md.
"""

from _experiment_utils import upsert_model_comparison

# Copiados de la celda "14. evaluación definitiva en test_final" del
# notebook de calibración (tabla_test_final), mismo test_final (85/15,
# corte en 2022-08-13) que random_forest.py y xgboost_model.py.
R2 = 0.281763
RMSE = 0.023049
PEARSON = 0.762042


def main():
    upsert_model_comparison(
        modelo="ridge_gradient_boosting",
        y_variable="ndvi",
        r2=R2,
        rmse=RMSE,
        pearson=PEARSON,
    )
    print("Fila 'ridge_gradient_boosting'/'ndvi' agregada/actualizada en results/model_comparison.csv")


if __name__ == "__main__":
    main()
