# Diccionario de datos — dataset_modelo.csv

| columna | unidad | fuente | % nulos | descripción |
|---|---|---|---|---|
| region | categórico | FAO/GAUL level1 | 0.00% | Cauca o Narino |
| window_start | fecha (YYYY-MM-DD) | MODIS MOD13Q1.061 | 0.00% | Fecha real del composite MODIS que abre la ventana |
| window_end | fecha (YYYY-MM-DD) | MODIS MOD13Q1.061 | 0.00% | Fecha real del siguiente composite MODIS de la misma región (cierre exclusivo de la ventana) |
| ndvi | índice (-1 a 1) | MODIS MOD13Q1.061 | 0.00% | NDVI de la ventana actual — variable Y |
| evi | índice (-1 a 1) | MODIS MOD13Q1.061 | 0.00% | EVI de la ventana actual — variable Y |
| precip_mm_lag0 | mm, suma de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Precipitación acumulada — ventana actual |
| pet_mm_lag0 | mm, suma de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Evapotranspiración potencial acumulada (signo corregido en 04_clean_transform.py respecto al crudo) — ventana actual |
| tmean_c_lag0 | °C, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura media — ventana actual |
| dewpoint_c_lag0 | °C, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Punto de rocío — ventana actual |
| soil_moist_layer1_lag0 | m3/m3 (0-1), promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Humedad volumétrica del suelo, capa 1 — ventana actual |
| lai_high_lag0 | índice, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Índice de área foliar, vegetación alta — ventana actual |
| tmax_c_lag0 | °C, máximo de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura máxima — ventana actual |
| tmin_c_lag0 | °C, mínimo de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura mínima — ventana actual |
| precip_mm_lag1 | mm, suma de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Precipitación acumulada — ventana inmediatamente anterior |
| pet_mm_lag1 | mm, suma de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Evapotranspiración potencial acumulada (signo corregido en 04_clean_transform.py respecto al crudo) — ventana inmediatamente anterior |
| tmean_c_lag1 | °C, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura media — ventana inmediatamente anterior |
| dewpoint_c_lag1 | °C, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Punto de rocío — ventana inmediatamente anterior |
| soil_moist_layer1_lag1 | m3/m3 (0-1), promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Humedad volumétrica del suelo, capa 1 — ventana inmediatamente anterior |
| lai_high_lag1 | índice, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Índice de área foliar, vegetación alta — ventana inmediatamente anterior |
| tmax_c_lag1 | °C, máximo de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura máxima — ventana inmediatamente anterior |
| tmin_c_lag1 | °C, mínimo de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura mínima — ventana inmediatamente anterior |
| precip_mm_lag2 | mm, suma de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Precipitación acumulada — dos ventanas atrás |
| pet_mm_lag2 | mm, suma de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Evapotranspiración potencial acumulada (signo corregido en 04_clean_transform.py respecto al crudo) — dos ventanas atrás |
| tmean_c_lag2 | °C, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura media — dos ventanas atrás |
| dewpoint_c_lag2 | °C, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Punto de rocío — dos ventanas atrás |
| soil_moist_layer1_lag2 | m3/m3 (0-1), promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Humedad volumétrica del suelo, capa 1 — dos ventanas atrás |
| lai_high_lag2 | índice, promedio de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Índice de área foliar, vegetación alta — dos ventanas atrás |
| tmax_c_lag2 | °C, máximo de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura máxima — dos ventanas atrás |
| tmin_c_lag2 | °C, mínimo de la ventana | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Temperatura mínima — dos ventanas atrás |
| precip_mm_roll32 | mm, suma de ~32 días (lag0+lag1) | ERA5-Land / ECMWF (vía Google Earth Engine) | 0.00% | Precipitación acumulada de las dos ventanas más recientes juntas (no es un lag) |
| et_mm_lag0 | mm/día equivalente, valor mensual | FLDAS / NASA (vía Google Earth Engine) | 0.00% | ET real del mes calendario que contiene el inicio de la ventana actual |
| et_mm_lag1 | mm/día equivalente, valor mensual | FLDAS / NASA (vía Google Earth Engine) | 0.17% | ET real del mes calendario inmediatamente anterior |
| et_resolution | categórico fijo | FLDAS / NASA (vía Google Earth Engine) | 0.00% | Siempre 'monthly' — deja explícito que et_mm es de menor resolución temporal que el resto de variables |
| deficit_hidrico | mm | Derivado (ERA5-Land) | 0.00% | precip_mm_lag0 - pet_mm_lag0 |
| soil_moist_anomaly | m3/m3 | Derivado (ERA5-Land) | 0.00% | soil_moist_layer1_lag0 - promedio histórico de esa variable por región y día del año de inicio de ventana, a través de todos los años disponibles |
| ndvi_lag_1year | índice (-1 a 1) | MODIS MOD13Q1.061 | 3.47% | NDVI de ~1 año atrás (23 ventanas atrás) en la misma región — señal de persistencia/nivel, no de la ventana actual |
| evi_lag_1year | índice (-1 a 1) | MODIS MOD13Q1.061 | 3.47% | EVI de ~1 año atrás (23 ventanas atrás) en la misma región — señal de persistencia/nivel, no de la ventana actual |
| deficit_hidrico_trend2y | mm | Derivado (ERA5-Land) | 3.63% | Promedio móvil retrospectivo de deficit_hidrico (~2 años, mínimo ~1 año de historia), por región — régimen climático de largo plazo |
| ndvi_lag1w | índice (-1 a 1) | MODIS MOD13Q1.061 | 0.00% | NDVI de 1 ventana atrás (~16 días) en la misma región — autocorrelación de corto plazo, la más fuerte medida entre todos los rezagos probados |
| evi_lag1w | índice (-1 a 1) | MODIS MOD13Q1.061 | 0.00% | EVI de 1 ventana atrás (~16 días) en la misma región — autocorrelación de corto plazo |
| doy_sin | adimensional (-1 a 1) | Derivado (fecha) | 0.00% | sin(2*pi*día_del_año/365.25) — codificación cíclica de estacionalidad |
| doy_cos | adimensional (-1 a 1) | Derivado (fecha) | 0.00% | cos(2*pi*día_del_año/365.25) — codificación cíclica de estacionalidad |

Nota: no se calcula ninguna anomalía de NDVI/EVI como variable predictora — NDVI/EVI es la variable Y, así que cualquier anomalía derivada de ella misma sería fuga de información hacia el modelo.

Nota: los % de nulos reportados aquí son los del dataset ya alineado (después de descartar ventanas sin lag2 o sin cierre real) — reflejan huecos reales de cobertura entre fuentes (p. ej. FLDAS no cubre todavía el mes de una ventana muy reciente), no valores imputados: este script no imputa nada.