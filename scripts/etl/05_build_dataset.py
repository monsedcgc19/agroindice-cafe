"""
05_build_dataset.py — Alineación temporal final: una fila por región x
ventana de MODIS (~16 días), con features de rezago de ERA5/FLDAS y
variables derivadas. Salida = única fuente que deben leer models/ y
dashboard/.

Input:
  - data/clean/clima/era5_diario.csv
  - data/clean/clima/et_mensual.csv
  - data/clean/ndvi_evi/modis_16dias.csv

Output:
  - data/processed/dataset_modelo.csv
  - data/processed/diccionario_datos.md

No requiere autenticación ni conexión a Earth Engine.

Reglas de alineación:
  - Granularidad: una fila por región x ventana MODIS, usando las fechas
    reales de adquisición de cada composite (no un calendario de 16 días
    asumido) — el cierre de cada ventana es la fecha real del siguiente
    composite MODIS de esa misma región.
  - Y: `ndvi`, `evi` de la ventana actual (MODIS).
  - ERA5 en 3 versiones no traslapadas por ventana: lag0 (actual), lag1
    (ventana inmediatamente anterior), lag2 (dos ventanas atrás).
    Agregación: suma para precip_mm/pet_mm, promedio para tmean_c/
    dewpoint_c/soil_moist_layer1/soil_moist_layer2/soil_moist_layer3/
    lai_high, máximo para tmax_c, mínimo para tmin_c.
  - precip_mm_roll32 = precip_mm_lag0 + precip_mm_lag1 (no es un lag: junta
    las dos ventanas más recientes en un solo número, ~32 días).
  - FLDAS et_mm_lag0/et_mm_lag1: valor del mes calendario que contiene el
    inicio de la ventana actual / del mes calendario inmediatamente
    anterior. Columna `et_resolution="monthly"` fija, para dejar explícita
    la menor resolución de esta fuente frente al resto.
  - deficit_hidrico = precip_mm_lag0 - pet_mm_lag0.
  - soil_moist_anomaly = soil_moist_layer1_lag0 - promedio histórico de esa
    misma variable, agrupando por región y día del año de inicio de
    ventana, a través de todos los años disponibles (no el promedio
    general de toda la serie) — respeta estacionalidad.
  - NO se calcula ninguna anomalía de NDVI/EVI como predictor: NDVI/EVI es
    la variable Y, así que cualquier anomalía derivada de ella misma sería
    fuga de información hacia el modelo.
  - Se descartan (y se reportan por separado):
      (a) la última ventana MODIS de cada región, porque no tiene un
          siguiente composite real que la cierre (no se asume una
          duración de 16 días de calendario);
      (b) las primeras ventanas de cada región que no alcanzan a tener
          lag2 (necesitan 2 ventanas previas reales en esa región).

Fuente de NDVI/EVI (decisión 2026-08-29): `data/clean/ndvi_evi/modis_16dias.csv`
ahora proviene de la extracción filtrada por `SummaryQA` (ver
03_extract_modis.py y 04_clean_transform.py) en vez de la extracción
original sin filtrar — se detectó que el promedio anual de NDVI/EVI sin
filtrar subía de forma sostenida a partir de 2023 mientras el clima se
mantenía estable en el mismo período (artefacto de píxeles de nube/nieve),
ver notebooks/debug_random_forest.ipynb. No cambia ninguna regla de
alineación de este script, solo el contenido de NDVI/EVI que entra por
data/clean/.

Features nuevas (decisión 2026-08-30) — experimento para atacar el problema
de calibración de nivel detectado en el modelado (Random Forest/XGBoost
capturan bien la forma de NDVI, Pearson alto, pero el nivel de test_final
queda ligeramente por encima del histórico de train_val, lo que hunde el
R²; ver notebooks/debug_random_forest.ipynb y results/experiment_log.csv):
  - `ndvi_lag_1year` / `evi_lag_1year`: valor de NDVI/EVI de ~1 año atrás
    (23 ventanas atrás — con la duración promedio real de ventana de este
    dataset, ~15.9 días, 23 ventanas ≈ 365 días), por región. Le da al
    modelo una señal directa de en qué "nivel" está la vegetación
    actualmente (persistencia estacional), sin ser una anomalía calculada
    sobre toda la serie. Se usa un rezago de ~1 año (no de 1-2 ventanas)
    a propósito: un rezago de NDVI/EVI muy reciente dependería de que el
    último composite MODIS ya esté publicado al momento de predecir, y
    MODIS tiene su propio rezago de disponibilidad real (ver
    01/02/03_extract_*.py) — con 1 año de rezago esa disponibilidad nunca
    es un problema en una implementación real. No es fuga de información:
    es el valor real medido en una ventana muy anterior, no del futuro.
  - `deficit_hidrico_trend2y`: promedio móvil retrospectivo (ventana de 46
    ventanas ≈ 2 años, mínimo 23 ventanas ≈ 1 año de historia para
    calcularlo) de `deficit_hidrico`, por región. Da una señal de régimen
    climático de más largo plazo (más allá de los lags cortos de 0-2
    ventanas), construida solo con ERA5-Land (sin el problema de
    disponibilidad de MODIS).
  - Ninguna de las dos requiere imputación: quedan como NaN real en las
    primeras ventanas de cada región donde no hay suficiente historia
    (23 o 46 ventanas atrás según el caso) — mismo criterio de "no imputar"
    del resto del script.

Segunda iteración de features (decisión 2026-08-30, misma tanda): el
resultado con ndvi_lag_1year/evi_lag_1year mejoró pero siguió lejos de la
meta, así que se probó qué tan autocorrelacionado está NDVI/EVI a rezagos
más cortos (ver notebooks/ o el chequeo hecho aparte): la correlación a 1
ventana atrás (~16 días) resultó ser la MÁS fuerte de todas (0.69-0.70 en
NDVI, más que el rezago de 1 año) — decisión del equipo: sí vale la pena
acercar el rezago, la disponibilidad operativa de MODIS para un rezago de
~16 días es asumible.
  - `ndvi_lag1w` / `evi_lag1w`: valor de NDVI/EVI de 1 ventana atrás
    (~16 días), por región. Como ya se exige k>=2 para el lag2 climático,
    este rezago corto NUNCA queda nulo en las filas que sobreviven — no
    agrega NaN nuevos.
  - `doy_sin` / `doy_cos`: codificación cíclica (seno/coseno) del día del
    año de `window_start`, para que el modelo tenga una señal directa y
    continua de estacionalidad (la autocorrelación de NDVI se vuelve
    negativa a mitad de año y vuelve a subir cerca del año completo — un
    patrón estacional clásico que esta codificación deja explícito, en vez
    de que el modelo tenga que inferirlo indirectamente de otras
    variables). No depende de ninguna fuente externa, se deriva de la
    fecha — sin nulos.
"""

