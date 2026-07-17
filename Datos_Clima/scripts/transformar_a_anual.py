import sys
from pathlib import Path

import pandas as pd

# ============================================================
# CONFIGURA AQUÍ el archivo de entrada
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVO_ENTRADA = BASE_DIR / "Datos_por_municipio" / "Por_Dia" / "duplicados_Oaxaca.csv"

# Columnas que se PROMEDIAN (temperaturas)
COLS_PROMEDIO = ["temp_max", "temp_min", "temp_app_max", "temp_app_min"]

# Columnas que se SUMAN (valores acumulados por día)
COLS_SUMA = ["lluvia_acumulada", "evapotranspiracion"]

# Columnas que se mantienen fijas (no cambian dentro de un municipio)
COLS_FIJAS = ["latitud", "longitud"]
# ============================================================


def cargar_datos(archivo_entrada: str | Path) -> pd.DataFrame:
    ruta = Path(archivo_entrada)
    if not ruta.is_absolute():
        ruta = (BASE_DIR / ruta).resolve()

    if ruta.suffix.lower() == ".csv":
        df = pd.read_csv(ruta)
    elif ruta.suffix.lower() in {".xlsx", ".xls", ".xlsm"}:
        df = pd.read_excel(ruta)
    else:
        raise ValueError(f"Formato no soportado: {ruta.suffix}")

    if "fecha" not in df.columns:
        raise KeyError("El archivo no contiene la columna 'fecha'.")

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["fecha"])
    return df


def transformar_a_anual(archivo_entrada: str | Path) -> pd.DataFrame:
    df = cargar_datos(archivo_entrada)

    # Año de cada registro
    df["anio"] = df["fecha"].dt.year

    agregaciones = {col: "mean" for col in COLS_PROMEDIO}
    agregaciones.update({col: "sum" for col in COLS_SUMA})
    agregaciones.update({col: "first" for col in COLS_FIJAS})

    df_anual = (
        df.groupby(["municipio", "anio"])
        .agg(agregaciones)
        .reset_index()
    )

    cols_redondear = COLS_PROMEDIO + COLS_SUMA
    df_anual[cols_redondear] = df_anual[cols_redondear].round(2)

    df_anual = df_anual.sort_values(["municipio", "anio"]).reset_index(drop=True)
    return df_anual


def procesar_archivo(archivo_entrada: str | Path):
    ruta = Path(archivo_entrada)
    if not ruta.is_absolute():
        ruta = (BASE_DIR / ruta).resolve()

    df_anual = transformar_a_anual(ruta)
    salida = ruta.with_name(f"{ruta.stem}_ANUAL.csv")
    df_anual.to_csv(salida, index=False)
    print(f"[OK] {ruta} -> {salida}  ({len(df_anual)} filas)")


if __name__ == "__main__":
    # Si se pasan archivos por línea de comandos, procesa esos.
    # Si no, procesa el ARCHIVO_ENTRADA definido arriba.
    archivos = sys.argv[1:] if len(sys.argv) > 1 else [ARCHIVO_ENTRADA]

    for archivo in archivos:
        procesar_archivo(archivo)
