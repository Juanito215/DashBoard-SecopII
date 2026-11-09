"""
Suite de Pruebas Automatizadas de Transformación Financiera y Cronológica
Historia de Usuario: HU-06 (Transformación de Formatos Financieros y Cronológicos)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
import numpy as np
import pandas as pd
import pytest
from src.etl.transformer import DataTransformer


def test_limpieza_monetaria_variantes():
    """
    HU-06 / Criterio 1: Valida que formatos con '$', comas, puntos y espacios
    se conviertan con exactitud a valores float64 en Pesos Colombianos (COP).
    """
    serie_cruda = pd.Series([
        "$ 120.000.000",
        "$45,500.50",
        " 3000000 ",
        "$ 0",
        "$ 150.000.000,00",
        "150,000,000",
        "150.000.000"
    ])

    serie_limpia = DataTransformer.limpiar_columna_monetaria(serie_cruda)

    assert serie_limpia.dtype == np.float64, "El tipo debe ser estrictamente float64"
    assert serie_limpia.iloc[0] == 120000000.0
    assert serie_limpia.iloc[1] == 45500.50
    assert serie_limpia.iloc[2] == 3000000.0
    assert serie_limpia.iloc[3] == 0.0
    assert serie_limpia.iloc[4] == 150000000.0
    assert serie_limpia.iloc[5] == 150000000.0
    assert serie_limpia.iloc[6] == 150000000.0


def test_extraccion_anio_mes_trimestre():
    """
    HU-06 / Criterio 2: Comprueba que fechas heterogéneas se conviertan a ISODate
    y se extraigan anio_vigencia, mes_vigencia y trimestre como enteros.
    """
    datos = pd.DataFrame([
        {"fecha_firma": "2022-05-18"},
        {"fecha_firma": "18/05/2022"},
        {"fecha_firma": "2022-01-05"},
        {"fecha_firma": "2022-10-31"},
        {"fecha_firma": "invalida_o_nula"}
    ])

    df_trans = DataTransformer.parsear_fechas_y_derivar_tiempo(datos, col_fecha="fecha_firma")

    assert pd.api.types.is_datetime64_any_dtype(df_trans["fecha_firma"]), "Debe ser tipo datetime64"
    assert df_trans["anio_vigencia"].dtype in [np.int32, np.int64, int]
    assert df_trans["mes_vigencia"].dtype in [np.int32, np.int64, int]
    assert df_trans["trimestre"].dtype in [np.int32, np.int64, int]

    # Fila 0 (2022-05-18 -> Q2)
    assert df_trans.iloc[0]["anio_vigencia"] == 2022
    assert df_trans.iloc[0]["mes_vigencia"] == 5
    assert df_trans.iloc[0]["trimestre"] == 2

    # Fila 1 (18/05/2022 -> Q2)
    assert df_trans.iloc[1]["anio_vigencia"] == 2022
    assert df_trans.iloc[1]["mes_vigencia"] == 5
    assert df_trans.iloc[1]["trimestre"] == 2

    # Fila 2 (Enero -> Q1)
    assert df_trans.iloc[2]["mes_vigencia"] == 1
    assert df_trans.iloc[2]["trimestre"] == 1

    # Fila 3 (Octubre -> Q4)
    assert df_trans.iloc[3]["mes_vigencia"] == 10
    assert df_trans.iloc[3]["trimestre"] == 4

    # Fila 4 (Fecha nula o corrupta -> Imputada con fecha semilla 2022-01-01)
    assert df_trans.iloc[4]["anio_vigencia"] == 2022
    assert df_trans.iloc[4]["mes_vigencia"] == 1
    assert df_trans.iloc[4]["trimestre"] == 1


def test_calculo_cuantia_final_y_tiene_adicion():
    """
    HU-06 / Criterio 3: Valida cuantia_final = cuantia_inicial + valor_adiciones
    y que tiene_adicion sea booleano estricto según valor_adiciones > 0.
    """
    datos = pd.DataFrame([
        {"cuantia_inicial": "$ 80.000.000", "valor_adiciones": "$ 20.000.000"},
        {"cuantia_inicial": "50000000", "valor_adiciones": "0"},
        {"cuantia_inicial": 10000000.0, "valor_adiciones": 0.0}
    ])

    df_calc = DataTransformer.calcular_variables_financieras(datos)

    assert df_calc.iloc[0]["cuantia_final"] == 100000000.0
    assert bool(df_calc.iloc[0]["tiene_adicion"]) is True

    assert df_calc.iloc[1]["cuantia_final"] == 50000000.0
    assert bool(df_calc.iloc[1]["tiene_adicion"]) is False

    assert df_calc.iloc[2]["cuantia_final"] == 10000000.0
    assert bool(df_calc.iloc[2]["tiene_adicion"]) is False


def test_no_retencion_de_tipos_object():
    """
    HU-06 / Criterio 1 y 2: Asegura que tras la transformación ninguna columna
    monetaria ni cronológica permanezca con tipo 'object' (cadena de texto).
    """
    datos = pd.DataFrame([
        {"id_contrato": "C1", "cuantia_inicial": "$ 100.000", "valor_adiciones": "$ 50.000", "fecha_firma": "2022-03-01"},
        {"id_contrato": "C2", "cuantia_inicial": "$ 200.000", "valor_adiciones": "$ 0", "fecha_firma": "2022-04-01"}
    ])

    df_trans, metricas = DataTransformer.transformar_lote_completo(datos, col_fecha="fecha_firma")

    # Columnas monetarias no deben ser object
    for col in ["cuantia_inicial", "valor_adiciones", "cuantia_final"]:
        assert df_trans[col].dtype == np.float64, f"Columna {col} no debe ser de tipo object"

    # Columna de fecha no debe ser object
    assert pd.api.types.is_datetime64_any_dtype(df_trans["fecha_firma"])

    # Columnas temporales derivadas
    for col in ["anio_vigencia", "mes_vigencia", "trimestre"]:
        assert df_trans[col].dtype in [np.int32, np.int64, int]

    assert metricas["total_con_adicion"] == 1
    assert metricas["pct_con_adicion"] == 50.0
    assert metricas["anios_detectados"] == [2022]


def test_transformacion_sobre_dataset_real_10k():
    """
    HU-06: Valida la ejecución sobre el dataset de muestra 10k real de SECOP II.
    """
    from src.etl.etl_pipeline import SecopETLPipeline
    pipeline = SecopETLPipeline()

    df_extraido = pipeline.extraer_csv("data/raw/secop muestra 10k 2022.csv")
    df_trans, metricas = DataTransformer.transformar_lote_completo(df_extraido, col_fecha="fecha_firma")

    assert len(df_trans) == 10000
    assert df_trans["cuantia_inicial"].dtype == np.float64
    assert df_trans["cuantia_final"].dtype == np.float64
    assert pd.api.types.is_datetime64_any_dtype(df_trans["fecha_firma"])
    assert metricas["anios_detectados"] == [2022]
    assert metricas["dtypes_monetarios"] == "float64"
