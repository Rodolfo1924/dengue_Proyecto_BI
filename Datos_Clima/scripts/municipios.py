import requests
import pandas as pd
import time

# ==========================================================
# CONFIGURACIÓN
# ==========================================================

# Cambia este valor por el estado que quieras descargar
ESTADO = "Guanajuato"

# Ruta del CSV
CSV_MUNICIPIOS = r"\Datos_por_municipio\poblacion.csv"

# Endpoint de Open-Meteo
URL = "https://archive-api.open-meteo.com/v1/archive"

PARAMS_BASE = {
    "start_date": "2020-01-01",
    "end_date": "2026-06-30",
    "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,rain_sum,et0_fao_evapotranspiration",
    "timezone": "America/Mexico_City"
}

# Número de municipios por consulta
TAM_LOTE = 20

# ==========================================================
# LEER CSV
# ==========================================================

municipios = pd.read_csv(CSV_MUNICIPIOS)

# Filtrar solo el estado deseado
municipios = municipios[
    municipios["entidad"].str.strip().str.lower()
    == ESTADO.strip().lower()
].reset_index(drop=True)

if municipios.empty:
    print("No se encontró el estado:", ESTADO)
    exit()

print(f"\nEstado: {ESTADO}")
print(f"Municipios: {len(municipios)}")

# ==========================================================
# DESCARGA
# ==========================================================

registros = []

for inicio in range(0, len(municipios), TAM_LOTE):

    fin = min(inicio + TAM_LOTE, len(municipios))

    print(f"Lote {inicio+1} - {fin}")

    lote = municipios.iloc[inicio:fin]

    latitudes = ",".join(lote["latitud"].astype(str))
    longitudes = ",".join(lote["longitud"].astype(str))

    params = PARAMS_BASE.copy()

    params["latitude"] = latitudes
    params["longitude"] = longitudes

    respuesta = requests.get(URL, params=params)

    if respuesta.status_code != 200:
        print("Error:", respuesta.status_code)
        print(respuesta.text)
        continue

    datos = respuesta.json()

    if isinstance(datos, dict):
        datos = [datos]

    for i, municipio_data in enumerate(datos):

        municipio = lote.iloc[i]

        daily = municipio_data["daily"]

        for j in range(len(daily["time"])):

            registros.append({

                "fecha": daily["time"][j],

                "municipio": municipio["municipio"],

                "latitud": municipio["latitud"],

                "longitud": municipio["longitud"],

                "temp_max":
                    daily["temperature_2m_max"][j],

                "temp_min":
                    daily["temperature_2m_min"][j],

                "temp_app_max":
                    daily["apparent_temperature_max"][j],

                "temp_app_min":
                    daily["apparent_temperature_min"][j],

                "lluvia_acumulada":
                    daily["rain_sum"][j],

                "evapotranspiracion":
                    daily["et0_fao_evapotranspiration"][j]

            })

    # Esperar un poco entre peticiones
    time.sleep(1)

# ==========================================================
# GUARDAR EXCEL
# ==========================================================

import os

df = pd.DataFrame(registros)

nombre = ESTADO.replace(" ", "_")

# Ruta de la carpeta donde quieres guardar
ruta = r"Datos_por_municipio"   # relativa a tu proyecto

# Crear la carpeta si no existe
os.makedirs(ruta, exist_ok=True)

# Construir la ruta completa del archivo
archivo = os.path.join(ruta, f"clima_{nombre}.xlsx")

df.to_excel(
    archivo,
    index=False,
    engine="openpyxl"
)

print("\n========================================")
print("Proceso terminado.")
print(f"Registros descargados: {len(df)}")
print(f"Archivo generado: {archivo}")
print("========================================")
