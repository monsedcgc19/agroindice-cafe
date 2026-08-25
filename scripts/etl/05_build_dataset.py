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
    dewpoint_c/soil_moist_layer1/lai_high, máximo para tmax_c, mínimo para
    tmin_c.
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
"""

from pathlib import Path

import pandas as pd

CLEAN_DIR = Path(__file__).resolve().parents[2] / "data" / "clean"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

ERA5_PATH = CLEAN_DIR / "clima" / "era5_diario.csv"
FLDAS_PATH = CLEAN_DIR / "clima" / "et_mensual.csv"
MODIS_PATH = CLEAN_DIR / "ndvi_evi" / "modis_16dias.csv"

DATASET_PATH = PROCESSED_DIR / "dataset_modelo.csv"
DICT_PATH = PROCESSED_DIR / "diccionario_datos.md"

SUM_VARS = ["precip_mm", "pet_mm"]
MEAN_VARS = ["tmean_c", "dewpoint_c", "soil_moist_layer1", "lai_high"]
MAX_VARS = ["tmax_c"]
MIN_VARS = ["tmin_c"]
ERA5_VARS = SUM_VARS + MEAN_VARS + MAX_VARS + MIN_VARS
N_LAGS = 3  # lag0, lag1, lag2

LAG_LABELS = {0: "ventana actual", 1: "ventana inmediatamente anterior", 2: "dos ventanas atrás"}

BASE_META = {
    "precip_mm": ("mm, suma de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Precipitación acumulada"),
    "pet_mm": ("mm, suma de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Evapotranspiración potencial acumulada (signo corregido en 04_clean_transform.py respecto al crudo)"),
    "tmean_c": ("°C, promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Temperatura media"),
    "dewpoint_c": ("°C, promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Punto de rocío"),
    "soil_moist_layer1": ("m3/m3 (0-1), promedio de la ventana", "ERA5-Land / ECMWF (vía Google Earth Engine)", "Humedad volumétrica del suelo, capa 1"),
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
