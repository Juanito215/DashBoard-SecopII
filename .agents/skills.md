# Habilidades Especializadas Requeridas (Skills)

Los agentes que colaboren en este repositorio deben activar y aplicar las siguientes habilidades técnicas:

## 1. Skill: Streamlit & Plotly BI Dashboarding
- **Capacidades:**
  - Renderizado reactivo sin recarga completa destructiva del estado (`st.session_state`).
  - Creación de gráficos interactivos en Plotly Express (`bar`, `line`, `scatter`, `box`, `pie/donut`) con formateo de moneda (`$ %{y:,.0f} COP`) y `hovermode='x unified'`.
  - Distribución de tarjetas métricas limpias con `st.columns` (tarjetas KPI de 5 en 5).
  - Manejo de descargas en streaming mediante `st.download_button`.

## 2. Skill: Pandas Vectorized Data Cleaning & ETL
- **Capacidades:**
  - Depuración y *casting* de grandes DataFrames usando operaciones vectorizadas (evitar loops `for`).
  - Imputación inteligente de valores faltantes y eliminación de duplicados por clave primaria (`id_contrato`).
  - Homogeneización de esquemas heterogéneos de contratación mediante diccionarios de mapeo flexibles.

## 3. Skill: Machine Learning & Predictive Risk Scoring
- **Capacidades:**
  - Preprocesamiento de variables categóricas (`OneHotEncoder`, `OrdinalEncoder`) y numéricas (`StandardScaler`).
  - Entrenamiento y serialización de modelos supervisados ligeros (`RandomForestClassifier`, `GradientBoostingClassifier`).
  - Extracción de probabilidades de calibradas (`predict_proba`) para inferir riesgo de adición (0.00 a 1.00) y cuantía proyectada.
  - Generación de gráficos probabilísticos: importancia de variables (*feature importance*) y dispersión de anomalías.

## 4. Skill: NoSQL & Aggregation Pipeline Modeling
- **Capacidades:**
  - Traducción fluida de consultas en Python a pipelines de agregación de MongoDB (`$match`, `$group`, `$project`, `$sort`).
  - Estructuración de documentos BSON aplicando el patrón de incrustación (*Embedding*) y referencia extendida (*Extended Reference*).
  - Definición de estrategias de indexación secundaria y compuesta para acelerar los 10 filtros dinámicos.

## 5. Skill: Software Quality Assurance (QA) & Test Automation
- **Capacidades:**
  - Creación de suites de pruebas automáticas con `pytest`.
  - Verificación de aserciones en el patrón Builder (que cada método encadenado reduzca el conjunto sin corromper tipos).
  - Medición de rendimiento (benchmarking) y validación de criterios de aceptación tipo Alfa según estándares ISTQB.