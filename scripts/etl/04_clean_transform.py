"""
04_clean_transform.py — Limpieza y QA por fuente, sin fusionar entre sí.

Input:
  - data/raw/clima/era5_diario.csv
  - data/raw/clima/et_mensual.csv
  - data/raw/ndvi_evi/modis_16dias.csv

Output:
  - data/clean/clima/era5_diario.csv
  - data/clean/clima/et_mensual.csv
  - data/clean/ndvi_evi/modis_16dias.csv
  - data/clean/quality_report.md

No requiere autenticación ni conexión a Earth Engine.

Qué hace este script (y qué no hace):
  - Valida que la columna `region` tenga exactamente los mismos valores en
    los tres archivos.
  - Calcula estadísticas descriptivas (mínimo, máximo, media, desviación
    estándar) por variable y por archivo.
  - MARCA (no elimina) valores fuera de rangos físicamente plausibles y
    deliberadamente amplios — no se usan los rangos observados en el
    Anteproyecto (ventana corta 2023-2025) como umbral, porque no representan
    toda la variabilidad del rango histórico ampliado (2000-hoy).
  - Detecta y reporta duplicados (misma fecha + región dentro de un mismo
    archivo) — se marcan, no se eliminan.
  - Reporta el % de nulos reales por variable y archivo.
  - Corrige el signo de `pet_mm` (ver `correct_era5_pet_sign` más abajo) antes
    de calcular estadísticas y evaluar rangos plausibles — es la única
    transformación de valores que hace este script; todo lo demás es
    detección/marcado.
  - NO imputa, NO elimina filas, NO alinea temporalmente entre fuentes — eso
    queda se hace en 05_build_dataset.py.
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
CLEAN_DIR = Path(__file__).resolve().parents[2] / "data" / "clean"

RAW_PATHS = {
    "era5_diario": RAW_DIR / "clima" / "era5_diario.csv",
    "et_mensual": RAW_DIR / "clima" / "et_mensual.csv",
    "modis_16dias": RAW_DIR / "ndvi_evi" / "modis_16dias.csv",
}

CLEAN_PATHS = {
    "era5_diario": CLEAN_DIR / "clima" / "era5_diario.csv",
    "et_mensual": CLEAN_DIR / "clima" / "et_mensual.csv",
    "modis_16dias": CLEAN_DIR / "ndvi_evi" / "modis_16dias.csv",
}

# Rangos físicamente plausibles y AMPLIOS para Cauca/Nariño (no ajustados a la
# ventana corta del Anteproyecto). None = sin cota en ese extremo. Una
# variable ausente en un archivo simplemente no se evalúa.
PLAUSIBLE_RANGES = {
    "tmax_c": (0, 45),
    "tmin_c": (0, 45),
    "tmean_c": (0, 45),
    "dewpoint_c": (0, 45),
    "precip_mm": (0, None),
    "pet_mm": (0, None),
    "et_mm": (0, None),
    "soil_moist_layer1": (0, 1),
    "lai_high": (0, 10),
    "ndvi": (-1, 1),
    "evi": (-1, 1),
}


def load_raw():
    return {name: pd.read_csv(path) for name, path in RAW_PATHS.items()}


def correct_era5_pet_sign(dfs):
    """Corrige el signo de `pet_mm` (potencial evapotranspiración) en
    era5_diario, sin tocar el CSV crudo en data/raw/ ni 01_extract_era5.py.

    ERA5-Land define `potential_evaporation_sum` con convención de flujo
    descendente-positivo (viene de ECMWF): la evapotranspiración, al ser un
    flujo ascendente (agua que sale de la superficie hacia la atmósfera),
    queda registrada con signo negativo en el dato crudo. Por eso el 100% de
    los valores de pet_mm salían negativos tras la conversión de unidades en
    prep_bands() de 01_extract_era5.py. Se multiplica por -1 aquí, en la capa
    de limpieza, para que pet_mm represente evapotranspiración potencial en
    su signo físico habitual (>= 0) antes de evaluar el rango plausible.
    """
    df = dfs["era5_diario"].copy()
    if "pet_mm" in df.columns:
        df["pet_mm"] = -df["pet_mm"]
    dfs = dict(dfs)
    dfs["era5_diario"] = df
    return dfs


def numeric_columns(df):
    return [c for c in df.columns if c not in ("date", "region")]


def validate_regions(dfs):
    """Confirma que el set de valores de `region` sea idéntico en los tres
    archivos (no que las filas coincidan 1 a 1, cada archivo tiene su propia
    cadencia)."""
    region_sets = {name: set(df["region"].unique()) for name, df in dfs.items()}
    reference = next(iter(region_sets.values()))
    all_equal = all(regions == reference for regions in region_sets.values())
    return all_equal, region_sets


def describe_variables(df, file_label):
    rows = []
    for col in numeric_columns(df):
        series = df[col]
        rows.append(
            {
                "archivo": file_label,
                "variable": col,
                "min": series.min(),
                "max": series.max(),
                "media": series.mean(),
                "std": series.std(),
                "n_validos": int(series.notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def null_report(df, file_label):
    n = len(df)
    rows = []
    for col in numeric_columns(df):
        n_null = int(df[col].isna().sum())
        rows.append(
            {
                "archivo": file_label,
                "variable": col,
                "n_nulos": n_null,
                "pct_nulos": round(100 * n_null / n, 2) if n else 0.0,
            }
        )
    return pd.DataFrame(rows)


def flag_out_of_range(df):
    """Agrega una columna booleana `<variable>_fuera_de_rango` por cada
    variable con rango definido. No elimina ni modifica el valor original."""
    df = df.copy()
    for col in numeric_columns(df):
        if col not in PLAUSIBLE_RANGES:
            continue
        low, high = PLAUSIBLE_RANGES[col]
        mask = pd.Series(False, index=df.index)
        if low is not None:
            mask |= df[col] < low
        if high is not None:
            mask |= df[col] > high
        mask &= df[col].notna()
        df[f"{col}_fuera_de_rango"] = mask
    return df


def flag_duplicates(df):
    """Agrega `es_duplicado` = True en todas las filas que comparten
    (date, region) con al menos otra fila. No elimina ninguna."""
    df = df.copy()
    df["es_duplicado"] = df.duplicated(subset=["date", "region"], keep=False)
    return df


def main():
    dfs = load_raw()
    dfs = correct_era5_pet_sign(dfs)

    regions_ok, region_sets = validate_regions(dfs)
    print("Validación de columna `region`:")
    for name, regions in region_sets.items():
        print(f"  {name}: {sorted(regions)}")
    print(f"  -> idénticas entre los tres archivos: {regions_ok}")
    if not regions_ok:
        raise ValueError(
            "Los valores de 'region' no coinciden entre los tres archivos crudos; "
            "revisar extracción antes de continuar."
        )

    report_lines = [
        "# Reporte de calidad — 04_clean_transform.py",
        "",
        f"Validación de `region` idéntica entre archivos: **{regions_ok}**",
        f"Valores de region: {sorted(next(iter(region_sets.values())))}",
        "",
        "**Corrección aplicada:** `pet_mm` en `era5_diario` se multiplicó por "
        "-1 respecto al crudo de `data/raw/`. ERA5-Land define "
        "`potential_evaporation_sum` con convención de flujo "
        "descendente-positivo, así que la evapotranspiración (flujo "
        "ascendente) sale negativa en el dato crudo. El CSV en `data/raw/` y "
        "`01_extract_era5.py` no se modificaron; la corrección vive solo en "
        "esta capa de limpieza (`data/clean/`).",
        "",
    ]

    stats_frames = []
    nulls_frames = []

    for name, df in dfs.items():
        stats_frames.append(describe_variables(df, name))
        nulls_frames.append(null_report(df, name))

        df_flagged = flag_out_of_range(df)
        df_flagged = flag_duplicates(df_flagged)

        n_dupes = int(df_flagged["es_duplicado"].sum())
        out_of_range_cols = [c for c in df_flagged.columns if c.endswith("_fuera_de_rango")]
        n_out_of_range = int(df_flagged[out_of_range_cols].any(axis=1).sum()) if out_of_range_cols else 0

        clean_path = CLEAN_PATHS[name]
        clean_path.parent.mkdir(parents=True, exist_ok=True)
        df_flagged.to_csv(clean_path, index=False)

        print(f"\n{name}: {len(df)} filas -> {clean_path}")
        print(f"  duplicados (date+region), filas marcadas: {n_dupes}")
        print(f"  filas con algún valor fuera de rango físico: {n_out_of_range}")

        report_lines.append(f"## {name}")
        report_lines.append("")
        report_lines.append(f"- Archivo crudo: `{RAW_PATHS[name].relative_to(RAW_DIR.parents[0])}`")
        report_lines.append(f"- Archivo limpio: `{clean_path.relative_to(CLEAN_DIR.parents[0])}`")
        report_lines.append(f"- Filas: {len(df)}")
        report_lines.append(f"- Duplicados (date+region), filas marcadas: {n_dupes}")
        report_lines.append(f"- Filas con algún valor fuera de rango físico: {n_out_of_range}")
        report_lines.append("")

    stats_df = pd.concat(stats_frames, ignore_index=True)
    nulls_df = pd.concat(nulls_frames, ignore_index=True)

    report_lines.append("## Estadísticas descriptivas por variable y archivo")
    report_lines.append("")
    report_lines.append(stats_df.to_markdown(index=False))
    report_lines.append("")
    report_lines.append("## % de nulos reales por variable y archivo")
    report_lines.append("")
    report_lines.append(nulls_df.to_markdown(index=False))
    report_lines.append("")
    report_lines.append("## Rangos físicamente plausibles usados para marcar (no filtrar)")
    report_lines.append("")
    report_lines.append("| variable | mínimo | máximo |")
    report_lines.append("|---|---|---|")
    for var, (low, high) in PLAUSIBLE_RANGES.items():
        report_lines.append(f"| {var} | {low if low is not None else '-'} | {high if high is not None else '-'} |")
    report_lines.append("")
    report_lines.append(
        "Nota: estos rangos son deliberadamente amplios y no corresponden a los "
        "valores observados en el Anteproyecto (ventana 2023-2025), que no "
        "representa toda la variabilidad del rango histórico ampliado "
        "(2000-hoy). Ningún valor fue eliminado ni imputado en este paso."
    )

    report_path = CLEAN_DIR / "quality_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nReporte de calidad guardado en: {report_path}")


if __name__ == "__main__":
    main()
