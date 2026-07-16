import requests
import pandas as pd
import time
import os

# ==========================================================
# CONFIGURACIÓN
# ==========================================================

# Cambia este valor por el estado que quieras descargar
ESTADO = "Oaxaca"

# Ruta del CSV con los municipios (columnas: entidad, municipio, latitud, longitud)
CSV_MUNICIPIOS = r"Datos_por_municipio\poblacion.csv"

URL = "https://archive-api.open-meteo.com/v1/archive"

VARIABLES = (
    "temperature_2m_max,temperature_2m_min,"
    "apparent_temperature_max,apparent_temperature_min,"
    "rain_sum,et0_fao_evapotranspiration"
)

# Rango total, partido en años para no truncar respuestas
RANGO_INICIO = 2020
RANGO_FIN = 2026  # hasta junio 2026

TAM_LOTE = 10              # municipios por request
MAX_REINTENTOS = 5         # reintentos ante errores temporales (429 pasajero, timeouts, etc.)
ESPERA_ENTRE_REQUESTS = 1.2  # segundos entre peticiones exitosas

RUTA_SALIDA = "Datos_por_municipio\\Por_Dia"
os.makedirs(RUTA_SALIDA, exist_ok=True)
nombre = ESTADO.replace(" ", "_")
ARCHIVO_CSV = os.path.join(RUTA_SALIDA, f"clima_{nombre}.csv")
ARCHIVO_LOG_FALLOS = os.path.join(RUTA_SALIDA, f"fallos_{nombre}.csv")

# ==========================================================
# LEER CSV Y FILTRAR ESTADO
# ==========================================================

municipios = pd.read_csv(CSV_MUNICIPIOS)
municipios = municipios[
    municipios["entidad"].str.strip().str.lower() == ESTADO.strip().lower()
].reset_index(drop=True)

if municipios.empty:
    print("No se encontró el estado:", ESTADO)
    raise SystemExit(1)

print(f"\nEstado: {ESTADO}")
print(f"Municipios: {len(municipios)}")

# ==========================================================
# RETOMAR SI YA HAY DESCARGAS PREVIAS (checkpoint)
# ==========================================================

ya_descargados = set()
if os.path.exists(ARCHIVO_CSV):
    df_previo = pd.read_csv(ARCHIVO_CSV, usecols=["municipio", "anio"])
    ya_descargados = set(zip(df_previo["municipio"], df_previo["anio"]))
    print(f"Retomando: {len(ya_descargados)} combinaciones municipio-año ya descargadas.")

fallos = []


def escribir_lote(registros):
    """Guarda incrementalmente para no perder todo si se interrumpe a la mitad."""
    df_lote = pd.DataFrame(registros)
    escribir_encabezado = not os.path.exists(ARCHIVO_CSV)
    df_lote.to_csv(ARCHIVO_CSV, mode="a", header=escribir_encabezado, index=False)


def pedir_con_reintentos(params):
    """
    Hace la petición con reintentos y backoff ante errores temporales.
    Si detecta que se agotó el límite DIARIO de la API, detiene el script
    por completo con un mensaje claro (reintentar no sirve hasta el día siguiente).
    """
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = requests.get(URL, params=params, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"  Error de conexión: {e}. Reintentando en 5s...")
            time.sleep(5)
            continue

        if resp.status_code == 200:
            return resp

        if resp.status_code == 429:
            if "Daily API request limit exceeded" in resp.text:
                print("\n*** Límite DIARIO de la API agotado. ***")
                print("*** Detén el script y vuelve a correrlo mañana. ***")
                print("*** Gracias al checkpoint, retomará donde se quedó. ***")
                raise SystemExit(1)

            espera = 5 * intento  # backoff simple
            print(f"  Rate limit temporal (429). Esperando {espera}s (intento {intento}/{MAX_REINTENTOS})...")
            time.sleep(espera)
            continue

        print(f"  Error {resp.status_code}: {resp.text[:200]}")
        time.sleep(3)

    return None


# ==========================================================
# DESCARGA: por año, por lote de municipios
# ==========================================================

for anio in range(RANGO_INICIO, RANGO_FIN + 1):
    fecha_inicio = f"{anio}-01-01"
    fecha_fin = f"{anio}-06-30" if anio == RANGO_FIN else f"{anio}-12-31"

    print(f"\n=== Año {anio} ({fecha_inicio} a {fecha_fin}) ===")

    for inicio in range(0, len(municipios), TAM_LOTE):
        fin = min(inicio + TAM_LOTE, len(municipios))
        lote = municipios.iloc[inicio:fin]

        # Saltar municipios que ya se descargaron para este año
        lote_pendiente = lote[
            ~lote["municipio"].apply(lambda m: (m, anio) in ya_descargados)
        ]
        if lote_pendiente.empty:
            continue

        print(f"  Lote {inicio + 1}-{fin}: {len(lote_pendiente)} municipios pendientes")

        params = {
            "latitude": ",".join(lote_pendiente["latitud"].astype(str)),
            "longitude": ",".join(lote_pendiente["longitud"].astype(str)),
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
            "daily": VARIABLES,
            "timezone": "America/Mexico_City",
        }

        respuesta = pedir_con_reintentos(params)

        if respuesta is None:
            print(f"  -> Lote fallido tras {MAX_REINTENTOS} intentos, se registra para reintento manual.")
            fallos.extend(lote_pendiente["municipio"].tolist())
            continue

        datos = respuesta.json()
        if isinstance(datos, dict):
            datos = [datos]

        # VALIDACIÓN: ¿coincide el número de resultados con lo pedido?
        if len(datos) != len(lote_pendiente):
            print(f"  ADVERTENCIA: pedí {len(lote_pendiente)} y recibí {len(datos)} -> posible truncamiento")

        registros = []
        for i, municipio_data in enumerate(datos):
            if i >= len(lote_pendiente):
                break
            municipio = lote_pendiente.iloc[i]

            if "daily" not in municipio_data:
                print(f"  Sin datos 'daily' para {municipio['municipio']}, se omite.")
                fallos.append(municipio["municipio"])
                continue

            daily = municipio_data["daily"]

            for j in range(len(daily["time"])):
                registros.append({
                    "fecha": daily["time"][j],
                    "anio": anio,
                    "municipio": municipio["municipio"],
                    "latitud": municipio["latitud"],
                    "longitud": municipio["longitud"],
                    "temp_max": daily["temperature_2m_max"][j],
                    "temp_min": daily["temperature_2m_min"][j],
                    "temp_app_max": daily["apparent_temperature_max"][j],
                    "temp_app_min": daily["apparent_temperature_min"][j],
                    "lluvia_acumulada": daily["rain_sum"][j],
                    "evapotranspiracion": daily["et0_fao_evapotranspiration"][j],
                })

        if registros:
            escribir_lote(registros)

        time.sleep(ESPERA_ENTRE_REQUESTS)

# ==========================================================
# REPORTE FINAL
# ==========================================================

if fallos:
    pd.DataFrame({"municipio_fallido": fallos}).to_csv(ARCHIVO_LOG_FALLOS, index=False)
    print(f"\n{len(fallos)} municipios con fallos guardados en {ARCHIVO_LOG_FALLOS}")

print("\n========================================")
print("Proceso terminado.")
print(f"Archivo generado (CSV incremental): {ARCHIVO_CSV}")
print("========================================")