from pathlib import Path

import numpy as np
import pandas as pd

CLEAN_DIR = Path(__file__).resolve().parents[2] / "data" / "clean"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

ERA5_PATH = CLEAN_DIR / "clima" / "era5_diario.csv"
FLDAS_PATH = CLEAN_DIR / "clima" / "et_mensual.csv"
MODIS_PATH = CLEAN_DIR / "ndvi_evi" / "modis_16dias.csv"

DATASET_PATH = PROCESSED_DIR / "dataset_modelo.csv"
DICT_PATH = PROCESSED_DIR / "diccionario_datos.md"

SUM_VARS = ["precip_mm", "pet_mm"]
MEAN_VARS = ["tmean_c", "dewpoint_c", "soil_moist_layer1", "soil_moist_layer2", "soil_moist_layer3", "lai_high"]
MAX_VARS = ["tmax_c"]
MIN_VARS = ["tmin_c"]
ERA5_VARS = SUM_VARS + MEAN_VARS + MAX_VARS + MIN_VARS
N_LAGS = 3  # lag0, lag1, lag2

# ~1 año, en unidades de "ventanas MODIS": duración promedio real de ventana
# en este dataset ≈ 15.9 días -> 365 / 15.9 ≈ 23 ventanas.
LAG_1YEAR_WINDOWS = 23
TREND_WINDOW_2Y = 2 * LAG_1YEAR_WINDOWS  # ~2 años
TREND_MIN_PERIODS = LAG_1YEAR_WINDOWS  # exige al menos ~1 año de historia real

