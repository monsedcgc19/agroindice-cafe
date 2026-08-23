"""
03_extract_modis.py — Extracción de NDVI/EVI (~16 días) de MODIS MOD13Q1.061
vía Google Earth Engine, para Cauca y Nariño. Proxy principal de rendimiento.

Input:
  - Colección ee: MODIS/061/MOD13Q1 (bandas NDVI, EVI)
  - Geometrías de Cauca y Nariño (FAO/GAUL level1), vía _gee_common

Output:
  - data/raw/ndvi_evi/modis_16dias.csv

Autenticación: requiere que `ee.Authenticate()` ya se haya corrido
manualmente una vez en esta máquina. Este script solo hace
ee.Initialize() vía _gee_common.

Extracción independiente y a resolución nativa ~16 días: un registro por
región y composite MODIS, sin repetirse/rellenarse a diario (a diferencia del
notebook de anteproyecto, que buscaba el MODIS más cercano ±8 días para cada
día de ERA5 vía add_vi, y ponía NDVI/EVI en 0 cuando no encontraba nada). No
cruza con ERA5 ni FLDAS.

El rango de fechas se toma de la fecha real de la primera imagen disponible
en la colección (no se hardcodea ~2000). No se rellena ningún valor faltante
con cero: si un composite queda enmascarado (p. ej. por nubes) en una región,
reduceRegion lo deja como nulo.
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

MODIS_COLLECTION = "MODIS/061/MOD13Q1"
OUTPUT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "raw" / "ndvi_evi" / "modis_16dias.csv"
)
SCALE = 250  # resolución nativa de MOD13Q1


def scale_vi(image):
    """Escala NDVI/EVI por el factor 0.0001 indicado por el producto MODIS."""
    ndvi = image.select("NDVI").multiply(0.0001).rename("ndvi")
    evi = image.select("EVI").multiply(0.0001).rename("evi")
    return ndvi.addBands(evi).copyProperties(image, ["system:time_start"])


def main():
    init_ee()
    geometries = get_region_geometries()

    start_date = get_collection_start_date(MODIS_COLLECTION)
    end_date = today_str()
    end_date_excl = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()

    print(f"Rango de extracción MODIS NDVI/EVI (~16 días): {start_date} -> {end_date}")

    modis = (
        ee.ImageCollection(MODIS_COLLECTION)
        .filterDate(start_date, end_date_excl)
        .map(scale_vi)
    )

    fc = extract_region_features(modis, geometries, scale=SCALE)
    df = fc_to_dataframe(fc)
    df = df.sort_values(["region", "date"]).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Guardado: {OUTPUT_PATH} ({len(df)} filas)")


if __name__ == "__main__":
    main()
