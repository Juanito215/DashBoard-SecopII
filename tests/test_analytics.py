"""
Suite de Pruebas Automatizadas de Analítica Descriptiva y Agregación Financiera
Historia de Usuario: HU-19 (Tarjetas KPI de Volumen y Presupuesto Global)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.controllers.analytics_controller import AnalyticsController
from src.database.connection import MongoConnectionSingleton
from src.database.data_repository import DataRepositorySingleton
from src.queries.query_builder import ConsultaSecopBuilder


@pytest.fixture
def sample_kpi_dataframe() -> pd.DataFrame:
    """Fixture con contratos de prueba con cuantías monetarias controladas."""
    data = {
        "id_contrato": ["CTR-001", "CTR-002", "CTR-003", "CTR-004", "CTR-005"],
        "cuantia_inicial": [100_000_000.0, 250_000_000.0, 50_000_000.0, 400_000_000.0, 200_000_000.0],
        "valor_adiciones": [20_000_000.0, 0.0, 10_000_000.0, 50_000_000.0, 0.0],
        "cuantia_final": [120_000_000.0, 250_000_000.0, 60_000_000.0, 450_000_000.0, 200_000_000.0],
        "departamento": ["ANTIOQUIA", "VALLE DEL CAUCA", "ANTIOQUIA", "BOGOTA", "SANTANDER"],
        "modalidad": [
            "CONTRATACIÓN DIRECTA",
            "SELECCIÓN ABREVIADA",
            "CONTRATACIÓN DIRECTA",
            "LICITACIÓN PÚBLICA",
            "MÍNIMA CUANTÍA"
        ],
        "anio_vigencia": [2022, 2022, 2023, 2023, 2024],
        "mes_vigencia": [1, 2, 1, 5, 12],
        "entidad": [
            "ALCALDÍA DE MEDELLÍN",
            "GOBERNACIÓN DEL VALLE DEL CAUCA",
            "ALCALDÍA DE MEDELLÍN",
            "INSTITUTO DE DESARROLLO URBANO - IDU BOGOTÁ",
            "SECRETARÍA DE SALUD DE SANTANDER"
        ],
        "estado": [
            "MODIFICADO",
            "EN EJECUCIÓN",
            "MODIFICADO",
            "CELEBRADO",
            "TERMINADO"
        ],
    }
    return pd.DataFrame(data)


def test_formatear_cop_valores_especiales():
    """
    HU-19: Valida que valores nulos, cero o NaN retornen '$ 0 COP'.
    """
    assert AnalyticsController.formatear_cop(0) == "$ 0 COP"
    assert AnalyticsController.formatear_cop(0.0) == "$ 0 COP"
    assert AnalyticsController.formatear_cop(np.nan) == "$ 0 COP"
    assert AnalyticsController.formatear_cop(None) == "$ 0 COP"


def test_formatear_cop_exacto_y_compacto():
    """
    HU-19: Valida el formateo monetario en Pesos Colombianos estándar y abreviado.
    """
    # Formato completo en COP
    assert AnalyticsController.formatear_cop(500_000.0, compacto=False) == "$ 500,000 COP"
    assert AnalyticsController.formatear_cop(1_500_000.0, compacto=False) == "$ 1,500,000 COP"

    # Formato compacto (M, Mil M, Billones)
    assert AnalyticsController.formatear_cop(25_000_000.0, compacto=True) == "$ 25.0 M"
    assert AnalyticsController.formatear_cop(4_500_000_000.0, compacto=True) == "$ 4.50 Mil M"
    assert AnalyticsController.formatear_cop(2_100_000_000_000.0, compacto=True) == "$ 2.10 Billones"


def test_calcular_kpis_volumen_presupuesto_dataframe_valido(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-19 / Criterio 2: Valida el cálculo de los 4 indicadores KPI sobre datos válidos:
    1. Total de contratos celebrados
    2. Cuantía inicial total adjudicada
    3. Valor total de adiciones presupuestales
    4. Presupuesto total consolidado (cuantía final)
    """
    kpis = AnalyticsController.calcular_kpis_volumen_presupuesto(sample_kpi_dataframe)

    assert kpis["total_contratos"] == 5
    assert kpis["cuantia_inicial_total"] == 1_000_000_000.0
    assert kpis["valor_adiciones_total"] == 80_000_000.0
    assert kpis["cuantia_final_total"] == 1_080_000_000.0

    # Comprobación de formato
    assert "COP" in kpis["cuantia_inicial_exacta"]
    assert "COP" in kpis["cuantia_final_exacta"]
    assert "$ 1.00 Mil M" == kpis["cuantia_inicial_fmt"]
    assert "$ 80.0 M" == kpis["valor_adiciones_fmt"]
    assert "$ 1.08 Mil M" == kpis["cuantia_final_fmt"]


def test_calcular_kpis_volumen_presupuesto_dataframe_vacio_o_none():
    """
    HU-19: Valida que DataFrames vacíos o None se procesen de forma segura sin excepciones.
    """
    kpis_vacio = AnalyticsController.calcular_kpis_volumen_presupuesto(pd.DataFrame())
    assert kpis_vacio["total_contratos"] == 0
    assert kpis_vacio["cuantia_inicial_total"] == 0.0
    assert kpis_vacio["cuantia_final_total"] == 0.0
    assert kpis_vacio["cuantia_inicial_fmt"] == "$ 0 COP"

    kpis_none = AnalyticsController.calcular_kpis_volumen_presupuesto(None)
    assert kpis_none["total_contratos"] == 0
    assert kpis_none["cuantia_final_total"] == 0.0


def test_paridad_matematica_pandas_vs_mongodb_aggregation():
    """
    HU-19 / Criterio 1: Garantiza paridad matemática entre el cálculo vectorizado en Pandas
    y la agregación de MongoDB ($match -> $group con $sum y $count).
    """
    col = MongoConnectionSingleton.get_collection("contratos")
    if col.count_documents({}) > 0:
        docs = list(col.find({}, {"cuantia_inicial": 1, "valor_adiciones": 1, "cuantia_final": 1}))
        df_mongo = pd.DataFrame(docs)

        # Cálculo con Pandas
        kpis_pandas = AnalyticsController.calcular_kpis_volumen_presupuesto(df_mongo)

        # Cálculo con MongoDB
        kpis_mongo = AnalyticsController.agregar_volumen_presupuesto_mongo()

        assert kpis_mongo["total_contratos"] == kpis_pandas["total_contratos"]
        assert pytest.approx(kpis_mongo["cuantia_inicial_total"], rel=1e-5) == kpis_pandas["cuantia_inicial_total"]
        assert pytest.approx(kpis_mongo["valor_adiciones_total"], rel=1e-5) == kpis_pandas["valor_adiciones_total"]
        assert pytest.approx(kpis_mongo["cuantia_final_total"], rel=1e-5) == kpis_pandas["cuantia_final_total"]


