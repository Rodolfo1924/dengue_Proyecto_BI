import pandas as pd
import sys
from pathlib import Path

# ============================================================
# CONFIGURA AQUÍ el archivo de entrada
# ============================================================
ARCHIVO_ENTRADA = "Datos_Clima\Datos_por_municipio\clima_Hidalgo.xlsx"   # <-- cambia esto por cada archivo

# Columnas que se PROMEDIAN (temperaturas)
COLS_PROMEDIO = ["temp_max", "temp_min", "temp_app_max", "temp_app_min"]

# Columnas que se SUMAN (valores acumulados por día)
COLS_SUMA = ["lluvia_acumulada", "evapotranspiracion"]

# Columnas que se mantienen fijas (no cambian dentro de un municipio)
COLS_FIJAS = ["latitud", "longitud"]
# ============================================================


def transformar_a_anual(archivo_entrada: str) -> pd.DataFrame:
    df = pd.read_excel(archivo_entrada)

    # Detectar formato de fecha automáticamente (acepta aaaa-mm-dd ISO o dd/mm/aaaa)
    df["fecha"] = pd.to_datetime(df["fecha"], format="mixed", dayfirst=True)

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


def procesar_archivo(archivo_entrada: str):
    ruta = Path(archivo_entrada)
    df_anual = transformar_a_anual(archivo_entrada)

    salida = ruta.stem + "_ANUAL.xlsx"
    df_anual.to_excel(salida, index=False)
    print(f"[OK] {archivo_entrada} -> {salida}  ({len(df_anual)} filas)")


if __name__ == "__main__":
    # Si se pasan archivos por línea de comandos, procesa esos.
    # Si no, procesa el ARCHIVO_ENTRADA definido arriba.
    archivos = sys.argv[1:] if len(sys.argv) > 1 else [ARCHIVO_ENTRADA]

    for archivo in archivos:
        procesar_archivo(archivo)
