"""
Suite de Pruebas Automatizadas del Pipeline ETL y Esquema en Estrella
Caso de Prueba de Aceptación: PA-ALFA-002 (Ingesta y Depuración ETL)
Historia de Usuario: HU-02
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from datetime import datetime
import pandas as pd
import pytest
from src.database.connection import MongoConnectionSingleton
from src.etl.etl_pipeline import SecopETLPipeline


@pytest.fixture
def pipeline() -> SecopETLPipeline:
    """Retorna una instancia fresca del pipeline ETL."""
    return SecopETLPipeline()


def test_extraccion_columnas_mapeo(pipeline: SecopETLPipeline):
    """
    PA-ALFA-002: Valida que el pipeline reconozca y estandarice las columnas
    de SECOP II a nombres canónicos estructurados.
    """
    columnas_esperadas = [
        "id_contrato", "codigo_proceso", "cuantia_inicial", "valor_adiciones",
        "plazo_ejecucion_dias", "departamento", "municipio", "fecha_firma",
        "modalidad", "tipo_contrato", "estado", "codigo_unspsc",
        "nombre_entidad", "nit_entidad", "orden_entidad", "sector",
        "documento_proveedor", "proveedor", "es_pyme"
    ]

    # Probamos con el dataset ubicado en data/raw/
    df = pipeline.extraer_csv("data/raw/secop muestra 10k 2022.csv")

    assert len(df) == 10000, "El dataset original debe tener 10.000 registros"
    for col in columnas_esperadas:
        assert col in df.columns, f"La columna canónica '{col}' no fue generada en el mapeo"


def test_limpieza_monetaria_y_fechas(pipeline: SecopETLPipeline):
    """
    PA-ALFA-002: Comprueba que símbolos monetarios, comas y formatos mixtos
    se transformen a float continuo en COP y las fechas a ISODate / datetime.
    """
    datos_crudos = pd.DataFrame([
        {
            "id_contrato": "CO1.PCONTR.TEST01",
            "cuantia_inicial": "$ 15.000.000,50",
            "valor_adiciones": "$ 2,500,000.00",
            "fecha_firma": "2022-04-15",
            "plazo_ejecucion_dias": "90",
            "departamento": "valle del cauca",
            "municipio": "tuluá",
            "es_pyme": "Si",
            "nombre_entidad": "  Alcaldia  de Tulua  ",
            "proveedor": "  suministros   del valle sas  "
        },
        {
            "id_contrato": "CO1.PCONTR.TEST02",
            "cuantia_inicial": "0",  # Corrupta / menor o igual a cero (debe descartarse)
            "valor_adiciones": "0",
            "fecha_firma": "2022-08-20",
            "plazo_ejecucion_dias": "30",
            "departamento": "antioquia",
            "municipio": "medellin",
            "es_pyme": "No",
            "nombre_entidad": "Gobernacion",
            "proveedor": "Contratista"
        }
    ])

    df_extraido = pipeline.extraer_csv(datos_crudos)
    df_limpio, total_leidos, descartados = pipeline.transformar_datos(df_extraido)

    assert total_leidos == 2
    assert descartados == 1, "El registro con cuantía 0 debió descartarse"
    assert len(df_limpio) == 1

    fila = df_limpio.iloc[0]
    # Validación numérica en COP
    assert isinstance(fila["cuantia_inicial"], float)
    assert fila["cuantia_inicial"] == 15000000.50
    assert isinstance(fila["valor_adiciones"], float)
    assert fila["valor_adiciones"] == 2500000.00

    # Validación de limpieza de texto en mayúsculas sostenidas
    assert fila["nombre_entidad"] == "ALCALDIA DE TULUA"
    assert fila["proveedor"] == "SUMINISTROS DEL VALLE SAS"
    assert fila["departamento"] == "VALLE DEL CAUCA"
    assert fila["municipio"] == "TULUÁ"

    # Validación temporal
    assert fila["anio_vigencia"] == 2022
    assert fila["mes_vigencia"] == 4
    assert fila["trimestre"] == 2


def test_variables_derivadas(pipeline: SecopETLPipeline):
    """
    PA-ALFA-002 / Regla 2: Valida cálculo vectorizado de variables derivadas:
    - cuantia_final == cuantia_inicial + valor_adiciones
    - tiene_adicion == (valor_adiciones > 0)
    - plazo_ejecucion_dias >= 0
    """
    datos = pd.DataFrame([
        {
            "id_contrato": "CO1.PCONTR.CON_ADICION",
            "cuantia_inicial": 50000000.0,
            "valor_adiciones": 12000000.0,
            "fecha_firma": "2022-01-10",
            "plazo_ejecucion_dias": 180,
            "es_pyme": "Si"
        },
        {
            "id_contrato": "CO1.PCONTR.SIN_ADICION",
            "cuantia_inicial": 30000000.0,
            "valor_adiciones": 0.0,
            "fecha_firma": "2022-03-15",
            "plazo_ejecucion_dias": 60,
            "es_pyme": "No"
        }
    ])

    df_extraido = pipeline.extraer_csv(datos)
    df_limpio, _, _ = pipeline.transformar_datos(df_extraido)

    con_adicion = df_limpio[df_limpio["id_contrato"] == "CO1.PCONTR.CON_ADICION"].iloc[0]
    sin_adicion = df_limpio[df_limpio["id_contrato"] == "CO1.PCONTR.SIN_ADICION"].iloc[0]

    # Caso con adición
    assert con_adicion["cuantia_final"] == 62000000.0
    assert bool(con_adicion["tiene_adicion"]) is True
    assert bool(con_adicion["es_pyme"]) is True

    # Caso sin adición
    assert sin_adicion["cuantia_final"] == 30000000.0
    assert bool(sin_adicion["tiene_adicion"]) is False
    assert bool(sin_adicion["es_pyme"]) is False


def test_carga_lote_mongodb(pipeline: SecopETLPipeline):
    """
    PA-ALFA-002: Inserta un lote de prueba en MongoDB, lo recupera mediante
    MongoConnectionSingleton y valida los tipos BSON en el Esquema en Estrella.
    """
    id_test = "CO1.PCONTR.PRUEBA_UNITARIA_002"
    datos_prueba = pd.DataFrame([{
        "id_contrato": id_test,
        "codigo_proceso": "PROC-2022-VALLE-001",
        "cuantia_inicial": 85000000.0,
        "valor_adiciones": 15000000.0,
        "fecha_firma": "2022-07-20",
        "plazo_ejecucion_dias": 120,
        "departamento": "VALLE DEL CAUCA",
        "municipio": "TULUÁ",
        "modalidad": "Selección Abreviada",
        "tipo_contrato": "Obra",
        "estado": "Terminado",
        "codigo_unspsc": "72121100",
        "nombre_entidad": "ALCALDÍA MUNICIPAL DE TULUÁ",
        "nit_entidad": "891900424",
        "orden_entidad": "Territorial",
        "sector": "Desarrollo Institucional",
        "documento_proveedor": "900123456",
        "proveedor": "CONSTRUCTORA CENTRO VALLE S.A.S.",
        "es_pyme": "Si"
    }])

    df_extraido = pipeline.extraer_csv(datos_prueba)
    df_limpio, _, _ = pipeline.transformar_datos(df_extraido)
    docs = pipeline.estructurar_esquema_estrella(df_limpio)
    
    assert len(docs) == 1
    doc = docs[0]

    # Validar estructura y tipos antes de cargar
    assert doc["_id"] == id_test
    assert isinstance(doc["tiempo"]["fecha_firma"], datetime)
    assert isinstance(doc["cuantia_inicial"], float)
    assert doc["tiene_adicion"] is True

    # Cargar en MongoDB
    total_cargados = pipeline.cargar_en_mongodb(docs)
    assert total_cargados == 1

    # Recuperar desde la base de datos real
    col = MongoConnectionSingleton.get_collection("contratos")
    doc_recuperado = col.find_one({"_id": id_test})

    assert doc_recuperado is not None, "El documento debe existir en la colección 'contratos'"
    assert doc_recuperado["_id"] == id_test
    assert doc_recuperado["cuantia_final"] == 100000000.0
    assert doc_recuperado["geografia"]["municipio"] == "TULUÁ"
    assert doc_recuperado["geografia"]["departamento"] == "VALLE DEL CAUCA"
    assert doc_recuperado["entidad"]["nit"] == "891900424"
    assert doc_recuperado["proveedor"]["es_pyme"] is True

    # Limpieza del documento de prueba
    col.delete_one({"_id": id_test})
