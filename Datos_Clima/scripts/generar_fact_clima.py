import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "Datos_Clima"
DIM_DIR = ROOT / "DIMENSIONES"
HECHOS_DIR = ROOT / "HECHOS"
HECHOS_DIR.mkdir(parents=True, exist_ok=True)

CLIMA_DIA_CSV = DATA_DIR / "Datos_por_estado" / "clima_mexico_estados_2020_2026.csv"
DIM_GEO_CSV = DIM_DIR / "DIM_GEOGRAFIA.csv"
DIM_TIEMPO_CSV = DIM_DIR / "DIM_TIEMPO.csv"
POBLACION_CSV = DATA_DIR / "Datos_por_municipio" / "poblacion.csv"
FACT_OUTPUT = HECHOS_DIR / "Fact_Clima.csv"


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    for ch in [" ", "-", "_", ".", ",", "(", ")", "/", "'", "¿", "?", "¡", "!", "á", "é", "í", "ó", "ú", "ñ"]:
        texto = texto.replace(ch, "")
    return texto


def actualizar_dim_geografia():
    print("[1/3] Leyendo DIM_GEOGRAFIA y poblacion.csv...")
    geo = pd.read_csv(DIM_GEO_CSV)
    pob = pd.read_csv(POBLACION_CSV)

    geo = geo.copy()
    pob = pob.copy()

    geo["entidad_norm"] = geo["entidad"].apply(normalizar_texto)
    geo["municipio_norm"] = geo["municipio"].apply(normalizar_texto)
    pob["entidad_norm"] = pob["entidad"].apply(normalizar_texto)
    pob["municipio_norm"] = pob["municipio"].apply(normalizar_texto)

    poblacion_map = (
        pob[["entidad_norm", "municipio_norm", "latitud", "longitud"]]
        .drop_duplicates(subset=["entidad_norm", "municipio_norm"])
        .copy()
    )
    poblacion_map = poblacion_map.rename(columns={"latitud": "latitud_pob", "longitud": "longitud_pob"})

    geo = geo.merge(poblacion_map, on=["entidad_norm", "municipio_norm"], how="left")
    geo["latitud"] = pd.to_numeric(geo["latitud"], errors="coerce")
    geo["longitud"] = pd.to_numeric(geo["longitud"], errors="coerce")
    geo["latitud_pob"] = pd.to_numeric(geo["latitud_pob"], errors="coerce")
    geo["longitud_pob"] = pd.to_numeric(geo["longitud_pob"], errors="coerce")

    geo["latitud"] = geo["latitud"].combine_first(geo["latitud_pob"])
    geo["longitud"] = geo["longitud"].combine_first(geo["longitud_pob"])

    geo = geo.drop(columns=["entidad_norm", "municipio_norm", "latitud_pob", "longitud_pob"])
    geo = geo.sort_values(["entidad", "municipio"]).reset_index(drop=True)

    geo.to_csv(DIM_GEO_CSV, index=False)
    print(f"[OK] Se actualizaron coordenadas en {DIM_GEO_CSV.name} ({len(geo)} filas)")
    return geo


def construir_fact_clima():
    print("[2/3] Cargando datos diarios de clima y tiempo...")
    clima = pd.read_csv(CLIMA_DIA_CSV)
    tiempo = pd.read_csv(DIM_TIEMPO_CSV)
    geo = pd.read_csv(DIM_GEO_CSV)

    clima["fecha"] = pd.to_datetime(clima["fecha"], format="%d/%m/%Y", errors="coerce")
    tiempo["fecha"] = pd.to_datetime(tiempo["fecha"], errors="coerce")

    tiempo = tiempo[["id_tiempo", "fecha"]].drop_duplicates(subset=["fecha"])

    geo = geo.copy()
    geo["entidad_norm"] = geo["entidad"].apply(normalizar_texto)
    geo["municipio_norm"] = geo["municipio"].apply(normalizar_texto)

    geo_estado = geo[geo["municipio"].astype(str).str.upper().eq("NO ESPECIFICADO")].copy()
    geo_estado = geo_estado[["id_geografia", "entidad_norm"]].drop_duplicates(subset=["entidad_norm"])

    clima["estado_norm"] = clima["estado"].apply(normalizar_texto)

    fact = clima.merge(tiempo, left_on="fecha", right_on="fecha", how="left")
    fact = fact.dropna(subset=["id_tiempo"])

    fact = fact.merge(
        geo_estado.rename(columns={"entidad_norm": "estado_norm", "id_geografia": "id_geografia"}),
        on="estado_norm",
        how="left",
    )
    fact = fact.dropna(subset=["id_geografia"])

    fact = fact[[
        "id_tiempo",
        "id_geografia",
        "temp_max",
        "temp_min",
        "lluvia_acumulada",
        "evapotranspiracion",
    ]].copy()

    fact = fact.sort_values(["id_tiempo", "id_geografia"]).reset_index(drop=True)
    fact.to_csv(FACT_OUTPUT, index=False)
    print(f"[OK] Se generó {FACT_OUTPUT} con {len(fact)} filas")
    print(f"[3/3] Vista previa:\n{fact.head(10).to_string(index=False)}")


if __name__ == "__main__":
    actualizar_dim_geografia()
    construir_fact_clima()