def test_calcular_kpis_reactivo_con_query_builder(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-19: Valida el cálculo de KPIs sobre un subconjunto filtrado reactivamente con ConsultaSecopBuilder.
    """
    builder = ConsultaSecopBuilder(sample_kpi_dataframe)
    df_filtrado, _, _ = builder.filtrar_departamento(["ANTIOQUIA"]).build()

    kpis = AnalyticsController.calcular_kpis_volumen_presupuesto(df_filtrado)

    assert kpis["total_contratos"] == 2
    assert kpis["cuantia_inicial_total"] == 150_000_000.0  # 100M + 50M
    assert kpis["valor_adiciones_total"] == 30_000_000.0   # 20M + 10M
    assert kpis["cuantia_final_total"] == 180_000_000.0     # 120M + 60M


def test_apptest_dashboard_kpis_volumen_ui():
    """
    HU-19 / Criterio 2 y 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Comprobar que en el Dashboard General se rendericen las 4 tarjetas KPI
       con títulos ejecutivos y sin excepciones.
    """
    from streamlit.testing.v1 import AppTest

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Comprobar que el HTML renderizado incluya las 4 tarjetas KPI de volumen
    html_dashboard = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Total de Contratos Celebrados" in html_dashboard
    assert "Cuantía Inicial Adjudicada" in html_dashboard
    assert "Adiciones Presupuestales" in html_dashboard
    assert "Presupuesto Total Consolidado" in html_dashboard


# ==============================================================================
# PRUEBAS AUTOMATIZADAS HU-20: SOBRECOSTOS Y ADICIONES PRESUPUESTALES
# ==============================================================================

def test_calcular_kpis_sobrecostos_adiciones_dataframe_valido(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-20 / Criterio 1: Valida el cálculo de los 4 indicadores de sobrecostos y adiciones:
    1. Monto total de adiciones presupuestales
    2. Porcentaje y conteo de contratos adicionados
    3. Incremento promedio sobre cuantía inicial (%)
    4. Valor promedio por adición (COP)
    """
    kpis = AnalyticsController.calcular_kpis_sobrecostos_adiciones(sample_kpi_dataframe)

    assert kpis["total_contratos"] == 5
    assert kpis["contratos_con_adicion"] == 3
    assert kpis["monto_adiciones_total"] == 80_000_000.0
    assert kpis["porcentaje_contratos_adicionados"] == 60.0
    assert kpis["porcentaje_adicionados_fmt"] == "60.0%"
    assert pytest.approx(kpis["incremento_promedio_pct"], rel=1e-2) == 17.5
    assert kpis["incremento_promedio_fmt"] == "+17.5%"
    assert pytest.approx(kpis["adicion_promedio_cop"], rel=1e-2) == 26_666_666.67
    assert "$ 80.0 M" in kpis["monto_adiciones_fmt"]


def test_calcular_kpis_sobrecostos_adiciones_sin_adiciones():
    """
    HU-20: Valida que un conjunto de datos sin ninguna adición retorne ceros
    sin arrojar errores de división por cero (ZeroDivisionError o NaN).
    """
    datos_sin_adicion = pd.DataFrame({
        "id_contrato": ["C1", "C2", "C3"],
        "cuantia_inicial": [100.0, 200.0, 300.0],
        "valor_adiciones": [0.0, 0.0, 0.0],
        "tiene_adicion": [False, False, False]
    })
    kpis = AnalyticsController.calcular_kpis_sobrecostos_adiciones(datos_sin_adicion)

    assert kpis["total_contratos"] == 3
    assert kpis["contratos_con_adicion"] == 0
    assert kpis["monto_adiciones_total"] == 0.0
    assert kpis["porcentaje_contratos_adicionados"] == 0.0
    assert kpis["incremento_promedio_pct"] == 0.0
    assert kpis["adicion_promedio_cop"] == 0.0


def test_calcular_kpis_sobrecostos_adiciones_vacio_o_none():
    """
    HU-20: Valida resiliencia ante DataFrames vacíos o None.
    """
    kpis_vacio = AnalyticsController.calcular_kpis_sobrecostos_adiciones(pd.DataFrame())
    assert kpis_vacio["total_contratos"] == 0
    assert kpis_vacio["contratos_con_adicion"] == 0
    assert kpis_vacio["monto_adiciones_total"] == 0.0
    assert kpis_vacio["porcentaje_contratos_adicionados"] == 0.0

    kpis_none = AnalyticsController.calcular_kpis_sobrecostos_adiciones(None)
    assert kpis_none["total_contratos"] == 0
    assert kpis_none["monto_adiciones_total"] == 0.0


def test_agregar_sobrecostos_mongo_paridad():
    """
    HU-20 / Criterio 2: Certifica paridad matemática exacta entre el cálculo
    en memoria con Pandas y el Aggregation Pipeline de MongoDB ($cond y $group).
    """
    col = MongoConnectionSingleton.get_collection("contratos")
    if col.count_documents({}) > 0:
        docs = list(col.find({}, {"cuantia_inicial": 1, "valor_adiciones": 1, "tiene_adicion": 1}))
        df_mongo = pd.DataFrame(docs)

        # Cálculo en Pandas
        kpis_pandas = AnalyticsController.calcular_kpis_sobrecostos_adiciones(df_mongo)

        # Cálculo en MongoDB
        kpis_mongo = AnalyticsController.agregar_sobrecostos_mongo()

        assert kpis_mongo["total_contratos"] == kpis_pandas["total_contratos"]
        assert kpis_mongo["contratos_con_adicion"] == kpis_pandas["contratos_con_adicion"]
        assert pytest.approx(kpis_mongo["monto_adiciones_total"], rel=1e-3) == kpis_pandas["monto_adiciones_total"]
        assert pytest.approx(kpis_mongo["porcentaje_contratos_adicionados"], rel=1e-2) == kpis_pandas["porcentaje_contratos_adicionados"]


def test_apptest_analytics_kpis_sobrecostos_ui():
    """
    HU-20 / Criterio 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a la pestaña 'Analítica y Tendencias'
    3. Comprobar que se rendericen las 4 tarjetas KPI de sobrecostos y adiciones presupuestales:
       - 'Monto Total de Adiciones'
       - 'Contratos Adicionados'
       - 'Incremento Promedio'
       - 'Valor Promedio por Adición'
    """
    from streamlit.testing.v1 import AppTest

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar a Analítica y Tendencias
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Analítica y Tendencias").run()

    assert len(at.exception) == 0

    # Comprobar tarjetas KPI en la vista de analítica
    html_analytics = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Monto Total de Adiciones" in html_analytics
    assert "Contratos Adicionados" in html_analytics
    assert "Incremento Promedio" in html_analytics
    assert "Valor Promedio por Adición" in html_analytics


# ==============================================================================
# PRUEBAS AUTOMATIZADAS HU-21: CUANTÍA PROMEDIO Y MEDIANA CONTRACTUAL
# ==============================================================================

def test_calcular_kpis_promedio_mediana_dataframe_valido(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-21 / Criterio 1: Valida el cálculo de tendencia central y dispersión:
    1. Cuantía promedio por contrato (Media aritmética)
    2. Mediana contractual (Percentil 50 representativo)
    3. Ratio de distorsión / asimetría (Media / Mediana)
    4. Mayor cuantía adjudicada (Megaproyecto techo)
    5. Rango intercuartílico (IQR = Q75 - Q25)
    """
    kpis = AnalyticsController.calcular_kpis_promedio_mediana(sample_kpi_dataframe)

    # Valores esperados para [120M, 250M, 60M, 450M, 200M]:
    # Media: 216.0 M
    # Mediana: 200.0 M
    # Max: 450.0 M
    # Q25: 120.0 M, Q75: 250.0 M -> IQR: 130.0 M
    # Ratio: 216 / 200 = 1.08 -> 1.1x -> "Distribución equilibrada"
    assert pytest.approx(kpis["cuantia_promedio"], rel=1e-3) == 216_000_000.0
    assert pytest.approx(kpis["cuantia_mediana"], rel=1e-3) == 200_000_000.0
    assert pytest.approx(kpis["cuantia_maxima"], rel=1e-3) == 450_000_000.0
    assert pytest.approx(kpis["iqr_cop"], rel=1e-3) == 130_000_000.0
    assert pytest.approx(kpis["ratio_distorsion"], rel=1e-2) == 1.08
    assert kpis["ratio_distorsion_fmt"] == "1.1x"
    assert kpis["nivel_sesgo"] == "Distribución equilibrada"

    assert "$ 216.0 M" in kpis["cuantia_promedio_fmt"]
    assert "$ 200.0 M" in kpis["cuantia_mediana_fmt"]
    assert "$ 450.0 M" in kpis["cuantia_maxima_fmt"]
    assert "$ 130.0 M" in kpis["iqr_fmt"]


def test_calcular_kpis_promedio_mediana_sesgo_labels():
    """
    HU-21 / Criterio 1: Valida la clasificación cualitativa de sesgo y asimetría:
    - ratio >= 3.0: 'Alta distorsión por atípicos'
    - ratio >= 1.5: 'Sesgo moderado a la derecha'
    - ratio < 1.5: 'Distribución equilibrada'
    - sin datos o 0: 'Sin datos'
    """
    # 1. Alta distorsión por megaproyecto atípico
    df_alto_sesgo = pd.DataFrame({
        "cuantia_final": [10_000_000.0, 10_000_000.0, 10_000_000.0, 10_000_000.0, 1_000_000_000.0]
    })
    kpis_alto = AnalyticsController.calcular_kpis_promedio_mediana(df_alto_sesgo)
    assert kpis_alto["ratio_distorsion"] >= 3.0
    assert kpis_alto["nivel_sesgo"] == "Alta distorsión por atípicos"

    # 2. Sesgo moderado a la derecha
    df_moderado = pd.DataFrame({
        "cuantia_final": [10_000_000.0, 10_000_000.0, 10_000_000.0, 20_000_000.0, 50_000_000.0]
    })
    kpis_mod = AnalyticsController.calcular_kpis_promedio_mediana(df_moderado)
    assert 1.5 <= kpis_mod["ratio_distorsion"] < 3.0
    assert kpis_mod["nivel_sesgo"] == "Sesgo moderado a la derecha"

    # 3. Distribución equilibrada
    df_equilibrado = pd.DataFrame({
        "cuantia_final": [10_000_000.0, 11_000_000.0, 12_000_000.0, 13_000_000.0, 14_000_000.0]
    })
    kpis_eq = AnalyticsController.calcular_kpis_promedio_mediana(df_equilibrado)
    assert kpis_eq["ratio_distorsion"] < 1.5
    assert kpis_eq["nivel_sesgo"] == "Distribución equilibrada"


def test_calcular_kpis_promedio_mediana_vacio_o_none():
    """
    HU-21: Valida que DataFrames vacíos o None se procesen con tolerancia total
    a fallos retornando valores cero sin arrojar excepciones.
    """
    kpis_vacio = AnalyticsController.calcular_kpis_promedio_mediana(pd.DataFrame())
    assert kpis_vacio["cuantia_promedio"] == 0.0
    assert kpis_vacio["cuantia_mediana"] == 0.0
    assert kpis_vacio["ratio_distorsion"] == 0.0
    assert kpis_vacio["ratio_distorsion_fmt"] == "0.0x"
    assert kpis_vacio["nivel_sesgo"] == "Sin datos"
    assert kpis_vacio["cuantia_promedio_fmt"] == "$ 0 COP"

    kpis_none = AnalyticsController.calcular_kpis_promedio_mediana(None)
    assert kpis_none["cuantia_promedio"] == 0.0
    assert kpis_none["cuantia_mediana"] == 0.0
    assert kpis_none["nivel_sesgo"] == "Sin datos"

    # DataFrame con ceros exclusivamente (sin división por cero)
    df_ceros = pd.DataFrame({"cuantia_final": [0.0, 0.0, 0.0]})
    kpis_ceros = AnalyticsController.calcular_kpis_promedio_mediana(df_ceros)
    assert kpis_ceros["cuantia_promedio"] == 0.0
    assert kpis_ceros["cuantia_mediana"] == 0.0
    assert kpis_ceros["ratio_distorsion"] == 0.0
    assert kpis_ceros["nivel_sesgo"] == "Sin datos"


def test_agregar_tendencia_central_mongo_paridad():
    """
    HU-21 / Criterio 2: Certifica paridad matemática entre el cálculo en memoria
    con Pandas y la agregación en MongoDB ($group, $avg, $max y cálculo de mediana).
    """
    col = MongoConnectionSingleton.get_collection("contratos")
    if col.count_documents({}) > 0:
        docs = list(col.find({}, {"cuantia_final": 1}))
        df_mongo = pd.DataFrame(docs)

        # Cálculo en Pandas
        kpis_pandas = AnalyticsController.calcular_kpis_promedio_mediana(df_mongo)

        # Agregación en MongoDB
        kpis_mongo = AnalyticsController.agregar_tendencia_central_mongo()

        assert pytest.approx(kpis_mongo["cuantia_promedio"], rel=1e-3) == kpis_pandas["cuantia_promedio"]
        assert pytest.approx(kpis_mongo["cuantia_maxima"], rel=1e-3) == kpis_pandas["cuantia_maxima"]
        assert pytest.approx(kpis_mongo["cuantia_mediana"], rel=1e-1) == kpis_pandas["cuantia_mediana"]

    # Consulta que no arroja resultados
    res_vacio = AnalyticsController.agregar_tendencia_central_mongo({"departamento": "DEPARTAMENTO_INEXISTENTE_XYZ"})
    assert res_vacio["cuantia_promedio"] == 0.0
    assert res_vacio["cuantia_mediana"] == 0.0
    assert res_vacio["cuantia_maxima"] == 0.0


def test_calcular_kpis_promedio_mediana_reactivo_con_query_builder(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-21: Valida el cálculo de tendencia central sobre subconjuntos filtrados reactivamente.
    """
    builder = ConsultaSecopBuilder(sample_kpi_dataframe)
    df_antioquia, _, _ = builder.filtrar_departamento(["ANTIOQUIA"]).build()

    # Antioquia tiene 2 contratos: 120M y 60M
    kpis = AnalyticsController.calcular_kpis_promedio_mediana(df_antioquia)

    assert pytest.approx(kpis["cuantia_promedio"], rel=1e-3) == 90_000_000.0
    assert pytest.approx(kpis["cuantia_mediana"], rel=1e-3) == 90_000_000.0
    assert pytest.approx(kpis["cuantia_maxima"], rel=1e-3) == 120_000_000.0
    assert pytest.approx(kpis["ratio_distorsion"], rel=1e-3) == 1.0


def test_apptest_analytics_kpis_tendencia_central_ui():
    """
    HU-21 / Criterio 3: Prueba de integración visual con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a 'Analítica y Tendencias'
    3. Comprobar que se rendericen las 4 tarjetas KPI de tendencia central y dispersión:
       - 'Cuantía Promedio'
       - 'Mediana Contractual'
       - 'Ratio de Distorsión'
       - 'Mayor Cuantía Adjudicada'
    """
    from streamlit.testing.v1 import AppTest

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar a Analítica y Tendencias
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Analítica y Tendencias").run()

    assert len(at.exception) == 0

    # Comprobar tarjetas KPI en la vista de analítica
    html_analytics = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Cuantía Promedio" in html_analytics
    assert "Mediana Contractual" in html_analytics
    assert "Ratio de Distorsión" in html_analytics
    assert "Mayor Cuantía Adjudicada" in html_analytics


# ==============================================================================
# PRUEBAS AUTOMATIZADAS HU-22: GRÁFICA DESCRIPTIVA 1 - GASTO POR MODALIDAD
# ==============================================================================

def test_obtener_gasto_por_modalidad_dataframe_valido(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-22 / Criterio 1: Valida la agregación por modalidad de contratación:
    - Agrupación por modalidad
    - Cálculo de monto_total acumulado
    - Conteo de cantidad_contratos
    - Porcentaje de participación respecto al total
    - Ordenamiento descendente por cuantía acumulada
    """
    df_mod = AnalyticsController.obtener_gasto_por_modalidad(sample_kpi_dataframe)

    assert not df_mod.empty
    assert list(df_mod.columns) == ["modalidad", "monto_total", "cantidad_contratos", "participacion_pct", "monto_fmt"]

    # 4 modalidades únicas esperadas
    assert len(df_mod) == 4

    # Ordenamiento descendente por monto_total
    assert df_mod["monto_total"].is_monotonic_decreasing

    # Modalidad líder en monto: LICITACIÓN PÚBLICA (450M)
    lider = df_mod.iloc[0]
    assert lider["modalidad"] == "LICITACIÓN PÚBLICA"
    assert pytest.approx(lider["monto_total"], rel=1e-3) == 450_000_000.0
    assert lider["cantidad_contratos"] == 1
    assert pytest.approx(lider["participacion_pct"], rel=1e-2) == 41.67
    assert "$ 450.0 M" in lider["monto_fmt"]

    # Contratación Directa: 2 contratos (120M + 60M = 180M)
    directa = df_mod[df_mod["modalidad"] == "CONTRATACIÓN DIRECTA"].iloc[0]
    assert pytest.approx(directa["monto_total"], rel=1e-3) == 180_000_000.0
    assert directa["cantidad_contratos"] == 2
    assert pytest.approx(directa["participacion_pct"], rel=1e-2) == 16.67

    # Suma de participaciones debe ser aproximadamente 100%
    assert pytest.approx(df_mod["participacion_pct"].sum(), rel=1e-3) == 100.0


def test_obtener_gasto_por_modalidad_vacio_o_none():
    """
    HU-22: Valida resiliencia ante DataFrames vacíos o None retornando
    un DataFrame vacío con las columnas estructuradas esperadas.
    """
    columnas_esperadas = ["modalidad", "monto_total", "cantidad_contratos", "participacion_pct", "monto_fmt"]

    df_none = AnalyticsController.obtener_gasto_por_modalidad(None)
    assert isinstance(df_none, pd.DataFrame)
    assert df_none.empty
    assert list(df_none.columns) == columnas_esperadas

    df_vacio = AnalyticsController.obtener_gasto_por_modalidad(pd.DataFrame())
    assert isinstance(df_vacio, pd.DataFrame)
    assert df_vacio.empty
    assert list(df_vacio.columns) == columnas_esperadas

    # DataFrame con columnas pero sin registros
    df_cols_vacio = pd.DataFrame(columns=["modalidad", "cuantia_final"])
    df_res = AnalyticsController.obtener_gasto_por_modalidad(df_cols_vacio)
    assert df_res.empty
    assert list(df_res.columns) == columnas_esperadas


def test_generar_grafica_gasto_modalidad_figura_valida(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-22 / Criterio 2: Valida la construcción de la figura Plotly:
    - Retorna instancia de go.Figure
    - Tipo de traza de barras horizontales (orientation='h')
    - Coloración diferenciada para Contratación Directa (#4F46E5)
    - Título y etiquetas de ejes configuradas
    """
    import plotly.graph_objects as go

    fig = AnalyticsController.generar_grafica_gasto_modalidad(sample_kpi_dataframe)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0

    traza = fig.data[0]
    assert traza.type == "bar"
    assert traza.orientation == "h"

    # Verificar que el color índigo corporativo (#4F46E5) está asignado a CONTRATACIÓN DIRECTA
    colores_asignados = list(traza.marker.color)
    assert "#4F46E5" in colores_asignados
    assert "#93C5FD" in colores_asignados

    # Verificar hovertemplate y formato
    assert "Cuantía Acumulada" in traza.hovertemplate
    assert "Participación del Gasto" in traza.hovertemplate


def test_generar_grafica_gasto_modalidad_figura_vacia():
    """
    HU-22: Valida que ante datos vacíos se genere una figura informativa
    con anotación sin lanzar errores en la interfaz.
    """
    import plotly.graph_objects as go

    fig_vacia = AnalyticsController.generar_grafica_gasto_modalidad(pd.DataFrame())
    assert isinstance(fig_vacia, go.Figure)
    assert len(fig_vacia.layout.annotations) > 0
    assert "Sin registros disponibles" in fig_vacia.layout.annotations[0].text


def test_agregar_gasto_modalidad_mongo_paridad():
    """
    HU-22 / Criterio 3: Certifica paridad matemática entre el cálculo en memoria
    con Pandas y el Aggregation Pipeline de MongoDB ($group por clasificacion.modalidad y $sort).
    """
    col = MongoConnectionSingleton.get_collection("contratos")
    if col.count_documents({}) > 0:
        docs = list(col.find({}, {"clasificacion.modalidad": 1, "cuantia_final": 1}))
        registros_limpios = []
        for d in docs:
            mod = d.get("clasificacion", {}).get("modalidad") if isinstance(d.get("clasificacion"), dict) else None
            registros_limpios.append({
                "modalidad": mod or "NO REGISTRA",
                "cuantia_final": d.get("cuantia_final", 0.0)
            })
        df_mongo = pd.DataFrame(registros_limpios)

        # Agregación en Pandas
        df_mod_pandas = AnalyticsController.obtener_gasto_por_modalidad(df_mongo)

        # Agregación en MongoDB
        lista_mongo = AnalyticsController.agregar_gasto_modalidad_mongo()

        assert len(lista_mongo) > 0
        total_mongo = sum(item["monto_total"] for item in lista_mongo)
        total_pandas = df_mod_pandas["monto_total"].sum()
        assert pytest.approx(total_mongo, rel=1e-3) == total_pandas

        # Verificar ordenamiento descendente en MongoDB
        montos_mongo = [item["monto_total"] for item in lista_mongo]
        assert montos_mongo == sorted(montos_mongo, reverse=True)


def test_obtener_gasto_modalidad_reactivo_con_query_builder(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-22: Valida la reactividad de la agregación por modalidad cuando
    el conjunto es filtrado previamente mediante ConsultaSecopBuilder.
    """
    builder = ConsultaSecopBuilder(sample_kpi_dataframe)
    df_antioquia, _, _ = builder.filtrar_departamento(["ANTIOQUIA"]).build()

    # En Antioquia solo hay CONTRATACIÓN DIRECTA (120M + 60M = 180M)
    df_mod_ant = AnalyticsController.obtener_gasto_por_modalidad(df_antioquia)

    assert len(df_mod_ant) == 1
    assert df_mod_ant.iloc[0]["modalidad"] == "CONTRATACIÓN DIRECTA"
    assert pytest.approx(df_mod_ant.iloc[0]["monto_total"], rel=1e-3) == 180_000_000.0
    assert df_mod_ant.iloc[0]["cantidad_contratos"] == 2
    assert pytest.approx(df_mod_ant.iloc[0]["participacion_pct"], rel=1e-3) == 100.0


def test_apptest_analytics_grafica_modalidad_ui():
    """
    HU-22 / Criterio 2 y 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a 'Analítica y Tendencias'
    3. Comprobar que se renderice el contenedor de la gráfica de modalidad
       sin excepciones ni errores visuales.
    """
    from streamlit.testing.v1 import AppTest

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar a Analítica y Tendencias
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Analítica y Tendencias").run()

    assert len(at.exception) == 0

    # Comprobar contenedor de la gráfica de modalidad
    html_analytics = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Distribución del Gasto por Modalidad de Selección" in html_analytics
    assert "Auditoría de Concentración Presupuestal" in html_analytics


# ==============================================================================
# PRUEBAS AUTOMATIZADAS HU-23: GRÁFICA DESCRIPTIVA 2 - SERIE TEMPORAL 2021-2026
# ==============================================================================

def test_obtener_serie_temporal_gasto_mensual_dataframe_valido(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-23 / Criterio 1: Valida la agregación mensual cronológica:
    - Agrupación por anio_vigencia y mes_vigencia
    - Formato de periodo 'AAAA-MM'
    - Cálculo de cuantia_total, adiciones_total y cantidad_contratos
    - Ordenamiento estrictamente ascendente en el tiempo
    """
    df_ts = AnalyticsController.obtener_serie_temporal_gasto(sample_kpi_dataframe, granularidad="Mensual")

    columnas_esperadas = ["periodo", "anio_vigencia", "mes_vigencia", "cuantia_total", "adiciones_total", "cantidad_contratos", "monto_fmt"]
    assert list(df_ts.columns) == columnas_esperadas
    assert len(df_ts) == 5

    periodos = list(df_ts["periodo"])
    assert periodos == ["2022-01", "2022-02", "2023-01", "2023-05", "2024-12"]

    # Validar primer periodo: 2022-01 (120M cuantia, 20M adiciones, 1 contrato)
    p1 = df_ts.iloc[0]
    assert p1["periodo"] == "2022-01"
    assert pytest.approx(p1["cuantia_total"], rel=1e-3) == 120_000_000.0
    assert pytest.approx(p1["adiciones_total"], rel=1e-3) == 20_000_000.0
    assert p1["cantidad_contratos"] == 1
    assert "$ 120.0 M" in p1["monto_fmt"]

    # Validar periodo con mayor cuantía: 2023-05 (450M cuantia, 50M adiciones, 1 contrato)
    p4 = df_ts[df_ts["periodo"] == "2023-05"].iloc[0]
    assert pytest.approx(p4["cuantia_total"], rel=1e-3) == 450_000_000.0
    assert pytest.approx(p4["adiciones_total"], rel=1e-3) == 50_000_000.0


def test_obtener_serie_temporal_gasto_anual_dataframe_valido(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-23 / Criterio 1: Valida la agregación interanual cronológica:
    - Agrupación por anio_vigencia
    - Formato de periodo 'AAAA'
    - Consolidación acumulada anual
    - Ordenamiento ascendente de vigencias
    """
    df_anual = AnalyticsController.obtener_serie_temporal_gasto(sample_kpi_dataframe, granularidad="Anual")

    assert len(df_anual) == 3
    assert list(df_anual["periodo"]) == ["2022", "2023", "2024"]

    # 2022: 120M + 250M = 370M, adiciones: 20M, 2 contratos
    y2022 = df_anual.iloc[0]
    assert y2022["periodo"] == "2022"
    assert pytest.approx(y2022["cuantia_total"], rel=1e-3) == 370_000_000.0
    assert pytest.approx(y2022["adiciones_total"], rel=1e-3) == 20_000_000.0
    assert y2022["cantidad_contratos"] == 2

    # 2023: 60M + 450M = 510M, adiciones: 60M, 2 contratos
    y2023 = df_anual.iloc[1]
    assert y2023["periodo"] == "2023"
    assert pytest.approx(y2023["cuantia_total"], rel=1e-3) == 510_000_000.0
    assert pytest.approx(y2023["adiciones_total"], rel=1e-3) == 60_000_000.0

    # 2024: 200M, adiciones: 0, 1 contrato
    y2024 = df_anual.iloc[2]
    assert y2024["periodo"] == "2024"
    assert pytest.approx(y2024["cuantia_total"], rel=1e-3) == 200_000_000.0


def test_obtener_serie_temporal_gasto_vacio_o_none():
    """
    HU-23: Valida resiliencia ante DataFrames vacíos o None.
    """
    columnas_esperadas = ["periodo", "anio_vigencia", "mes_vigencia", "cuantia_total", "adiciones_total", "cantidad_contratos", "monto_fmt"]

    df_none = AnalyticsController.obtener_serie_temporal_gasto(None)
    assert isinstance(df_none, pd.DataFrame)
    assert df_none.empty
    assert list(df_none.columns) == columnas_esperadas

    df_vacio = AnalyticsController.obtener_serie_temporal_gasto(pd.DataFrame())
    assert isinstance(df_vacio, pd.DataFrame)
    assert df_vacio.empty
    assert list(df_vacio.columns) == columnas_esperadas


def test_generar_grafica_serie_temporal_figura_valida(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-23 / Criterio 2: Valida la figura Plotly estilo Figma Spline:
    - Retorna go.Figure con dos trazas (Cuantía Consolidada y Adiciones Presupuestales)
    - Línea con curva suavizada (shape='spline')
    - Área sombreada bajo la curva (fill='tozeroy')
    - Tooltip unificado y marcadores circulares
    """
    import plotly.graph_objects as go

    fig = AnalyticsController.generar_grafica_serie_temporal(sample_kpi_dataframe, granularidad="Mensual")

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2

    # Traza 1: Cuantía Consolidada
    traza_cuantia = fig.data[0]
    assert traza_cuantia.name == "Cuantía Consolidada"
    assert traza_cuantia.line.shape == "spline"
    assert traza_cuantia.fill == "tozeroy"
    assert "#4F46E5" in traza_cuantia.line.color

    # Traza 2: Adiciones Presupuestales
    traza_adiciones = fig.data[1]
    assert traza_adiciones.name == "Adiciones Presupuestales"
    assert traza_adiciones.line.dash == "dot"
    assert "#0EA5E9" in traza_adiciones.line.color


def test_generar_grafica_serie_temporal_figura_vacia():
    """
    HU-23: Valida que ante un conjunto sin datos se presente una figura informativa limpia.
    """
    import plotly.graph_objects as go

    fig_vacia = AnalyticsController.generar_grafica_serie_temporal(pd.DataFrame())
    assert isinstance(fig_vacia, go.Figure)
    assert len(fig_vacia.layout.annotations) > 0
    assert "Sin datos cronológicos disponibles" in fig_vacia.layout.annotations[0].text


def test_agregar_serie_temporal_mongo_paridad():
    """
    HU-23 / Criterio 3: Certifica paridad matemática entre el cálculo en memoria
    con Pandas y el Aggregation Pipeline de MongoDB ($group por tiempo.anio y tiempo.mes).
    """
    col = MongoConnectionSingleton.get_collection("contratos")
    if col.count_documents({}) > 0:
        docs = list(col.find({}, {"tiempo.anio_vigencia": 1, "tiempo.mes_vigencia": 1, "cuantia_final": 1, "valor_adiciones": 1}))
        registros_limpios = []
        for d in docs:
            t = d.get("tiempo", {}) if isinstance(d.get("tiempo"), dict) else {}
            registros_limpios.append({
                "anio_vigencia": t.get("anio_vigencia", 2022),
                "mes_vigencia": t.get("mes_vigencia", 1),
                "cuantia_final": d.get("cuantia_final", 0.0),
                "valor_adiciones": d.get("valor_adiciones", 0.0)
            })
        df_mongo = pd.DataFrame(registros_limpios)

        # Agregación en Pandas
        df_ts_pandas = AnalyticsController.obtener_serie_temporal_gasto(df_mongo, granularidad="Mensual")

        # Agregación en MongoDB
        lista_mongo = AnalyticsController.agregar_serie_temporal_mongo()

        assert len(lista_mongo) > 0
        total_mongo = sum(item["cuantia_total"] for item in lista_mongo)
        total_pandas = df_ts_pandas["cuantia_total"].sum()
        assert pytest.approx(total_mongo, rel=1e-3) == total_pandas

        total_adic_mongo = sum(item["adiciones_total"] for item in lista_mongo)
        total_adic_pandas = df_ts_pandas["adiciones_total"].sum()
        assert pytest.approx(total_adic_mongo, rel=1e-3) == total_adic_pandas


def test_obtener_serie_temporal_reactivo_con_query_builder(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-23: Valida reactividad temporal sobre subconjuntos filtrados con ConsultaSecopBuilder.
    """
    builder = ConsultaSecopBuilder(sample_kpi_dataframe)
    df_antioquia, _, _ = builder.filtrar_departamento(["ANTIOQUIA"]).build()

    # En Antioquia solo están CTR-001 (2022-01: 120M) y CTR-003 (2023-01: 60M)
    df_ts_ant = AnalyticsController.obtener_serie_temporal_gasto(df_antioquia, granularidad="Mensual")

    assert len(df_ts_ant) == 2
    assert list(df_ts_ant["periodo"]) == ["2022-01", "2023-01"]
    assert pytest.approx(df_ts_ant.iloc[0]["cuantia_total"], rel=1e-3) == 120_000_000.0
    assert pytest.approx(df_ts_ant.iloc[1]["cuantia_total"], rel=1e-3) == 60_000_000.0


def test_apptest_analytics_grafica_serie_temporal_ui():
    """
    HU-23 / Criterio 2 y 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a 'Analítica y Tendencias'
    3. Comprobar que se renderice el contenedor de la serie temporal cronológica
       sin errores visuales ni excepciones.
    """
    from streamlit.testing.v1 import AppTest

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar a Analítica y Tendencias
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Analítica y Tendencias").run()

    assert len(at.exception) == 0

    # Comprobar contenedor de la serie temporal
    html_analytics = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Evolución Cronológica del Gasto Contractual" in html_analytics
    assert "Serie Histórica y Estacionalidad Presupuestal" in html_analytics


# ==============================================================================
# PRUEBAS AUTOMATIZADAS HU-24: GRÁFICA DESCRIPTIVA 3 - TOP 10 ENTIDADES
# ==============================================================================

def test_obtener_top_entidades_dataframe_valido(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-24 / Criterio 1: Valida la clasificación y agregación del Top de entidades:
    - Agrupación por entidad compradora
    - Sumatoria de cuantia_final y valor_adiciones
    - Conteo de cantidad_contratos y cálculo de porcentaje de participación
    - Truncamiento estético para nombres extensos (entidad_corta <= 38 caracteres)
    - Ordenamiento estrictamente descendente
    """
    df_top = AnalyticsController.obtener_top_entidades(sample_kpi_dataframe, top_n=10)

    columnas_esperadas = [
        "entidad", "entidad_corta", "monto_total", "adiciones_total",
        "cantidad_contratos", "participacion_pct", "monto_fmt"
    ]
    assert list(df_top.columns) == columnas_esperadas
    assert len(df_top) == 4

    # Orden estrictamente descendente por monto_total
    assert df_top["monto_total"].is_monotonic_decreasing

    # Entidad líder: INSTITUTO DE DESARROLLO URBANO - IDU BOGOTÁ (450M)
    lider = df_top.iloc[0]
    assert lider["entidad"] == "INSTITUTO DE DESARROLLO URBANO - IDU BOGOTÁ"
    assert pytest.approx(lider["monto_total"], rel=1e-3) == 450_000_000.0
    assert pytest.approx(lider["adiciones_total"], rel=1e-3) == 50_000_000.0
    assert lider["cantidad_contratos"] == 1
    assert pytest.approx(lider["participacion_pct"], rel=1e-2) == 41.67
    assert "$ 450.0 M" in lider["monto_fmt"]

    # Validación de truncamiento elegante para el eje Y
    assert len(lider["entidad_corta"]) <= 38
    assert lider["entidad_corta"].endswith("...")

    # Validación de entidad con múltiples procesos: ALCALDÍA DE MEDELLÍN (120M + 60M = 180M)
    medellin = df_top[df_top["entidad"] == "ALCALDÍA DE MEDELLÍN"].iloc[0]
    assert pytest.approx(medellin["monto_total"], rel=1e-3) == 180_000_000.0
    assert pytest.approx(medellin["adiciones_total"], rel=1e-3) == 30_000_000.0
    assert medellin["cantidad_contratos"] == 2
    assert medellin["entidad_corta"] == "ALCALDÍA DE MEDELLÍN"


def test_obtener_top_entidades_limite_top_n(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-24 / Criterio 1: Valida que el parámetro top_n acote estrictamente la cantidad de registros.
    """
    df_top_2 = AnalyticsController.obtener_top_entidades(sample_kpi_dataframe, top_n=2)
    assert len(df_top_2) == 2
    assert df_top_2.iloc[0]["entidad"] == "INSTITUTO DE DESARROLLO URBANO - IDU BOGOTÁ"
    assert df_top_2.iloc[1]["entidad"] == "GOBERNACIÓN DEL VALLE DEL CAUCA"


def test_obtener_top_entidades_vacio_o_none():
    """
    HU-24: Valida resiliencia ante DataFrames vacíos o None.
    """
    columnas_esperadas = [
        "entidad", "entidad_corta", "monto_total", "adiciones_total",
        "cantidad_contratos", "participacion_pct", "monto_fmt"
    ]
    df_none = AnalyticsController.obtener_top_entidades(None)
    assert isinstance(df_none, pd.DataFrame)
    assert df_none.empty
    assert list(df_none.columns) == columnas_esperadas

    df_vacio = AnalyticsController.obtener_top_entidades(pd.DataFrame())
    assert isinstance(df_vacio, pd.DataFrame)
    assert df_vacio.empty
    assert list(df_vacio.columns) == columnas_esperadas


def test_generar_grafica_top_entidades_figura_valida(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-24 / Criterio 2: Valida la figura Plotly de barras horizontales:
    - Retorna instancia de go.Figure
    - Barra horizontal (orientation='h')
    - Customdata preserva nombre institucional completo
    - Resalta el Top 3 en índigo corporativo (#4F46E5)
    """
    import plotly.graph_objects as go

    fig = AnalyticsController.generar_grafica_top_entidades(sample_kpi_dataframe, top_n=10)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0

    traza = fig.data[0]
    assert traza.type == "bar"
    assert traza.orientation == "h"

    # Verificar que el color índigo (#4F46E5) está asignado a las entidades del Top 3
    colores_asignados = list(traza.marker.color)
    assert "#4F46E5" in colores_asignados

    # Tooltip contiene campos ejecutivos
    assert "Presupuesto Ejecutado" in traza.hovertemplate
    assert "Adiciones Acumuladas" in traza.hovertemplate
    assert "Contratos Adjudicados" in traza.hovertemplate


def test_generar_grafica_top_entidades_figura_vacia():
    """
    HU-24: Valida que ante un conjunto sin datos se retorne una figura informativa.
    """
    import plotly.graph_objects as go

    fig_vacia = AnalyticsController.generar_grafica_top_entidades(pd.DataFrame())
    assert isinstance(fig_vacia, go.Figure)
    assert len(fig_vacia.layout.annotations) > 0
    assert "Sin entidades registradas" in fig_vacia.layout.annotations[0].text


def test_agregar_top_entidades_mongo_paridad():
    """
    HU-24 / Criterio 3: Certifica paridad matemática entre el cálculo en memoria
    con Pandas y el Aggregation Pipeline de MongoDB ($match -> $group -> $sort -> $limit).
    """
    col = MongoConnectionSingleton.get_collection("contratos")
    if col.count_documents({}) > 0:
        docs = list(col.find({}, {"entidad.nombre": 1, "cuantia_final": 1, "valor_adiciones": 1}))
        registros_limpios = []
        for d in docs:
            ent = d.get("entidad", {}).get("nombre") if isinstance(d.get("entidad"), dict) else None
            registros_limpios.append({
                "entidad": ent or "ENTIDAD NO ESPECIFICADA",
                "cuantia_final": d.get("cuantia_final", 0.0),
                "valor_adiciones": d.get("valor_adiciones", 0.0)
            })
        df_mongo = pd.DataFrame(registros_limpios)

        # Agregación con Pandas
        df_top_pandas = AnalyticsController.obtener_top_entidades(df_mongo, top_n=10)

        # Agregación con MongoDB
        lista_mongo = AnalyticsController.agregar_top_entidades_mongo(top_n=10)

        assert len(lista_mongo) <= 10
        assert len(lista_mongo) == len(df_top_pandas)

        # Verificar que el monto de la entidad #1 coincide
        if lista_mongo:
            assert lista_mongo[0]["_id"] == df_top_pandas.iloc[0]["entidad"]
            assert pytest.approx(lista_mongo[0]["monto_total"], rel=1e-3) == df_top_pandas.iloc[0]["monto_total"]

        # Verificar ordenamiento descendente en MongoDB
        montos_mongo = [item["monto_total"] for item in lista_mongo]
        assert montos_mongo == sorted(montos_mongo, reverse=True)


def test_obtener_top_entidades_reactivo_con_query_builder(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-24: Valida la reactividad de la clasificación cuando el conjunto es filtrado con ConsultaSecopBuilder.
    """
    builder = ConsultaSecopBuilder(sample_kpi_dataframe)
    df_antioquia, _, _ = builder.filtrar_departamento(["ANTIOQUIA"]).build()

    # En Antioquia solo está la ALCALDÍA DE MEDELLÍN (180M)
    df_top_ant = AnalyticsController.obtener_top_entidades(df_antioquia, top_n=10)

    assert len(df_top_ant) == 1
    assert df_top_ant.iloc[0]["entidad"] == "ALCALDÍA DE MEDELLÍN"
    assert pytest.approx(df_top_ant.iloc[0]["monto_total"], rel=1e-3) == 180_000_000.0
    assert df_top_ant.iloc[0]["cantidad_contratos"] == 2
    assert pytest.approx(df_top_ant.iloc[0]["participacion_pct"], rel=1e-3) == 100.0


def test_apptest_analytics_grafica_top_entidades_ui():
    """
    HU-24 / Criterio 2 y 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a 'Analítica y Tendencias'
    3. Comprobar que se renderice el contenedor del Top 10 de entidades
       sin errores visuales ni excepciones.
    """
    from streamlit.testing.v1 import AppTest

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar a Analítica y Tendencias
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Analítica y Tendencias").run()

    assert len(at.exception) == 0

    # Comprobar contenedor del Top 10 de entidades
    html_analytics = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Top 10 Entidades con Mayor Ejecución Presupuestal" in html_analytics
    assert "Control de Gestión y Auditoría" in html_analytics


# ==============================================================================
# PRUEBAS AUTOMATIZADAS HU-25: GRÁFICA DESCRIPTIVA 4 - DISTRIBUCIÓN POR ESTADO
# ==============================================================================

def test_obtener_distribucion_estados_dataframe_valido(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-25 / Criterio 1: Valida la agregación por estado contractual:
    - Agrupación por estado (Modificado, En ejecución, Celebrado, Terminado)
    - Cálculo de cantidad_contratos y porcentaje sobre el total
    - Consolidación de monto_total acumulado
    - Ordenamiento descendente por volumen de procesos
    """
    df_est = AnalyticsController.obtener_distribucion_estados(sample_kpi_dataframe)

    columnas_esperadas = ["estado", "cantidad_contratos", "porcentaje", "monto_total", "monto_fmt"]
    assert list(df_est.columns) == columnas_esperadas
    assert len(df_est) == 4

    # Estado líder en volumen: MODIFICADO con 2 procesos (40.0%)
    lider = df_est.iloc[0]
    assert lider["estado"] == "MODIFICADO"
    assert lider["cantidad_contratos"] == 2
    assert pytest.approx(lider["porcentaje"], rel=1e-2) == 40.0
    assert pytest.approx(lider["monto_total"], rel=1e-3) == 180_000_000.0
    assert "$ 180.0 M" in lider["monto_fmt"]

    # Suma de contratos debe ser igual a 5 y porcentajes sumar 100%
    assert df_est["cantidad_contratos"].sum() == 5
    assert pytest.approx(df_est["porcentaje"].sum(), rel=1e-3) == 100.0


def test_obtener_distribucion_estados_consolidacion_otros():
    """
    HU-25 / Criterio 1: Valida que si existen más de max_categorias (6),
    los estados minoritarios se agrupen bajo 'Otros estados'.
    """
    datos_muchos_estados = pd.DataFrame({
        "estado": ["E1", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"],
        "cuantia_final": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    })
    df_est = AnalyticsController.obtener_distribucion_estados(datos_muchos_estados, max_categorias=6)

    assert len(df_est) == 6
    assert "Otros estados" in list(df_est["estado"])

    # 'Otros estados' debe agrupar los 3 últimos estados minoritarios (3 contratos)
    fila_otros = df_est[df_est["estado"] == "Otros estados"].iloc[0]
    assert fila_otros["cantidad_contratos"] == 3
    assert pytest.approx(fila_otros["monto_total"], rel=1e-3) == 30.0


def test_obtener_distribucion_estados_vacio_o_none():
    """
    HU-25: Valida resiliencia ante DataFrames vacíos o None.
    """
    columnas_esperadas = ["estado", "cantidad_contratos", "porcentaje", "monto_total", "monto_fmt"]

    df_none = AnalyticsController.obtener_distribucion_estados(None)
    assert isinstance(df_none, pd.DataFrame)
    assert df_none.empty
    assert list(df_none.columns) == columnas_esperadas

    df_vacio = AnalyticsController.obtener_distribucion_estados(pd.DataFrame())
    assert isinstance(df_vacio, pd.DataFrame)
    assert df_vacio.empty
    assert list(df_vacio.columns) == columnas_esperadas


def test_generar_grafica_dona_estados_figura_valida(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-25 / Criterio 2: Valida la figura Plotly de dona estilo Figma:
    - Retorna go.Figure con una traza go.Pie
    - Configuración de dona con agujero central (hole=0.64)
    - Indicador central en el anillo con conteo total de procesos
    - Customdata preserva monto_total y monto_fmt para tooltips
    """
    import plotly.graph_objects as go

    fig = AnalyticsController.generar_grafica_dona_estados(sample_kpi_dataframe)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1

    traza = fig.data[0]
    assert traza.type == "pie"
    assert pytest.approx(traza.hole, rel=1e-2) == 0.64

    # Verificar que el centro tiene la anotación con el total de contratos (5)
    assert len(fig.layout.annotations) > 0
    assert "5" in fig.layout.annotations[0].text
    assert "Contratos" in fig.layout.annotations[0].text

    # Hovertemplate contiene campos clave
    assert "Contratos:" in traza.hovertemplate
    assert "Cuantía Asociada:" in traza.hovertemplate


def test_generar_grafica_dona_estados_figura_vacia():
    """
    HU-25: Valida que ante un conjunto sin datos se retorne una figura informativa.
    """
    import plotly.graph_objects as go

    fig_vacia = AnalyticsController.generar_grafica_dona_estados(pd.DataFrame())
    assert isinstance(fig_vacia, go.Figure)
    assert len(fig_vacia.layout.annotations) > 0
    assert "Sin registros de estado disponibles" in fig_vacia.layout.annotations[0].text


def test_agregar_estados_mongo_paridad():
    """
    HU-25 / Criterio 3: Certifica paridad matemática entre el cálculo en memoria
    con Pandas y el Aggregation Pipeline de MongoDB ($match -> $group por clasificacion.estado).
    """
    col = MongoConnectionSingleton.get_collection("contratos")
    if col.count_documents({}) > 0:
        docs = list(col.find({}, {"clasificacion.estado": 1, "cuantia_final": 1}))
        registros_limpios = []
        for d in docs:
            est = d.get("clasificacion", {}).get("estado") if isinstance(d.get("clasificacion"), dict) else None
            registros_limpios.append({
                "estado": est or "SIN ESTADO DEFINIDO",
                "cuantia_final": d.get("cuantia_final", 0.0)
            })
        df_mongo = pd.DataFrame(registros_limpios)

        # Agregación en Pandas
        df_est_pandas = AnalyticsController.obtener_distribucion_estados(df_mongo, max_categorias=50)

        # Agregación en MongoDB
        lista_mongo = AnalyticsController.agregar_estados_mongo()

        assert len(lista_mongo) > 0
        total_mongo = sum(item["cantidad_contratos"] for item in lista_mongo)
        total_pandas = df_est_pandas["cantidad_contratos"].sum()
        assert total_mongo == total_pandas

        # Verificar ordenamiento descendente por cantidad_contratos
        cantidades_mongo = [item["cantidad_contratos"] for item in lista_mongo]
        assert cantidades_mongo == sorted(cantidades_mongo, reverse=True)


def test_obtener_distribucion_estados_reactivo_con_query_builder(sample_kpi_dataframe: pd.DataFrame):
    """
    HU-25: Valida la reactividad de la distribución de estados sobre subconjuntos filtrados con ConsultaSecopBuilder.
    """
    builder = ConsultaSecopBuilder(sample_kpi_dataframe)
    df_antioquia, _, _ = builder.filtrar_departamento(["ANTIOQUIA"]).build()

    # En Antioquia solo están CTR-001 (MODIFICADO) y CTR-003 (MODIFICADO)
    df_est_ant = AnalyticsController.obtener_distribucion_estados(df_antioquia)

    assert len(df_est_ant) == 1
    assert df_est_ant.iloc[0]["estado"] == "MODIFICADO"
    assert df_est_ant.iloc[0]["cantidad_contratos"] == 2
    assert pytest.approx(df_est_ant.iloc[0]["porcentaje"], rel=1e-3) == 100.0
    assert pytest.approx(df_est_ant.iloc[0]["monto_total"], rel=1e-3) == 180_000_000.0


def test_apptest_analytics_grafica_dona_estados_ui():
    """
    HU-25 / Criterio 2 y 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a 'Analítica y Tendencias'
    3. Comprobar que se renderice el contenedor del gráfico de dona de estados
       sin errores visuales ni excepciones.
    """
    from streamlit.testing.v1 import AppTest

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar a Analítica y Tendencias
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Analítica y Tendencias").run()

    assert len(at.exception) == 0

    # Comprobar contenedor de la gráfica de dona de estados
    html_analytics = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Distribución por Estado de los Procesos" in html_analytics
    assert "Ciclo de Vida Contractual" in html_analytics


# ==============================================================================
# PRUEBAS HU-26: GRÁFICA DESCRIPTIVA 5 - BOXPLOT DE DISPERSIÓN DE CUANTÍAS Y PLAZOS
# ==============================================================================

@pytest.fixture
def sample_dispersion_dataframe() -> pd.DataFrame:
    """Fixture con contratos y tipologías contractuales para prueba de cuartiles y boxplot."""
    return pd.DataFrame({
        "id_contrato": [f"CTR-{i:03d}" for i in range(1, 13)],
        "tipo_contrato": [
            "Obra", "Obra", "Obra", "Obra",
            "Prestación de servicios", "Prestación de servicios", "Prestación de servicios", "Prestación de servicios",
            "Suministro", "Suministro", "Suministro", "Suministro"
        ],
        "cuantia_final": [
            100_000_000.0, 150_000_000.0, 200_000_000.0, 1_000_000_000.0,
            20_000_000.0, 25_000_000.0, 30_000_000.0, 35_000_000.0,
            50_000_000.0, 60_000_000.0, 70_000_000.0, 80_000_000.0
        ],
        "plazo_dias": [
            180, 240, 300, 720,
            30, 60, 90, 120,
            15, 30, 45, 60
        ]
    })


def test_obtener_estadisticas_dispersion_tipo_calculos(sample_dispersion_dataframe: pd.DataFrame):
    """
    HU-26 / Criterio 1: Valida el cálculo de cuartiles, rango intercuartílico (IQR)
    y detección de valores atípicos (outliers) por tipología contractual.
    """
    df_plot, df_resumen = AnalyticsController.obtener_estadisticas_dispersion_tipo(
        sample_dispersion_dataframe, metrica="cuantia_final"
    )

    assert not df_plot.empty
    assert not df_resumen.empty
    assert len(df_resumen) == 3

    # Ordenado por mediana descendente: Obra (175M), Suministro (65M), Prestación (27.5M)
    assert df_resumen.iloc[0]["tipo_contrato"] == "Obra"
    assert df_resumen.iloc[0]["cantidad"] == 4
    assert df_resumen.iloc[0]["mediana"] == 175_000_000.0
    assert df_resumen.iloc[0]["q1"] == 137_500_000.0
    assert df_resumen.iloc[0]["q3"] == 400_000_000.0
    assert df_resumen.iloc[0]["iqr"] == 262_500_000.0
    assert df_resumen.iloc[0]["maximo"] == 1_000_000_000.0
    # Obra supera q3 + 1.5*iqr (400M + 393.75M = 793.75M) con 1,000M -> 1 outlier detectado
    assert df_resumen.iloc[0]["outliers_count"] == 1

    # Prestación de servicios sin outliers extremos
    fila_prest = df_resumen[df_resumen["tipo_contrato"] == "Prestación de servicios"].iloc[0]
    assert fila_prest["cantidad"] == 4
    assert fila_prest["outliers_count"] == 0


def test_obtener_estadisticas_dispersion_tipo_plazos(sample_dispersion_dataframe: pd.DataFrame):
    """
    HU-26 / Criterio 1: Valida el cálculo de dispersión para la métrica alternativa de plazos (días).
    """
    df_plot, df_resumen = AnalyticsController.obtener_estadisticas_dispersion_tipo(
        sample_dispersion_dataframe, metrica="plazo_dias"
    )

    assert not df_plot.empty
    assert not df_resumen.empty
    assert "Obra" in df_resumen["tipo_contrato"].values
    fila_obra = df_resumen[df_resumen["tipo_contrato"] == "Obra"].iloc[0]
    assert fila_obra["mediana"] == 270.0
    assert fila_obra["maximo"] == 720.0


def test_obtener_estadisticas_dispersion_tipo_vacio_o_none():
    """
    HU-26: Valida robustez ante DataFrames vacíos o valores nulos.
    """
    p1, r1 = AnalyticsController.obtener_estadisticas_dispersion_tipo(None)
    assert p1.empty
    assert r1.empty
    assert "outliers_count" in r1.columns

    p2, r2 = AnalyticsController.obtener_estadisticas_dispersion_tipo(pd.DataFrame())
    assert p2.empty
    assert r2.empty


def test_generar_grafica_boxplot_dispersion_figura_valida(sample_dispersion_dataframe: pd.DataFrame):
    """
    HU-26 / Criterio 2: Valida la generación del objeto Figure de Plotly con trazas tipo Box,
    escala logarítmica y lineal.
    """
    import plotly.graph_objects as go

    # Escala logarítmica con cuantías
    fig_log = AnalyticsController.generar_grafica_boxplot_dispersion(
        sample_dispersion_dataframe, metrica="cuantia_final", escala_log=True
    )
    assert isinstance(fig_log, go.Figure)
    assert len(fig_log.data) == 3
    assert fig_log.data[0].type == "box"
    assert fig_log.layout.yaxis.type == "log"
    assert "$ " in fig_log.layout.yaxis.tickprefix
    assert "Dispersión de Cuantías Contractuales" in fig_log.layout.title.text

    # Escala lineal con plazos
    fig_lin = AnalyticsController.generar_grafica_boxplot_dispersion(
        sample_dispersion_dataframe, metrica="plazo_dias", escala_log=False
    )
    assert isinstance(fig_lin, go.Figure)
    assert fig_lin.layout.yaxis.type == "linear"
    assert fig_lin.layout.yaxis.tickprefix == ""
    assert "Dispersión de Plazos de Ejecución" in fig_lin.layout.title.text


def test_generar_grafica_boxplot_dispersion_figura_vacia():
    """
    HU-26: Valida que ante datos vacíos se genere una figura con anotación informativa.
    """
    import plotly.graph_objects as go

    fig = AnalyticsController.generar_grafica_boxplot_dispersion(pd.DataFrame())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0
    assert len(fig.layout.annotations) > 0
    assert "Sin registros numéricos suficientes" in fig.layout.annotations[0].text


def test_agregar_dispersion_tipo_mongo():
    """
    HU-26 / Criterio 3: Valida la ejecución del pipeline de agregación en MongoDB
    sobre clasificacion.tipo_contrato.
    """
    resultado = AnalyticsController.agregar_dispersion_tipo_mongo()
    assert isinstance(resultado, list)


def test_apptest_analytics_grafica_boxplot_dispersion_ui():
    """
    HU-26 / Criterios 1, 2 y 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a 'Analítica y Tendencias'
    3. Comprobar que se renderice el contenedor del diagrama de caja de dispersión
       y los conmutadores de variable y escala sin errores ni excepciones.
    """
    from streamlit.testing.v1 import AppTest

    repo = DataRepositorySingleton.get_instance()
    repo.cargar_fuente()

    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()

    # Iniciar sesión
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    assert at.session_state.get("autenticado") is True
    assert len(at.exception) == 0

    # Navegar a Analítica y Tendencias
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Analítica y Tendencias").run()

    assert len(at.exception) == 0

    # Comprobar contenedor del Boxplot de dispersión
    html_analytics = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Dispersión y Valores Atípicos por Tipología Contractual" in html_analytics
    assert "Diagnóstico de Cuartiles y Outliers" in html_analytics







