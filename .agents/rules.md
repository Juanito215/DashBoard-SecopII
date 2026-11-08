# Reglas de Desarrollo y Operación para Agentes

## Regla 1: Integridad Arquitectónica
- **Cero Monolitos:** Todo código nuevo debe encajar en la estructura de carpetas: `src/controllers`, `src/database`, `src/etl`, `src/ml`, `src/queries`, `src/views`, `tests`.
- **Uso estricto del Patrón Builder:** Cualquier operación de filtrado sobre el dataset debe implementarse o extenderse a través de métodos en la clase `ConsultaSecopBuilder`. No usar filtros sueltos con sintaxis arbitraria de Pandas en la vista.
- **Uso estricto del Patrón Singleton:** Ningún componente puede instanciar lecturas de disco masivas repetitivas; debe consumir siempre la instancia del repositorio gestionada con `@st.cache_resource`.

## Regla 2: Manejo de Datos y ETL (CRISP-DM)
- **Moneda Local:** Todos los valores monetarios son en Pesos Colombianos (COP) como tipo numérico continuo (`Double`/`Float`). Siempre limpiar símbolos `$`, comas y puntos de miles.
- **Fechas:** Siempre parsear cadenas de texto a `datetime` o `ISODate`. Extraer explícitamente `anio_vigencia` y `mes_vigencia`.
- **Variables Analíticas Derivadas:**
  - `cuantia_final = cuantia_inicial + valor_adiciones`
  - `tiene_adicion = valor_adiciones > 0`
  - `plazo_ejecucion_dias = (fecha_fin - fecha_inicio).days` (o valor numérico depurado).

## Regla 3: Trazabilidad con Pruebas de Software (Capítulo 8)
- Todo módulo o funcionalidad debe correlacionarse con una Historia de Usuario (HU) y un Caso de Prueba de Aceptación Alfa:
  - `PA-ALFA-001` <-> Autenticación y Roles (HU-01, HU-02, HU-03)
  - `PA-ALFA-002` <-> Ingesta y Depuración ETL (HU-04 a HU-07)
  - `PA-ALFA-003` <-> Consultas con 10 Filtros Dinámicos (HU-08 a HU-15)
  - `PA-ALFA-004` <-> Analítica Descriptiva (10 KPIs y 5 Gráficas) (HU-19 a HU-26)
  - `PA-ALFA-005` <-> Analítica Predictiva y Riesgo de Adición (HU-27 a HU-29)
- Siempre que se genere código de UI, incluir paneles de telemetría (tiempo de respuesta, conteo de registros y criterios cumplidos) para facilitar la toma de capturas del informe académico.

## Regla 4: Rendimiento y Tolerancia a Fallos
- Las consultas y agregaciones sobre el dataset deben resolverse en menos de 1.5 segundos.
- Implementar bloques `try/except` con valores de fallback para evitar que valores nulos o atípicos de columnas de SECOP II provoquen errores en la interfaz de Streamlit.