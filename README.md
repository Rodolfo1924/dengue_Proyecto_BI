# Analítica de BI para la Identificación de Zonas de Riesgo de Dengue mediante Variables Climáticas

Proyecto desarrollado para la materia de **Inteligencia de Negocios** del **Instituto Tecnológico de Matehuala**.

## Descripción del proyecto

El dengue es una enfermedad cuya incidencia está fuertemente influenciada por condiciones ambientales, como la temperatura y la precipitación. Este proyecto busca identificar **zonas de riesgo de dengue** mediante el análisis conjunto de variables climáticas, epidemiológicas y demográficas.

Para ello se diseñó un **modelo dimensional en esquema de constelación (galaxy schema)**, ya que el proyecto integra tres procesos de negocio distintos —incidencia epidemiológica, condiciones climáticas y dinámica poblacional— que comparten dimensiones comunes (tiempo, geografía, sexo y edad). Esta estructura permite realizar análisis cruzados, como:

- El cálculo de **tasas de incidencia** (casos por cada 100,000 habitantes).
- La **correlación entre variables climáticas** (temperatura, lluvia, evapotranspiración) y el número de casos reportados.

## Fuentes de datos

| Fuente | Datos que aporta |
|---|---|
| **Dirección General de Epidemiología** | Casos de dengue registrados (diagnóstico, institución notificante, comorbilidades, datos del paciente). |
| **Open-Meteo** | Variables climáticas diarias por estado (temperatura máx/mín, sensación térmica, lluvia acumulada, evapotranspiración). |
| **CONAPO** | Proyecciones y estimaciones de población por entidad, año, grupo de edad y sexo. |
| **INEGI** | Catálogo de claves geográficas oficiales (CVE_GEO, 2020), usado para estandarizar y unir las tres fuentes anteriores. |
| **INEGI (vía gist de lapanquecita)** | Latitud, longitud y población por municipio, 2020. Datos tomados de [poblacion.csv](https://gist.github.com/lapanquecita/1b819ec5373f9304efc52149e96a91b7), compilado por [@lapanquecita](https://github.com/lapanquecita) a partir de cifras de INEGI. |

## Modelo de datos

El modelo se compone de **3 tablas de hechos**:

- `Fact_Casos_Dengue` — grano: una fila por caso registrado.
- `Fact_Clima` — grano: una fila por día y estado.
- `Fact_Poblacion` — grano: una fila por año, entidad, grupo de edad y sexo.

Y de **dimensiones conformadas** compartidas entre ellas (`Dim_Tiempo`, `Dim_Geografia`, `Dim_Sexo`, `Dim_Edad`), además de **dimensiones exclusivas** de `Fact_Casos_Dengue` (`Dim_Institucion`, `Dim_Diagnostico` y `Dim_Comorbilidad` como dimensión basurero).

## Contexto académico

Proyecto realizado como parte de la materia de **Inteligencia de Negocios**, Instituto Tecnológico de Matehuala.

## Créditos de datos

- Latitud, longitud y población municipal: datos de **INEGI (2020)**, compilados en formato CSV por [@lapanquecita](https://github.com/lapanquecita) — [gist original](https://gist.github.com/lapanquecita/1b819ec5373f9304efc52149e96a91b7).
