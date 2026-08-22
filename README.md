# AgroÍndice Café

Dashboard analítico para validar un índice climático como base de un seguro agrícola
indexado en café, en los departamentos de Cauca y Nariño. Proyecto del curso
**Proyecto Aplicado de Analítica de Datos — MIAD, Universidad de los Andes**.

El artefacto compara modelos candidatos, valida qué tan bien un índice climático
representa el comportamiento del cultivo, y analiza umbrales de activación.
**No calcula primas, no emite pólizas, no es una plataforma comercial operativa**
(ver alcance del MVP en `docs/Prototipo_Fachada.pdf`).

## Equipo

| Rol | Responsable |
|---|---|
| Project Lead (trazabilidad, planeación, integración, cierre) | Daniel Santana |
| BI Specialist (diseño dashboard) | Martin Cufiño |
| Model Owner (coordinación de modelos y comparación) | José Gabriel Paredes |
| Data Engineer (scripts de ETL, `data/`) | Monserrat Da Costa |

Nota: todos apoyan en la creación y experimentación de modelos.

## Estructura

```
agroindice-cafe/
├── data/
│   ├── raw/                 # descargas originales
│   │   ├── clima/
│   │   ├── ndvi_evi/
│   │   └── rendimiento/
│   └── processed/           # datos procesados
├── scripts/etl/             # 01_extract → 02_extract → 03_clean_transform → 04_build_dataset
├── models/                  # un script por modelo candidato (RF, XGBoost, SVM, NN)
├── dashboard/               # app Streamlit, una página por pantalla del mockup
│   ├── app.py
│   ├── pages/
│   └── utils/
└── docs/                    # PDFs de anteproyecto, prototipo fachada, tabla de requerimientos
```

## Convenciones

- `data/raw/` no se edita a mano. Si se amplía el rango histórico o se cambia una
  fuente, se reemplaza el archivo y se comitea con un mensaje descriptivo — el
  historial de git funciona como versionado del dato crudo (relevante para R10).
- `data/processed/` es la única fuente que leen `models/` y `dashboard/`. Nunca se
  recalculan transformaciones "en vivo" dentro del dashboard.
- Cada script de `scripts/etl/` documenta en su docstring qué recibe, qué produce,
  y si algún paso requiere descarga manual (algunas fuentes no tienen API pública) —
  esto es lo que sustenta R7.
- Sin actualizaciones automáticas programadas por ahora: está fuera del alcance del
  MVP (ver Prototipo Fachada, sección de alcance). Se re-corre el pipeline manualmente
  antes de cada entrega.


## Métricas objetivo (Tabla de Requerimientos)

| Métrica | Meta |
|---|---|
| R² (regresión) | ≥ 0.60 |
| RMSE | ≤ 15% de la media |
| Correlación de Pearson | ≥ 0.65 |
| Riesgo base (1 − r²) | ≤ 50% |
| Calidad de datos | ≥ 90% registros válidos |
