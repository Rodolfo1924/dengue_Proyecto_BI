import requests
import pandas as pd

# 1. Diccionario completo con las coordenadas de los 32 estados de México
estados = [
    {"id": 0, "nombre": "Aguascalientes", "lat": 21.8823, "lon": -102.2826},
    {"id": 1, "nombre": "Baja California", "lat": 32.6278, "lon": -115.4545},
    {"id": 2, "nombre": "Baja California Sur", "lat": 24.1426, "lon": -110.3128},
    {"id": 3, "nombre": "Campeche", "lat": 19.8454, "lon": -90.5237},
    {"id": 4, "nombre": "Chiapas", "lat": 16.7569, "lon": -93.1292},
    {"id": 5, "nombre": "Chihuahua", "lat": 28.6330, "lon": -106.0691},
    {"id": 6, "nombre": "Ciudad de Mexico", "lat": 19.4326, "lon": -99.1332},
    {"id": 7, "nombre": "Coahuila", "lat": 25.4232, "lon": -101.0053},
    {"id": 8, "nombre": "Colima", "lat": 19.2433, "lon": -103.7247},
    {"id": 9, "nombre": "Durango", "lat": 24.0277, "lon": -104.6532},
    {"id": 10, "nombre": "Guanajuato", "lat": 21.0190, "lon": -101.2574},
    {"id": 11, "nombre": "Guerrero", "lat": 17.5513, "lon": -99.5005},
    {"id": 12, "nombre": "Hidalgo", "lat": 20.1011, "stack": "lon", "lon": -98.7591},
    {"id": 13, "nombre": "Jalisco", "lat": 20.6597, "lon": -103.3496},
    {"id": 14, "nombre": "Mexico", "lat": 19.2826, "lon": -99.6557},
    {"id": 15, "nombre": "Michoacan", "lat": 19.7006, "lon": -101.1864},
    {"id": 16, "nombre": "Morelos", "lat": 18.9220, "lon": -99.2348},
    {"id": 17, "nombre": "Nayarit", "lat": 21.5039, "lon": -104.8946},
    {"id": 18, "nombre": "Nuevo Leon", "lat": 25.6866, "lon": -100.3161},
    {"id": 19, "nombre": "Oaxaca", "lat": 17.0732, "lon": -96.7266},
    {"id": 20, "nombre": "Puebla", "lat": 19.0414, "lon": -98.2063},
    {"id": 21, "nombre": "Queretaro", "lat": 20.5888, "lon": -100.3899},
    {"id": 22, "nombre": "Quintana Roo", "lat": 18.5141, "lon": -88.3038},
    {"id": 23, "nombre": "San Luis Potosi", "lat": 22.1565, "lon": -100.9855},
    {"id": 24, "nombre": "Sinaloa", "lat": 24.8091, "lon": -107.3940},
    {"id": 25, "nombre": "Sonora", "lat": 29.0730, "lon": -110.9559},
    {"id": 26, "nombre": "Tabasco", "lat": 17.9892, "lon": -92.9475},
    {"id": 27, "nombre": "Tamaulipas", "lat": 23.7369, "lon": -99.1411},
    {"id": 28, "nombre": "Tlaxcala", "lat": 19.3182, "lon": -98.2375},
    {"id": 29, "nombre": "Veracruz", "lat": 19.5438, "lon": -96.9102},
    {"id": 30, "nombre": "Yucatan", "lat": 20.9674, "lon": -89.5926},
    {"id": 31, "nombre": "Zacatecas", "lat": 22.7709, "lon": -102.5832}
]

# 2. Separar coordenadas por comas
latitudes = ",".join([str(e["lat"]) for e in estados])
longitudes = ",".join([str(e["lon"]) for e in estados])

# 3. Parámetros corregidos para el archivo histórico (v1/archive)
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": latitudes,
    "longitude": longitudes,
    "start_date": "2020-01-01",
    "end_date": "2026-06-30",  # Acotado al último mes completo disponible en el histórico
    # Variables diarias estándar que acepta el endpoint /archive
    "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,rain_sum,et0_fao_evapotranspiration",
    "timezone": "America/Mexico_City",
    "format": "json"
}

print("Descargando datos climáticos de Open-Meteo...")
response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    all_rows = []
    
    # Si la respuesta es un solo diccionario (un único punto), lo volvemos lista
    if isinstance(data, dict):
        data = [data]
        
    for index, location_data in enumerate(data):
        estado_info = estados[index]
        daily_records = location_data["daily"]
        
        for i in range(len(daily_records["time"])):
            row = {
                "fecha": daily_records["time"][i],
                "estado": estado_info["nombre"],
                "latitud": estado_info["lat"],
                "longitud": estado_info["lon"],
                "temp_max": daily_records["temperature_2m_max"][i],
                "temp_min": daily_records["temperature_2m_min"][i],
                "temp_app_max": daily_records["apparent_temperature_max"][i],
                "temp_app_min": daily_records["apparent_temperature_min"][i],
                "lluvia_acumulada": daily_records["rain_sum"][i],
                "evapotranspiracion": daily_records["et0_fao_evapotranspiration"][i]
            }
            all_rows.append(row)
            
    df = pd.DataFrame(all_rows)
    df.to_csv("clima_mexico_estados_2020_2026.csv", index=False, encoding="utf-8")
    print("¡Archivo 'clima_mexico_estados_2020_2026.csv' guardado con éxito con los 32 estados!")
else:
    print(f"Error al consultar la API: {response.status_code}")
    print(response.text)  # Esto nos dirá exactamente qué parámetro falló si vuelve a ocurrir