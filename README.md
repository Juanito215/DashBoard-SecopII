# 🏛️ SECOP-Analytics: Sistema de Inteligencia Empresarial y Predicción para la Contratación Estatal en Colombia

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/UI-Streamlit%201.30%2B-red.svg)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/Database-MongoDB%20NoSQL-green.svg)](https://www.mongodb.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Plataforma de **Inteligencia de Negocios (Business Intelligence - BI)** y **Ciencia de Datos** diseñada para procesar, depurar, auditar e inferir patrones sobre el gasto público contractual en Colombia. A partir de los Datos Abiertos transaccionales del **SECOP II (vigencias 2021–2026)** publicados por la Agencia Nacional de Contratación Pública (Colombia Compra Eficiente) en `datos.gov.co`, el sistema transforma millones de registros crudos en un cuadro de mando (*dashboard*) gerencial interactivo de alto rendimiento.

---

## 👥 Autores y Créditos Institucionales
* **Samuel Escobar Rivera** – Código: `2266363` (Líder de Arquitectura y Backend)
* **Juan David Cuellar López** – Código: `2266087` (Ingeniero de Datos y Machine Learning)
* **Joseph Herrera Libreros** – Código: `2266309` (Ingeniero de Frontend y Aseguramiento de Calidad - QA)

**Universidad del Valle – Sede Tuluá**[cite: 3, 4]  
Facultad de Ingeniería | Programa de Ingeniería de Sistemas[cite: 3, 4]  
Asignatura: *Técnicas de Pruebas de Software*[cite: 3, 4]  
Docente: **Ing. Luis Adrián Lasso C., M.Sc.**[cite: 3, 4]  
Año: **2026**[cite: 3, 4]

---

## 📌 Contexto y Planteamiento del Problema
A pesar de la disponibilidad pública de más de 1.000.000 de registros en el SECOP II[cite: 3, 4], la explotación efectiva de esta información enfrenta barreras operativas críticas[cite: 4]:
1. **Volumen masivo y heterogeneidad:** Disparidad en esquemas anuales, valores nulos, columnas renombradas e inconsistencias tipográficas que saturan las bases de datos relacionales tradicionales[cite: 3, 4].
2. **Ausencia de analítica gerencial interactiva:** Los portales estatales ofrecen descargas de archivos planos (CSV/JSON), pero carecen de paneles con filtros multidimensionales en tiempo real para la toma de decisiones presupuestales[cite: 4].
3. **Enfoque puramente reactivo:** Las revisiones convencionales fiscalizan contratos ya liquidados; no incorporan algoritmos de Machine Learning que anticipen sobrecostos o adiciones antes y durante la ejecución contractual[cite: 3, 4].

**SECOP-Analytics** resuelve este vacío integrando procesos **ETL (CRISP-DM)**[cite: 3, 4], almacenamiento en **MongoDB**[cite: 3, 4], patrones de diseño orientados a objetos (**MVC, Singleton, Builder**)[cite: 3, 4] y modelos predictivos supervisados en un tablero web reactivo.

---

## 🏗️ Arquitectura de Software y Patrones de Diseño

El sistema se estructura en capas desacopladas que garantizan modularidad, rendimiento en subsegundos y alta cohesión[cite: 3, 4]:

```text
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE VISTA (Streamlit)              │
│   Tablero Gerencial: 10 Filtros | 10 KPIs | 8 Gráficas BI   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                  CAPA CONTROLADOR (Patrón MVC)              │
│       Gestión de Sesión, Roles y Despacho de Consultas      │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┐ ┌─────────────▼───────────────┐
│     Patrón BUILDER          │ │      Patrón SINGLETON       │
│  (ConsultaSecopBuilder)     │ │  (Connection Pool / Memory) │
│ Construcción fluida de los  │ │ Instancia única y segura de │
│ 10 filtros dinámicos        │ │ acceso a los datos NoSQL    │
└──────────────┬──────────────┘ └─────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────────────────────▼───────────────┐
│                   CAPA MODELO Y DATOS                       │
│  - FACT_CONTRATOS (Esquema en Estrella Lógico / Embedding)  │
│  - Pipeline ETL (Limpieza y estandarización de tipos)       │
│  - Inferencia ML (Random Forest: Propensión a Adición)      │
└─────────────────────────────────────────────────────────────┘