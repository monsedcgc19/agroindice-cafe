"""
03_extract_modis.py — Extracción de NDVI/EVI (~16 días) de MODIS MOD13Q1.061
vía Google Earth Engine, para Cauca y Nariño. Proxy principal de rendimiento.

Input:
  - Colección ee: MODIS/061/MOD13Q1 (bandas NDVI, EVI, SummaryQA)
  - Geometrías de Cauca y Nariño (FAO/GAUL level1), vía _gee_common

Output:
  - data/raw/ndvi_evi/modis_16dias_qa_filtrado.csv

Autenticación: requiere que `ee.Authenticate()` ya se haya corrido
manualmente una vez en esta máquina. Este script solo hace
ee.Initialize() vía _gee_common.

Extracción independiente y a resolución nativa ~16 días: un registro por
región y composite MODIS, sin repetirse/rellenarse a diario (a diferencia del
notebook de anteproyecto, que buscaba el MODIS más cercano ±8 días para cada
día de ERA5 vía add_vi, y ponía NDVI/EVI en 0 cuando no encontraba nada). No
cruza con ERA5 ni FLDAS.

El rango de fechas se toma de la fecha real de la primera imagen disponible
en la colección (~2000). No se rellena ningún valor faltante
con cero: si un composite queda enmascarado (p. ej. por nubes) en una región,
reduceRegion lo deja como nulo.

Filtro de calidad (SummaryQA): se detectó que el promedio anual de NDVI/EVI
sube de forma sostenida a partir de 2023 mientras que las variables
climáticas de ERA5/FLDAS en el mismo período se mantienen estables — ver
notebooks/debug_random_forest.ipynb. Una hipótesis es que la mezcla de
píxeles de baja calidad (nube/nieve) incluidos sin filtrar en el promedio
por región cambió entre años. Para probarla, este script ahora enmascara
cada píxel por la banda `SummaryQA` de MOD13Q1 (0=buena, 1=marginal,
2=nieve/hielo, 3=nublado) y solo promedia píxeles con SummaryQA en {0, 1}
antes de reduceRegion — si todos los píxeles de una región/fecha quedan
enmascarados, esa fila sale nula (no se rellena con cero, igual que antes).

Esta versión filtrada se guarda en un archivo NUEVO
(`modis_16dias_qa_filtrado.csv`), sin sobreescribir ni eliminar
`modis_16dias.csv` (la extracción original sin filtrar), para poder comparar
el antes y el después directamente.
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
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "ndvi_evi"
    / "modis_16dias_qa_filtrado.csv"
)
SCALE = 250  # resolución nativa de MOD13Q1
GOOD_QA_VALUES = (0, 1)  # SummaryQA: 0=buena, 1=marginal -> se mantienen; 2=nieve/hielo, 3=nube -> se descartan


def scale_vi(image):
    """Escala NDVI/EVI por el factor 0.0001 indicado por el producto MODIS, y
    enmascara los píxeles cuyo SummaryQA no esté en GOOD_QA_VALUES (nube o
    nieve/hielo) antes de que reduceRegion los promedie por región."""
    quality_ok = image.select("SummaryQA").gte(min(GOOD_QA_VALUES)).And(
        image.select("SummaryQA").lte(max(GOOD_QA_VALUES))
    )
    ndvi = image.select("NDVI").multiply(0.0001).updateMask(quality_ok).rename("ndvi")
    evi = image.select("EVI").multiply(0.0001).updateMask(quality_ok).rename("evi")
    return ndvi.addBands(evi).copyProperties(image, ["system:time_start"])


def main():
    init_ee()
    geometries = get_region_geometries()

    start_date = get_collection_start_date(MODIS_COLLECTION)
    end_date = today_str()
    end_date_excl = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()

    print(f"Rango de extracción MODIS NDVI/EVI (~16 días, filtrado por SummaryQA en {GOOD_QA_VALUES}): {start_date} -> {end_date}")

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
