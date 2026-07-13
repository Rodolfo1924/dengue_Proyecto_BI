import pandas as pd

# --- 1. Cargar datos ---
df = pd.read_csv("clima_mexico_estados_2020_2026.csv")

# La fecha viene como dd/mm/aaaa
df["fecha"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y")

# Columna auxiliar para agrupar por año-mes
df["anio_mes"] = df["fecha"].dt.to_period("M")

# --- 2. Definir cómo agregar cada columna ---
agregaciones = {
    "latitud": "first",              # fijo por estado
    "longitud": "first",             # fijo por estado
    "temp_max": "mean",              # promedio mensual
    "temp_min": "mean",
    "temp_app_max": "mean",
    "temp_app_min": "mean",
    "lluvia_acumulada": "sum",       # SUMA: es lluvia acumulada por día
    "evapotranspiracion": "sum",     # SUMA: también es un valor diario acumulado
}

# --- 3. Agrupar por estado y mes ---
df_mensual = (
    df.groupby(["estado", "anio_mes"])
    .agg(agregaciones)
    .reset_index()
)

# Redondear para que se vea limpio
cols_redondear = ["temp_max", "temp_min", "temp_app_max", "temp_app_min",
                   "lluvia_acumulada", "evapotranspiracion"]
df_mensual[cols_redondear] = df_mensual[cols_redondear].round(2)

# Convertir el periodo a texto tipo "2020-01"
df_mensual["anio_mes"] = df_mensual["anio_mes"].astype(str)

# Ordenar bonito
df_mensual = df_mensual.sort_values(["estado", "anio_mes"]).reset_index(drop=True)

# --- 4. Guardar resultado ---
df_mensual.to_csv("clima_mexico_estados_2020_2026_MENSUAL.csv", index=False)

print(df_mensual.head(15))
print(f"\nTotal de filas: {len(df_mensual)}")
