import re
import sys
from pathlib import Path

import pandas as pd

# ============================================================
# CONFIGURA AQUÍ la carpeta de entrada y el archivo de salida
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
CARPETA_ENTRADA = BASE_DIR / "Datos_por_municipio" / "Por_Dia"
ARCHIVO_SALIDA = BASE_DIR / "Datos_por_municipio" / "clima_municipios.xlsx"
# ============================================================


def detectar_formato_real(ruta: Path) -> str:
    """Detecta el formato real por firma de bytes, sin confiar en la extensión."""
    with open(ruta, "rb") as f:
        firma = f.read(8)
    if firma.startswith(b"PK\x03\x04"):
        return "xlsx"
    if firma.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    try:
        firma.decode("utf-8")
        return "csv_o_texto"
    except UnicodeDecodeError:
        return "desconocido"


def cargar_archivo(ruta: Path) -> pd.DataFrame:
    formato_real = detectar_formato_real(ruta)

    if formato_real == "xlsx":
        df = pd.read_excel(ruta, engine="openpyxl")
    elif formato_real == "xls":
        df = pd.read_excel(ruta, engine="xlrd")
    elif formato_real == "csv_o_texto":
        df = pd.read_csv(ruta, sep=None, engine="python")
    else:
        raise ValueError(f"Formato no identificable: {ruta.name}")

    return df


def nombre_hoja_valido(nombre: str, usados: set) -> str:
    """
    Excel limita los nombres de hoja a 31 caracteres y prohíbe : \\ / ? * [ ]
    Esta función limpia el nombre y evita duplicados.
    """
    limpio = re.sub(r'[:\\/?*\[\]]', "_", nombre)
    limpio = limpio[:31]

    base = limpio
    contador = 1
    while limpio in usados:
        sufijo = f"_{contador}"
        limpio = base[: 31 - len(sufijo)] + sufijo
        contador += 1

    usados.add(limpio)
    return limpio


MAX_FILAS_HOJA = 1_048_576 - 1  # -1 por la fila de encabezado


def escribir_hoja(writer, df: pd.DataFrame, nombre_estado: str, usados: set):
    """
    Escribe el DataFrame en una o varias hojas si rebasa el límite de filas
    de Excel (1,048,576, contando el encabezado).
    """
    if len(df) <= MAX_FILAS_HOJA:
        hoja = nombre_hoja_valido(nombre_estado, usados)
        df.to_excel(writer, sheet_name=hoja, index=False)
        print(f"  [OK] hoja '{hoja}' ({len(df)} filas)")
        return

    n_partes = -(-len(df) // MAX_FILAS_HOJA)  # redondeo hacia arriba
    print(f"  [AVISO] {nombre_estado} tiene {len(df)} filas, se divide en {n_partes} hojas")

    for i in range(n_partes):
        inicio = i * MAX_FILAS_HOJA
        fin = inicio + MAX_FILAS_HOJA
        parte = df.iloc[inicio:fin]

        hoja = nombre_hoja_valido(f"{nombre_estado}_{i + 1}", usados)
        parte.to_excel(writer, sheet_name=hoja, index=False)
        print(f"  [OK] hoja '{hoja}' ({len(parte)} filas)")


def main():
    if not CARPETA_ENTRADA.exists():
        print(f"[ERROR] No existe la carpeta: {CARPETA_ENTRADA}")
        sys.exit(1)

    archivos = sorted(
        p for p in CARPETA_ENTRADA.iterdir()
        if p.suffix.lower() in {".xlsx", ".xls", ".csv"} and p.name.startswith("clima_")
    )

    if not archivos:
        print(f"[ERROR] No se encontraron archivos clima_*.xlsx/.csv en {CARPETA_ENTRADA}")
        sys.exit(1)

    print(f"Encontrados {len(archivos)} archivos. Combinando...")

    usados = set()
    ARCHIVO_SALIDA.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(ARCHIVO_SALIDA, engine="openpyxl") as writer:
        for archivo in archivos:
            # Nombre del estado a partir de "clima_Estado.xlsx" -> "Estado"
            nombre_estado = archivo.stem.replace("clima_", "", 1)

            try:
                df = cargar_archivo(archivo)
            except Exception as e:
                print(f"[OMITIDO] {archivo.name}: {e}")
                continue

            print(f"  {archivo.name} ({len(df)} filas totales)")
            escribir_hoja(writer, df, nombre_estado, usados)

    print(f"\nListo: {ARCHIVO_SALIDA}")


if __name__ == "__main__":
    main()