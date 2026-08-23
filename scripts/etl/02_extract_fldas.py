"""
02_extract_fldas.py — Extracción mensual de evapotranspiración (FLDAS) vía
Google Earth Engine, para Cauca y Nariño.

Input:
  - Colección ee: NASA/FLDAS/NOAH01/C/GL/M/V001 (banda Evap_tavg, kg/m2/s)
  - Geometrías de Cauca y Nariño (FAO/GAUL level1), vía _gee_common

Output:
  - data/raw/clima/et_mensual.csv

Autenticación: requiere que `ee.Authenticate()` ya se haya corrido
manualmente una vez en esta máquina. Este script solo hace
ee.Initialize() vía _gee_common.

Extracción independiente y a resolución nativa mensual: un registro por
región y mes, sin repetirse/rellenarse a diario (a diferencia del notebook de
anteproyecto, que repetía el mismo ET a lo largo de todos los días del mes vía
add_et). No cruza con ERA5 ni MODIS.

El rango de fechas se acota por la disponibilidad real de MODIS (variable
proxy de rendimiento, la más restrictiva) — no se hardcodea un año de inicio.
No se rellena ningún valor faltante con cero: si un mes queda enmascarado en
una región, reduceRegion lo deja como nulo.
"""

from datetime import date, timedelta
from pathlib import Path

import ee

from _gee_common import (
    extract_region_features,
    fc_to_dataframe,
    get_collection_start_date,
    get_region_geometries,
    init_ee,
    today_str,
)

FLDAS_COLLECTION = "NASA/FLDAS/NOAH01/C/GL/M/V001"
MODIS_COLLECTION = "MODIS/061/MOD13Q1"
OUTPUT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "raw" / "clima" / "et_mensual.csv"
)
SCALE = 10000  # ~10 km, resolución nativa de FLDAS (0.1°)


def add_et_mm(image):
    """Evap_tavg (kg/m2/s) -> et_mm (mm/día equivalente), sin rellenar nulos."""
    et_mm = image.select("Evap_tavg").multiply(86400).rename("et_mm")
    return et_mm.copyProperties(image, ["system:time_start"])


def main():
    init_ee()
    geometries = get_region_geometries()

    start_date = get_collection_start_date(MODIS_COLLECTION)
    end_date = today_str()
    end_date_excl = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()

    print(f"Rango de extracción FLDAS (ET mensual): {start_date} -> {end_date}")

    fldas = (
        ee.ImageCollection(FLDAS_COLLECTION)
        .filterDate(start_date, end_date_excl)
        .map(add_et_mm)
    )

    fc = extract_region_features(fldas, geometries, scale=SCALE)
    df = fc_to_dataframe(fc)
    df = df.sort_values(["region", "date"]).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Guardado: {OUTPUT_PATH} ({len(df)} filas)")


if __name__ == "__main__":
    main()
