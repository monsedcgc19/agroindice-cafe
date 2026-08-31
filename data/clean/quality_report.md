# Reporte de calidad — 04_clean_transform.py

Validación de `region` idéntica entre archivos: **True**
Valores de region: ['Cauca', 'Narino']

**Corrección aplicada:** `pet_mm` en `era5_diario` se multiplicó por -1 respecto al crudo de `data/raw/`. ERA5-Land define `potential_evaporation_sum` con convención de flujo descendente-positivo, así que la evapotranspiración (flujo ascendente) sale negativa en el dato crudo. El CSV en `data/raw/` y `01_extract_era5.py` no se modificaron; la corrección vive solo en esta capa de limpieza (`data/clean/`).

## era5_diario

- Archivo crudo: `raw\clima\era5_diario.csv`
- Archivo limpio: `clean\clima\era5_diario.csv`
- Filas: 19368
- Duplicados (date+region), filas marcadas: 0
- Filas con algún valor fuera de rango físico: 0

## et_mensual

- Archivo crudo: `raw\clima\et_mensual.csv`
- Archivo limpio: `clean\clima\et_mensual.csv`
- Filas: 634
- Duplicados (date+region), filas marcadas: 0
- Filas con algún valor fuera de rango físico: 0

## modis_16dias

- Archivo crudo: `raw\ndvi_evi\modis_16dias_qa_filtrado.csv`
- Archivo limpio: `clean\ndvi_evi\modis_16dias.csv`
- Filas: 1218
- Duplicados (date+region), filas marcadas: 0
- Filas con algún valor fuera de rango físico: 0

## Estadísticas descriptivas por variable y archivo

| archivo      | variable          |       min |       max |     media |       std |   n_validos |
|:-------------|:------------------|----------:|----------:|----------:|----------:|------------:|
| era5_diario  | dewpoint_c        | 11.9416   | 19.7043   | 16.7817   | 1.19075   |       19368 |
| era5_diario  | lai_high          |  3.7401   |  4.04902  |  3.90011  | 0.0764622 |       19368 |
| era5_diario  | pet_mm            |  1.21946  | 10.6209   |  5.16014  | 1.22421   |       19368 |
| era5_diario  | precip_mm         |  0.444378 | 95.1988   | 16.3154   | 9.81445   |       19368 |
| era5_diario  | soil_moist_layer1 |  0.345445 |  0.457582 |  0.435715 | 0.0124742 |       19368 |
| era5_diario  | soil_moist_layer2 |  0.352515 |  0.461897 |  0.438266 | 0.0128098 |       19368 |
| era5_diario  | soil_moist_layer3 |  0.366946 |  0.46184  |  0.434781 | 0.0125099 |       19368 |
| era5_diario  | tmax_c            | 17.8354   | 26.1039   | 22.4011   | 1.13419   |       19368 |
| era5_diario  | tmean_c           | 16.4063   | 22.2096   | 19.0329   | 1.02668   |       19368 |
| era5_diario  | tmin_c            | 11.8637   | 20.0517   | 16.742    | 1.27231   |       19368 |
| et_mensual   | et_mm             |  2.86951  |  4.50902  |  3.6799   | 0.292097  |         634 |
| modis_16dias | evi               |  0.347847 |  0.577413 |  0.463174 | 0.0338684 |        1218 |
| modis_16dias | ndvi              |  0.605759 |  0.837154 |  0.757351 | 0.0358558 |        1218 |

## % de nulos reales por variable y archivo

| archivo      | variable          |   n_nulos |   pct_nulos |
|:-------------|:------------------|----------:|------------:|
| era5_diario  | dewpoint_c        |         0 |           0 |
| era5_diario  | lai_high          |         0 |           0 |
| era5_diario  | pet_mm            |         0 |           0 |
| era5_diario  | precip_mm         |         0 |           0 |
| era5_diario  | soil_moist_layer1 |         0 |           0 |
| era5_diario  | soil_moist_layer2 |         0 |           0 |
| era5_diario  | soil_moist_layer3 |         0 |           0 |
| era5_diario  | tmax_c            |         0 |           0 |
| era5_diario  | tmean_c           |         0 |           0 |
| era5_diario  | tmin_c            |         0 |           0 |
| et_mensual   | et_mm             |         0 |           0 |
| modis_16dias | evi               |         0 |           0 |
| modis_16dias | ndvi              |         0 |           0 |

## Rangos físicamente plausibles usados para marcar (no filtrar)

| variable | mínimo | máximo |
|---|---|---|
| tmax_c | 0 | 45 |
| tmin_c | 0 | 45 |
| tmean_c | 0 | 45 |
| dewpoint_c | 0 | 45 |
| precip_mm | 0 | - |
| pet_mm | 0 | - |
| et_mm | 0 | - |
| soil_moist_layer1 | 0 | 1 |
| soil_moist_layer2 | 0 | 1 |
| soil_moist_layer3 | 0 | 1 |
| lai_high | 0 | 10 |
| ndvi | -1 | 1 |
| evi | -1 | 1 |

Nota: estos rangos son deliberadamente amplios y no corresponden a los valores observados en el Anteproyecto (ventana 2023-2025), que no representa toda la variabilidad del rango histórico ampliado (2000-hoy). Ningún valor fue eliminado ni imputado en este paso.