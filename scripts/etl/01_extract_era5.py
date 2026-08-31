"""
01_extract_era5.py — Extracción diaria de clima (ERA5-Land) vía Google Earth
Engine, para los departamentos de Cauca y Nariño.

Input:
  - Colección ee: ECMWF/ERA5_LAND/DAILY_AGGR
  - Geometrías de Cauca y Nariño (FAO/GAUL level1), vía _gee_common

Output:
  - data/raw/clima/era5_diario.csv

Autenticación: requiere que `ee.Authenticate()` ya se haya corrido
manualmente una vez en esta máquina. Este script solo hace
ee.Initialize() vía _gee_common.

Extracción independiente: no cruza con FLDAS ni MODIS (a diferencia del
notebook de anteproyecto, que hacía un matching día a día vía add_vi/add_et).
Se extrae en bloques anuales por los límites de una sola llamada síncrona a
Earth Engine (~9600 imágenes diarias en total entre 2000 y hoy).

El rango de fechas se acota por la disponibilidad real de MODIS (variable
proxy de rendimiento, la más restrictiva) — no se hardcodea un año de inicio.
No se rellena ningún valor faltante con cero: si un pixel/banda queda
enmascarado en una región, reduceRegion lo deja como nulo.

Capas de suelo más profundas (decisión 2026-08-30): además de
`soil_moist_layer1` (0-7cm, muy superficial, reacciona a cada lluvia
individual y es ruidosa), se agregan `soil_moist_layer2` (7-28cm) y
`soil_moist_layer3` (28-100cm) de ERA5-Land — cubren razonablemente la zona
de raíces de un cafetal adulto e integran humedad sobre un plazo más largo,
con la hipótesis de que correlacionan mejor con el estrés hídrico real de
la planta que la capa 1 sola. No se agrega `layer_4` (100-289cm, más
profunda que la zona de raíces típica) para no sobresaturar el dataset con
una capa de relevancia agronómica dudosa.
"""

from datetime import date, timedelta
from pathlib import Path

import ee
import pandas as pd

from _gee_common import (
    extract_region_features,
    fc_to_dataframe,
    get_collection_start_date,
    get_region_geometries,
    init_ee,
    today_str,
)

ERA5_COLLECTION = "ECMWF/ERA5_LAND/DAILY_AGGR"
MODIS_COLLECTION = "MODIS/061/MOD13Q1"
OUTPUT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "raw" / "clima" / "era5_diario.csv"
)
SCALE = 10000  # ~10 km, resolución nativa de ERA5-Land

BAND_NAMES = [
    "precip_mm",
    "tmax_c",
    "tmin_c",
    "tmean_c",
    "dewpoint_c",
    "pet_mm",
    "soil_moist_layer1",
    "soil_moist_layer2",
    "soil_moist_layer3",
    "lai_high",
]


def prep_bands(image):
    """Deriva las bandas de interés en unidades legibles (°C, mm)."""
    tmax_c = image.select("temperature_2m_max").subtract(273.15).rename("tmax_c")
    tmin_c = image.select("temperature_2m_min").subtract(273.15).rename("tmin_c")
    tmean_c = image.select("temperature_2m").subtract(273.15).rename("tmean_c")
    dew_c = image.select("dewpoint_temperature_2m").subtract(273.15).rename("dewpoint_c")
    precip_mm = image.select("total_precipitation_sum").multiply(1000).rename("precip_mm")
    pet_mm = image.select("potential_evaporation_sum").multiply(1000).rename("pet_mm")
    soil_moist1 = image.select("volumetric_soil_water_layer_1").rename("soil_moist_layer1")
    soil_moist2 = image.select("volumetric_soil_water_layer_2").rename("soil_moist_layer2")
    soil_moist3 = image.select("volumetric_soil_water_layer_3").rename("soil_moist_layer3")
    lai_high = image.select("leaf_area_index_high_vegetation").rename("lai_high")

    return (
        precip_mm.addBands(
            [tmax_c, tmin_c, tmean_c, dew_c, pet_mm, soil_moist1, soil_moist2, soil_moist3, lai_high]
        )
        .copyProperties(image, ["system:time_start"])
    )


def year_blocks(start_date, end_date_excl):
    """Bloques [inicio, fin) por año calendario entre start_date y end_date_excl."""
    start_year = int(start_date[:4])
    end_year = int(end_date_excl[:4])
    blocks = []
    for year in range(start_year, end_year + 1):
        block_start = max(start_date, f"{year}-01-01")
        block_end = min(end_date_excl, f"{year + 1}-01-01")
        if block_start < block_end:
            blocks.append((block_start, block_end))
    return blocks


def main():
    init_ee()
    geometries = get_region_geometries()

    start_date = get_collection_start_date(MODIS_COLLECTION)
    end_date = today_str()
    end_date_excl = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()

    print(f"Rango de extracción ERA5-Land (diario): {start_date} -> {end_date}")

    blocks = year_blocks(start_date, end_date_excl)
    frames = []
    for block_start, block_end in blocks:
        print(f"  bloque {block_start} -> {block_end}")
        era5_block = (
            ee.ImageCollection(ERA5_COLLECTION)
            .filterDate(block_start, block_end)
            .map(prep_bands)
        )
        fc = extract_region_features(era5_block, geometries, scale=SCALE, band_names=BAND_NAMES)
        frames.append(fc_to_dataframe(fc))

    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(["region", "date"]).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Guardado: {OUTPUT_PATH} ({len(df)} filas)")


if __name__ == "__main__":
    main()