# Rezago corto (~16 días, "un par de semanas") de la propia variable Y — la
# autocorrelación real medida es la más fuerte de todas las que se probaron
# (ver docstring del módulo). Con k>=2 ya exigido para el lag2 climático,
# k - LAG_CLOSE_WINDOWS >= 1 siempre, así que esta feature nunca sale nula.
LAG_CLOSE_WINDOWS = 1

LAG_LABELS = {0: "ventana actual", 1: "ventana inmediatamente anterior", 2: "dos ventanas atrás"}

BASE_META = {
    "precip_mm": ("mm, suma de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Precipitación acumulada"),
    "pet_mm": ("mm, suma de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Evapotranspiración potencial acumulada (signo corregido en 04_clean_transform.py respecto al crudo)"),
    "tmean_c": ("°C, promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Temperatura media"),
    "dewpoint_c": ("°C, promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Punto de rocío"),
    "soil_moist_layer1": ("m3/m3 (0-1), promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Humedad volumétrica del suelo, capa 1 (0-7cm)"),
    "soil_moist_layer2": ("m3/m3 (0-1), promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Humedad volumétrica del suelo, capa 2 (7-28cm)"),
    "soil_moist_layer3": ("m3/m3 (0-1), promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Humedad volumétrica del suelo, capa 3 (28-100cm)"),
    "lai_high": ("índice, promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Índice de área foliar, vegetación alta"),
    "tmax_c": ("°C, máximo de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Temperatura máxima"),
    "tmin_c": ("°C, mínimo de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Temperatura mínima"),
}


def load_clean():
    era5 = pd.read_csv(ERA5_PATH, parse_dates=["date"])
    fldas = pd.read_csv(FLDAS_PATH, parse_dates=["date"])
    modis = pd.read_csv(MODIS_PATH, parse_dates=["date"])
    # Solo columnas de valor: se descartan los flags de QA de 04_clean_transform.py
    era5 = era5[["date", "region"] + ERA5_VARS]
    fldas = fldas[["date", "region", "et_mm"]]
    modis = modis[["date", "region", "ndvi", "evi"]]
    return era5, fldas, modis


def aggregate_era5_window(era5_region, start, end):
    """Agrega ERA5 diario dentro de [start, end) para una región."""
    window = era5_region[(era5_region["date"] >= start) & (era5_region["date"] < end)]
    agg = {}
    for var in SUM_VARS:
        agg[var] = window[var].sum(min_count=1)
    for var in MEAN_VARS:
        agg[var] = window[var].mean()
    for var in MAX_VARS:
        agg[var] = window[var].max()
    for var in MIN_VARS:
        agg[var] = window[var].min()
    return agg


def lookup_et(fldas_region, month_start):
    row = fldas_region[fldas_region["date"] == month_start]
    if row.empty:
        return None
    return row["et_mm"].iloc[0]


