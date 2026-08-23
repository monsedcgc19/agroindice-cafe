"""
_gee_common.py — Inicialización de Earth Engine y geometrías de Cauca/Nariño
(FAO/GAUL) reutilizadas por los scripts 01/02/03 de scripts/etl/.

No requiere descarga ni autenticación manual por sí mismo: `ee.Authenticate()`
es un paso manual que Monse corre una sola vez en su máquina; este módulo solo 
hace `ee.Initialize()` contra el proyecto de Google Cloud `earthengine-cafe`, 
asumiendo que ya existen credenciales guardadas localmente.
"""

from datetime import date

import ee
import pandas as pd

EE_PROJECT = "earthengine-cafe"

# Nombre del departamento tal como aparece en ADM1_NAME dentro de FAO/GAUL/2015/level1
_GAUL_ADM1_NAMES = {
    "Cauca": "Cauca",
    "Narino": "Narino",
}


def init_ee():
    """Inicializa la sesión de Earth Engine contra el proyecto del curso."""
    ee.Initialize(project=EE_PROJECT)


def get_region_geometries():
    """Geometrías (ee.Geometry) de Cauca y Nariño vía FAO/GAUL level1.

    Devuelve un dict {"Cauca": geom, "Narino": geom} con el polígono
    departamental completo (no puntos aproximados).
    """
    gaul = ee.FeatureCollection("FAO/GAUL/2015/level1")
    geometries = {}
    for region_name, adm1_name in _GAUL_ADM1_NAMES.items():
        geometries[region_name] = (
            gaul.filter(
                ee.Filter.And(
                    ee.Filter.eq("ADM0_NAME", "Colombia"),
                    ee.Filter.eq("ADM1_NAME", adm1_name),
                )
            ).geometry()
        )
    return geometries


def get_collection_start_date(collection_id, band=None):
    """Fecha (YYYY-MM-DD) de la primera imagen realmente disponible en una
    colección de Earth Engine, sin hardcodear rangos."""
    coll = ee.ImageCollection(collection_id)
    if band:
        coll = coll.select(band)
    first = coll.sort("system:time_start").first()
    return ee.Date(first.get("system:time_start")).format("YYYY-MM-dd").getInfo()


def today_str():
    """Fecha de hoy en formato YYYY-MM-DD (según reloj de esta máquina)."""
    return date.today().isoformat()


def extract_region_features(collection, geometries, scale, band_names=None):
    """Reduce cada imagen de `collection` a la media por región (una fila por
    imagen x región), sin cruzar con ninguna otra colección.

    Devuelve un ee.FeatureCollection con las bandas seleccionadas más las
    propiedades `date` y `region`. Si un pixel/región queda enmascarado para
    una banda, reduceRegion deja esa propiedad como null (no se rellena con
    cero en ningún punto de la extracción).
    """
    region_fcs = []
    for region_name, geom in geometries.items():

        def per_image(image, geom=geom, region_name=region_name):
            img = image.select(band_names) if band_names else image
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=scale,
                maxPixels=1e13,
            )
            return (
                ee.Feature(None, stats)
                .set("date", image.date().format("YYYY-MM-dd"))
                .set("region", region_name)
            )

        region_fcs.append(collection.map(per_image))

    merged = region_fcs[0]
    for fc in region_fcs[1:]:
        merged = merged.merge(fc)
    return merged


def fc_to_dataframe(fc):
    """Convierte un ee.FeatureCollection ya reducido (getInfo) en un
    pandas.DataFrame, preservando valores nulos tal como vienen de GEE."""
    features = fc.getInfo()["features"]
    return pd.DataFrame([f["properties"] for f in features])
