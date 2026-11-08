# Contexto del Proyecto: SECOP-Analytics

## 1. Identificación y Propósito
- **Nombre:** SECOP-Analytics: Sistema de Inteligencia Empresarial y Predicción para la Contratación Estatal en Colombia.
- **Entidad:** Universidad del Valle – Sede Tuluá | Facultad de Ingeniería | Ingeniería de Sistemas.
- **Asignatura:** Técnicas de Pruebas de Software (Docente: Ing. Luis Adrián Lasso C., M.Sc.).
- **Periodo y Datos:** Contratos de SECOP II publicados en `datos.gov.co` (vigencias 2021–2026), con un volumen de referencia de más de 1.000.000 de registros y un dataset local de muestra de 10.000 registros (`secop muestra 10k 2022.csv`).

## 2. Equipo y Roles
- **Samuel Escobar Rivera (2266363):** Líder de Arquitectura, Backend y MongoDB.
- **Juan David Cuellar López (2266087):** Ingeniero de Datos, ETL (CRISP-DM) y Machine Learning.
- **Joseph Herrera Libreros (2266309):** Frontend (Streamlit), UI/UX y Aseguramiento de Calidad (QA / Pruebas).

## 3. Arquitectura y Patrones de Diseño Obligatorios
1. **Esquema en Estrella Lógico / Físico NoSQL:**
   - **Colección de Hechos:** `FACT_CONTRATOS` (métricas: `cuantia_inicial`, `valor_adiciones`, `cuantia_final`, `plazo_ejecucion_dias`, `tiene_adicion`, `score_riesgo_anomalia`).
   - **Dimensiones Embebidas (*Embedding*):** `geografia` (departamento, municipio), `tiempo` (fecha, año, mes), `clasificacion` (modalidad, tipo, estado, UNSPSC).
   - **Referencias Extendidas:** `entidad` (nit, nombre, orden) y `proveedor` (documento, nombre, es_pyme).
2. **Patrón Arquitectónico MVC:**
   - Separación estricta entre Modelos (datos y ML), Controladores (sesión, roles, lógica) y Vistas (componentes Streamlit/Plotly).
3. **Patrón Creacional Singleton:**
   - Instancia única en memoria para la carga de datos (`@st.cache_resource`) o conexión a MongoDB, evitando fugas de memoria o saturación de sockets.
4. **Patrón Creacional Builder (`ConsultaSecopBuilder`):**
   - Construcción modular y encadenable (*fluent interface*) de los 10 filtros dinámicos del dashboard, emitiendo predicados estilo `$match` de MongoDB.

## 4. Usuarios y Roles de Acceso (RBAC)
- `Admin`: Gestión de datos ETL, reindexación, gestión de usuarios y reentrenamiento.
- `Analista_BI`: Acceso completo a filtros dinámicos, 10 KPIs, 8 gráficas, simulación ML y exportación.
- `Auditor_Veedor`: Acceso de solo lectura para auditoría ciudadana y monitoreo de riesgos.