def build_region_dataset(region, era5, fldas, modis):
    era5_region = era5[era5["region"] == region].sort_values("date")
    fldas_region = fldas[fldas["region"] == region].sort_values("date")
    modis_region = modis[modis["region"] == region].sort_values("date").reset_index(drop=True)

    dates = modis_region["date"].tolist()
    n_dates = len(dates)

    # Ventanas con cierre real: [dates[j], dates[j+1]) para j = 0..n_dates-2.
    # La última fecha de la región nunca cierra una ventana (no hay composite
    # siguiente real todavía) -> se descarta, no se asume duración de 16 días.
    n_windows_with_close = max(n_dates - 1, 0)
    n_dropped_no_close = 1 if n_dates >= 1 else 0

    records = []
    n_dropped_lag2 = 0

    for k in range(n_windows_with_close):
        if k < 2:
            n_dropped_lag2 += 1
            continue

        start0, end0 = dates[k], dates[k + 1]
        start1, end1 = dates[k - 1], dates[k]
        start2, end2 = dates[k - 2], dates[k - 1]

        agg0 = aggregate_era5_window(era5_region, start0, end0)
        agg1 = aggregate_era5_window(era5_region, start1, end1)
        agg2 = aggregate_era5_window(era5_region, start2, end2)

        month_start0 = start0.replace(day=1)
        month_start_prev = month_start0 - pd.DateOffset(months=1)
        et_lag0 = lookup_et(fldas_region, month_start0)
        et_lag1 = lookup_et(fldas_region, month_start_prev)

        row = {
            "region": region,
            "window_start": start0,
            "window_end": end0,
            "ndvi": modis_region.iloc[k]["ndvi"],
            "evi": modis_region.iloc[k]["evi"],
        }
        for var, value in agg0.items():
            row[f"{var}_lag0"] = value
        for var, value in agg1.items():
            row[f"{var}_lag1"] = value
        for var, value in agg2.items():
            row[f"{var}_lag2"] = value

        row["precip_mm_roll32"] = row["precip_mm_lag0"] + row["precip_mm_lag1"]
        row["et_mm_lag0"] = et_lag0
        row["et_mm_lag1"] = et_lag1
        row["et_resolution"] = "monthly"
        row["deficit_hidrico"] = row["precip_mm_lag0"] - row["pet_mm_lag0"]

        idx_1year = k - LAG_1YEAR_WINDOWS
        if idx_1year >= 0:
            row["ndvi_lag_1year"] = modis_region.iloc[idx_1year]["ndvi"]
            row["evi_lag_1year"] = modis_region.iloc[idx_1year]["evi"]
        else:
            row["ndvi_lag_1year"] = None
            row["evi_lag_1year"] = None

        idx_close = k - LAG_CLOSE_WINDOWS
        if idx_close >= 0:
            row["ndvi_lag1w"] = modis_region.iloc[idx_close]["ndvi"]
            row["evi_lag1w"] = modis_region.iloc[idx_close]["evi"]
        else:
            row["ndvi_lag1w"] = None
            row["evi_lag1w"] = None

        records.append(row)

    return pd.DataFrame(records), n_dropped_lag2, n_dropped_no_close


def add_soil_moist_anomaly(df):
    """soil_moist_anomaly = valor de la ventana - promedio histórico de esa
    misma variable, agrupando por región y día del año de inicio de ventana,
    a través de todos los años disponibles (respeta estacionalidad)."""
    df = df.copy()
    doy = df["window_start"].dt.dayofyear
    climatology = df.groupby([df["region"], doy])["soil_moist_layer1_lag0"].transform("mean")
    df["soil_moist_anomaly"] = df["soil_moist_layer1_lag0"] - climatology
    return df


def add_deficit_hidrico_trend(df):
    """deficit_hidrico_trend2y = promedio móvil retrospectivo de
    deficit_hidrico por región (ventana de TREND_WINDOW_2Y ~2 años, mínimo
    TREND_MIN_PERIODS ~1 año de historia real). Retrospectivo puro (rolling
    de pandas es right-aligned): solo usa ventanas anteriores o la actual,
    nunca futuras. Requiere que df ya esté ordenado por región y fecha."""
    df = df.sort_values(["region", "window_start"]).copy()
    df["deficit_hidrico_trend2y"] = df.groupby("region")["deficit_hidrico"].transform(
        lambda s: s.rolling(window=TREND_WINDOW_2Y, min_periods=TREND_MIN_PERIODS).mean()
    )
    return df


