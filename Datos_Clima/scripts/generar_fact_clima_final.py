from pathlib import Path
import pandas as pd
import unicodedata

root = Path(r'C:/Users/rodol/Downloads/clima/dengue_Proyecto_BI')
clima = pd.read_csv(root / 'Datos_Clima/Datos_por_estado/clima_mexico_estados_2020_2026.csv')
tiempo = pd.read_csv(root / 'DIMENSIONES/DIM_TIEMPO.csv')
geo = pd.read_csv(root / 'DIMENSIONES/DIM_GEOGRAFIA.csv')


def n(v):
    if pd.isna(v):
        return ''
    t = str(v).strip().lower()
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(ch for ch in t if not unicodedata.combining(ch))
    for ch in [' ', '-', '_', '.', ',', '(', ')', '/', "'", '¿', '?', '¡', '!', 'á', 'é', 'í', 'ó', 'ú', 'ñ']:
        t = t.replace(ch, '')
    return t

geo = geo.copy()
geo['entidad_norm'] = geo['entidad'].apply(n)
geo['municipio_norm'] = geo['municipio'].apply(n)
geo_estado = geo[geo['municipio'].astype(str).str.upper().eq('NO ESPECIFICADO')][['id_geografia', 'entidad_norm']].drop_duplicates(subset=['entidad_norm'])
clima['estado_norm'] = clima['estado'].apply(n)
clima['fecha'] = pd.to_datetime(clima['fecha'], format='%d/%m/%Y', errors='coerce')
tiempo['fecha'] = pd.to_datetime(tiempo['fecha'], errors='coerce')
tiempo = tiempo[['id_tiempo', 'fecha']].drop_duplicates(subset=['fecha'])

fact = clima.merge(tiempo, on='fecha', how='left').dropna(subset=['id_tiempo'])
fact = fact.merge(geo_estado.rename(columns={'entidad_norm': 'estado_norm', 'id_geografia': 'id_geografia'}), on='estado_norm', how='left').dropna(subset=['id_geografia'])
fact = fact[['id_tiempo', 'id_geografia', 'temp_max', 'temp_min', 'lluvia_acumulada', 'evapotranspiracion']].copy()
fact = fact.sort_values(['id_tiempo', 'id_geografia']).reset_index(drop=True)

out = root / 'HECHOS' / 'Fact_Clima.csv'
out.parent.mkdir(parents=True, exist_ok=True)
fact.to_csv(out, index=False)
print(f'archivo={out}')
print(f'filas={len(fact)}')
print(fact.head(5).to_string(index=False))
