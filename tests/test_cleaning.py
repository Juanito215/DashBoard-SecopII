"""
Suite de Pruebas Automatizadas de Calidad y Depuración de Datos
Historia de Usuario: HU-05 (Depuración de Inconsistencias, Duplicados y Nulos)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
import numpy as np
import pandas as pd
import pytest
from src.etl.cleaner import DataCleaner


def test_eliminacion_duplicados_por_id():
    """
    HU-05 / Criterio 1: Crea un DataFrame con IDs repetidos y comprueba
    que tras la deduplicación solo exista una fila conservando la primera ocurrencia.
    """
    datos = pd.DataFrame([
        {"id_contrato": "CO1.PCONTR.100", "cuantia_inicial": 1000000.0, "entidad": "Alcaldía A"},
        {"id_contrato": "CO1.PCONTR.100", "cuantia_inicial": 1000000.0, "entidad": "Alcaldía A Repetida 1"},
        {"id_contrato": "CO1.PCONTR.100", "cuantia_inicial": 1000000.0, "entidad": "Alcaldía A Repetida 2"},
        {"id_contrato": "CO1.PCONTR.200", "cuantia_inicial": 2000000.0, "entidad": "Gobernación B"},
        {"id_contrato": "CO1.PCONTR.300", "cuantia_inicial": 3000000.0, "entidad": "Hospital C"}
    ])

    df_dedup, dup_removidos = DataCleaner.eliminar_duplicados(datos, col_id="id_contrato")

    assert dup_removidos == 2, "Deben haberse identificado y removido exactamente 2 duplicados"
    assert len(df_dedup) == 3, "El DataFrame final debe contener 3 registros únicos"
    assert df_dedup["id_contrato"].tolist() == ["CO1.PCONTR.100", "CO1.PCONTR.200", "CO1.PCONTR.300"]
    # Comprobar que se preservó la primera ocurrencia
    assert df_dedup.iloc[0]["entidad"] == "Alcaldía A"


def test_descarte_cuantias_menores_o_iguales_a_cero():
    """
    HU-05 / Criterio 2: Introduce filas con valores <= 0, cadenas corruptas y nulos,
    validando que el resultado no contenga cuantías inválidas.
    """
    datos = pd.DataFrame([
        {"id_contrato": "C1", "cuantia_inicial": "$ 15.000.000,50"},  # Válida (15000000.5)
        {"id_contrato": "C2", "cuantia_inicial": "$ 0"},               # Inválida: igual a 0
        {"id_contrato": "C3", "cuantia_inicial": "-50000"},            # Inválida: negativa
        {"id_contrato": "C4", "cuantia_inicial": None},                # Inválida: nula
        {"id_contrato": "C5", "cuantia_inicial": "texto_corrupto"},    # Inválida: texto no numérico
        {"id_contrato": "C6", "cuantia_inicial": 2500000.0}            # Válida
    ])

    df_filtrado, descartados = DataCleaner.filtrar_cuantias_validas(datos, col_cuantia="cuantia_inicial")

    assert descartados == 4, "Debieron descartarse 4 registros con cuantías no válidas"
    assert len(df_filtrado) == 2, "Solo deben permanecer 2 registros con cuantía positiva"
    assert (df_filtrado["cuantia_inicial"] > 0).all(), "Todas las cuantías deben ser estrictamente > 0"
    assert df_filtrado["id_contrato"].tolist() == ["C1", "C6"]


def test_normalizacion_tipografica_y_espacios():
    """
    HU-05 / Criterio 3: Comprueba que textos con espacios desordenados o minúsculas
    se homogenicen a mayúsculas limpias y los nulos se imputen como 'NO REGISTRA'.
    """
    datos = pd.DataFrame([
        {
            "entidad": "  alcaldia  de  tulua  ",
            "departamento": "valle del cauca",
            "municipio": "  tuluá ",
            "modalidad": "contratacion directa",
            "observacion": "NULL"
        },
        {
            "entidad": "N/A",
            "departamento": "",
            "municipio": "NONE",
            "modalidad": "NAN",
            "observacion": "valida"
        }
    ])

    df_norm, celdas_imputadas = DataCleaner.normalizar_textos_y_nulos(datos)

    # Verificación de la fila 1
    assert df_norm.iloc[0]["entidad"] == "ALCALDIA DE TULUA"
    assert df_norm.iloc[0]["departamento"] == "VALLE DEL CAUCA"
    assert df_norm.iloc[0]["municipio"] == "TULUÁ"
    assert df_norm.iloc[0]["modalidad"] == "CONTRATACION DIRECTA"
    assert df_norm.iloc[0]["observacion"] == "NO REGISTRA"

    # Verificación de imputación de ausencias en la fila 2
    assert df_norm.iloc[1]["entidad"] == "NO REGISTRA"
    assert df_norm.iloc[1]["departamento"] == "NO REGISTRA"
    assert df_norm.iloc[1]["municipio"] == "NO REGISTRA"
    assert df_norm.iloc[1]["modalidad"] == "NO REGISTRA"
    assert df_norm.iloc[1]["observacion"] == "VALIDA"

    assert celdas_imputadas == 5, "Deben haberse imputado 5 celdas con patrones nulos"


def test_calculo_metricas_limpieza():
    """
    HU-05 / Criterio 4: Verifica la coherencia matemática del reporte cuantitativo
    de calidad: total_inicial == total_final + duplicados + descartados.
    """
    datos = pd.DataFrame([
        {"id_contrato": "A1", "cuantia_inicial": 100000.0, "entidad": "Entidad 1"},
        {"id_contrato": "A1", "cuantia_inicial": 100000.0, "entidad": "Entidad 1 Duplicada"},
        {"id_contrato": "A2", "cuantia_inicial": 0.0, "entidad": "Entidad 2 Cuantia Cero"},
        {"id_contrato": "A3", "cuantia_inicial": -50.0, "entidad": "Entidad 3 Cuantia Negativa"},
        {"id_contrato": "A4", "cuantia_inicial": 500000.0, "entidad": "  entidad   4  "},
        {"id_contrato": "A5", "cuantia_inicial": 800000.0, "entidad": "NULL"}
    ])

    df_limpio, metricas = DataCleaner.ejecutar_limpieza_completa(
        datos, col_id="id_contrato", col_cuantia="cuantia_inicial"
    )

    assert metricas["total_inicial"] == 6
    assert metricas["duplicados_eliminados"] == 1
    assert metricas["cuantias_invalidas_descartadas"] == 2
    assert metricas["total_final_limpio"] == 3
    assert metricas["celdas_imputadas"] >= 1
    assert metricas["tasa_retencion_pct"] == 50.0

    # Coherencia de flujo
    suma_balance = (
        metricas["total_final_limpio"]
        + metricas["duplicados_eliminados"]
        + metricas["cuantias_invalidas_descartadas"]
    )
    assert suma_balance == metricas["total_inicial"], "El balance de flujo de registros debe ser exacto"


def test_limpieza_sobre_dataset_real_10k():
    """
    HU-05: Valida la ejecución de DataCleaner sobre el archivo real de muestra 10k.
    Verifica que se detecten y descarten las 17 cuantías inválidas de la muestra.
    """
    from src.etl.etl_pipeline import SecopETLPipeline
    pipeline = SecopETLPipeline()

    df_extraido = pipeline.extraer_csv("data/raw/secop muestra 10k 2022.csv")
    df_limpio, metricas = DataCleaner.ejecutar_limpieza_completa(
        df_extraido, col_id="id_contrato", col_cuantia="cuantia_inicial"
    )

    assert metricas["total_inicial"] == 10000
    assert metricas["duplicados_eliminados"] == 0, "No hay duplicados en el id_contrato de la muestra 10k"
    assert metricas["cuantias_invalidas_descartadas"] == 17, "Debe descartar exactamente las 17 filas con cuantía <= 0"
    assert metricas["total_final_limpio"] == 9983
    assert metricas["tasa_retencion_pct"] == 99.83
    assert (df_limpio["cuantia_inicial"] > 0).all()