def add_seasonal_cyclical(df):
    """doy_sin / doy_cos = codificación cíclica del día del año de
    window_start. Se deriva solo de la fecha, no de ninguna fuente externa
    -- sin nulos, sin riesgo de fuga."""
    df = df.copy()
    doy = df["window_start"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    return df


def write_data_dictionary(dataset):
    null_pct = (dataset.isna().mean() * 100).round(2)
    rows = []

    def add_row(col, unit, source, desc):
        pct = null_pct.get(col, float("nan"))
        pct_str = f"{pct:.2f}%" if pd.notna(pct) else "-"
        rows.append((col, unit, source, pct_str, desc))

    add_row("region", "categórico", "FAO/GAUL level1", "Cauca o Narino")
    add_row("window_start", "fecha (YYYY-MM-DD)", "MODIS MOD13Q1.061", "Fecha real del composite MODIS que abre la ventana")
    add_row("window_end", "fecha (YYYY-MM-DD)", "MODIS MOD13Q1.061", "Fecha real del siguiente composite MODIS de la misma región (cierre exclusivo de la ventana)")
    add_row("ndvi", "índice (-1 a 1)", "MODIS MOD13Q1.061", "NDVI de la ventana actual — variable Y")
    add_row("evi", "índice (-1 a 1)", "MODIS MOD13Q1.061", "EVI de la ventana actual — variable Y")

    for lag, label in LAG_LABELS.items():
        for var, (unit, source, desc) in BASE_META.items():
            add_row(f"{var}_lag{lag}", unit, source, f"{desc} — {label}")

    add_row("precip_mm_roll32", "mm, suma de ~32 días (lag0+lag1)", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Precipitación acumulada de las dos ventanas más recientes juntas (no es un lag)")
    add_row("et_mm_lag0", "mm/día equivalente, valor mensual", "FLDAS / NASA (vía Google Earth Engine)", "ET real del mes calendario que contiene el inicio de la ventana actual")
    add_row("et_mm_lag1", "mm/día equivalente, valor mensual", "FLDAS / NASA (vía Google Earth Engine)", "ET real del mes calendario inmediatamente anterior")
    add_row("et_resolution", "categórico fijo", "FLDAS / NASA (vía Google Earth Engine)", "Siempre 'monthly' — deja explícito que et_mm es de menor resolución temporal que el resto de variables")
    add_row("deficit_hidrico", "mm", "Derivado (ERA5-Land)", "precip_mm_lag0 - pet_mm_lag0")
    add_row("soil_moist_anomaly", "m3/m3", "Derivado (ERA5-Land)", "soil_moist_layer1_lag0 - promedio histórico de esa variable por región y día del año de inicio de ventana, a través de todos los años disponibles")
    add_row("ndvi_lag_1year", "índice (-1 a 1)", "MODIS MOD13Q1.061", "NDVI de ~1 año atrás (23 ventanas atrás) en la misma región — señal de persistencia/nivel, no de la ventana actual")
    add_row("evi_lag_1year", "índice (-1 a 1)", "MODIS MOD13Q1.061", "EVI de ~1 año atrás (23 ventanas atrás) en la misma región — señal de persistencia/nivel, no de la ventana actual")
    add_row("deficit_hidrico_trend2y", "mm", "Derivado (ERA5-Land)", "Promedio móvil retrospectivo de deficit_hidrico (~2 años, mínimo ~1 año de historia), por región — régimen climático de largo plazo")
    add_row("ndvi_lag1w", "índice (-1 a 1)", "MODIS MOD13Q1.061", "NDVI de 1 ventana atrás (~16 días) en la misma región — autocorrelación de corto plazo, la más fuerte medida entre todos los rezagos probados")
    add_row("evi_lag1w", "índice (-1 a 1)", "MODIS MOD13Q1.061", "EVI de 1 ventana atrás (~16 días) en la misma región — autocorrelación de corto plazo")
    add_row("doy_sin", "adimensional (-1 a 1)", "Derivado (fecha)", "sin(2*pi*día_del_año/365.25) — codificación cíclica de estacionalidad")
    add_row("doy_cos", "adimensional (-1 a 1)", "Derivado (fecha)", "cos(2*pi*día_del_año/365.25) — codificación cíclica de estacionalidad")

    lines = ["# Diccionario de datos — dataset_modelo.csv", ""]
    lines.append("| columna | unidad | fuente | % nulos | descripción |")
    lines.append("|---|---|---|---|---|")
    for col, unit, source, pct, desc in rows:
        lines.append(f"| {col} | {unit} | {source} | {pct} | {desc} |")
    lines.append("")
    lines.append(
        "Nota: no se calcula ninguna anomalía de NDVI/EVI como variable "
        "predictora — NDVI/EVI es la variable Y, así que cualquier anomalía "
        "derivada de ella misma sería fuga de información hacia el modelo."
    )
    lines.append("")
    lines.append(
        "Nota: los % de nulos reportados aquí son los del dataset ya "
        "alineado (después de descartar ventanas sin lag2 o sin cierre "
        "real) — reflejan huecos reales de cobertura entre fuentes (p. ej. "
        "FLDAS no cubre todavía el mes de una ventana muy reciente), no "
        "valores imputados: este script no imputa nada."
    )

    DICT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    era5, fldas, modis = load_clean()
    regions = sorted(modis["region"].unique())

    frames = []
    total_dropped_lag2 = 0
    total_dropped_no_close = 0
    per_region_summary = []

    for region in regions:
        df_region, dropped_lag2, dropped_no_close = build_region_dataset(region, era5, fldas, modis)
        frames.append(df_region)
        total_dropped_lag2 += dropped_lag2
        total_dropped_no_close += dropped_no_close
        per_region_summary.append((region, len(df_region), dropped_lag2, dropped_no_close))

    dataset = pd.concat(frames, ignore_index=True)
    dataset = add_soil_moist_anomaly(dataset)
    dataset = add_deficit_hidrico_trend(dataset)
    dataset = add_seasonal_cyclical(dataset)
    dataset = dataset.sort_values(["region", "window_start"]).reset_index(drop=True)

    ordered_cols = ["region", "window_start", "window_end", "ndvi", "evi"]
    for lag in range(N_LAGS):
        ordered_cols += [f"{v}_lag{lag}" for v in ERA5_VARS]
    ordered_cols += [
        "precip_mm_roll32",
        "et_mm_lag0",
        "et_mm_lag1",
        "et_resolution",
        "deficit_hidrico",
        "soil_moist_anomaly",
        "ndvi_lag_1year",
        "evi_lag_1year",
        "deficit_hidrico_trend2y",
        "ndvi_lag1w",
        "evi_lag1w",
        "doy_sin",
        "doy_cos",
    ]
    dataset = dataset[ordered_cols]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(DATASET_PATH, index=False)
    write_data_dictionary(dataset)

    print("Resumen por región:")
    for region, kept, dropped_lag2, dropped_no_close in per_region_summary:
        print(
            f"  {region}: {kept} filas finales, {dropped_lag2} descartadas por "
            f"lag2 insuficiente, {dropped_no_close} descartada por ventana sin cierre real"
        )

    print(f"\nTotal filas finales: {len(dataset)}")
    print(
        "Rango de fechas (window_start): "
        f"{dataset['window_start'].min().date()} -> {dataset['window_start'].max().date()}"
    )
    print(f"Total descartadas por lag2 insuficiente: {total_dropped_lag2}")
    print(f"Total descartadas por ventana sin cierre real (última de cada región): {total_dropped_no_close}")
    print(f"Guardado: {DATASET_PATH}")
    print(f"Diccionario de datos: {DICT_PATH}")


if __name__ == "__main__":
    main()
