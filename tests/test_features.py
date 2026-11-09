"""
Suite de Pruebas Automatizadas de Ingeniería de Características (Feature Engineering)
Historia de Usuario: HU-07 (Generación de Variables Analíticas Derivadas)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
import numpy as np
import pandas as pd
import pytest
from src.etl.feature_engineering import FeatureEngineer


def test_calculo_cuantia_final():
    """
    HU-07 / Criterio 1: Verifica que para un contrato con cuantia_inicial = 100M
    y valor_adiciones = 25M, cuantia_final sea exactamente 125M (float64).
    """
    datos = pd.DataFrame([{
        "cuantia_inicial": 100_000_000.0,
        "valor_adiciones": 25_000_000.0
    }])

    df_res = FeatureEngineer.calcular_cuantias_y_etiqueta_adicion(datos)

    assert df_res.iloc[0]["cuantia_final"] == 125_000_000.0
    assert df_res["cuantia_final"].dtype == np.float64


def test_etiqueta_tiene_adicion_true():
    """
    HU-07 / Criterio 2: Verifica que cuando valor_adiciones > 0, tiene_adicion sea estrictamente True.
    """
    datos = pd.DataFrame([
        {"cuantia_inicial": 50_000_000.0, "valor_adiciones": 5_000_000.0},
        {"cuantia_inicial": 20_000_000.0, "valor_adiciones": 1.0}
    ])

    df_res = FeatureEngineer.calcular_cuantias_y_etiqueta_adicion(datos)

    assert bool(df_res.iloc[0]["tiene_adicion"]) is True
    assert bool(df_res.iloc[1]["tiene_adicion"]) is True
    assert (df_res["tiene_adicion"] == True).all()


def test_etiqueta_tiene_adicion_false():
    """
    HU-07 / Criterio 2: Verifica que cuando valor_adiciones == 0.0 o <= 0, tiene_adicion sea False.
    """
    datos = pd.DataFrame([
        {"cuantia_inicial": 40_000_000.0, "valor_adiciones": 0.0},
        {"cuantia_inicial": 30_000_000.0, "valor_adiciones": 0},
        {"cuantia_inicial": 15_000_000.0, "valor_adiciones": -100.0}
    ])

    df_res = FeatureEngineer.calcular_cuantias_y_etiqueta_adicion(datos)

    assert bool(df_res.iloc[0]["tiene_adicion"]) is False
    assert bool(df_res.iloc[1]["tiene_adicion"]) is False
    assert bool(df_res.iloc[2]["tiene_adicion"]) is False
    assert (df_res["tiene_adicion"] == False).all()


def test_calculo_plazo_dias_positivo():
    """
    HU-07 / Criterio 3: Valida que plazo_dias sea un entero positivo mayor que cero
    para todas las filas tras la conversión de unidades (días, meses, años) e imputación.
    """
    datos = pd.DataFrame([
        {"plazo_ejecucion_dias": "30 Días"},
        {"plazo_ejecucion_dias": "12 Meses"},
        {"plazo_ejecucion_dias": "1 Año"},
        {"plazo_ejecucion_dias": 90},
        {"plazo_ejecucion_dias": 0},       # Inválido: debe imputarse con mediana
        {"plazo_ejecucion_dias": -15},     # Inválido: debe imputarse con mediana
        {"plazo_ejecucion_dias": None}     # Nulo: debe imputarse con mediana
    ])

    df_res = FeatureEngineer.estandarizar_plazo_dias(datos, col_plazo="plazo_ejecucion_dias")

    assert (df_res["plazo_dias"] > 0).all(), "Todos los plazos deben ser estrictamente > 0"
    assert df_res.iloc[0]["plazo_dias"] == 30
    assert df_res.iloc[1]["plazo_dias"] == 360  # 12 meses * 30
    assert df_res.iloc[2]["plazo_dias"] == 365  # 1 año * 365
    assert df_res.iloc[3]["plazo_dias"] == 90

    # Las filas 4, 5 y 6 deben tener valores válidos mayores que cero
    for idx in [4, 5, 6]:
        assert df_res.iloc[idx]["plazo_dias"] > 0


def test_consistencia_tipos_series():
    """
    HU-07 / Criterio 5: Asegura la consistencia tipológica de las variables generadas:
    tiene_adicion (bool), plazo_dias (entero) y cuantia_final (float64).
    """
    datos = pd.DataFrame([
        {"cuantia_inicial": 1000000.0, "valor_adiciones": 500000.0, "plazo_ejecucion_dias": "60 Días"},
        {"cuantia_inicial": 2000000.0, "valor_adiciones": 0.0, "plazo_ejecucion_dias": "3 Meses"}
    ])

    df_res, _ = FeatureEngineer.aplicar_feature_engineering_lote(datos)

    assert df_res["tiene_adicion"].dtype == bool
    assert np.issubdtype(df_res["plazo_dias"].dtype, np.integer)
    assert np.issubdtype(df_res["plazo_ejecucion_dias"].dtype, np.integer)
    assert df_res["cuantia_final"].dtype == np.float64


def test_features_adicionales_ml():
    """
    HU-07: Comprueba la correcta generación de variables para Machine Learning:
    porcentaje_adicion, tasa_gasto_diario y es_cuantia_alta.
    """
    datos = pd.DataFrame([
        {"cuantia_inicial": 100_000_000.0, "valor_adiciones": 20_000_000.0, "plazo_ejecucion_dias": 100},
        {"cuantia_inicial": 50_000_000.0, "valor_adiciones": 0.0, "plazo_ejecucion_dias": 50}
    ])

    df_res, metricas = FeatureEngineer.aplicar_feature_engineering_lote(datos)

    assert "porcentaje_adicion" in df_res.columns
    assert "tasa_gasto_diario" in df_res.columns
    assert "es_cuantia_alta" in df_res.columns

    # Fila 0: 20M / 100M = 0.20
    assert df_res.iloc[0]["porcentaje_adicion"] == 0.20
    # Fila 0: 120M / 100 días = 1,200,000.0 COP/día
    assert df_res.iloc[0]["tasa_gasto_diario"] == 1200000.0

    # Fila 1: 0% adición
    assert df_res.iloc[1]["porcentaje_adicion"] == 0.0

    # Métricas de resumen
    assert metricas["total_registros"] == 2
    assert metricas["total_con_adicion"] == 1
    assert metricas["tasa_adicion_pct"] == 50.0
    assert metricas["cuantia_final_total"] == 170_000_000.0


def test_feature_engineering_dataset_real_10k():
    """
    HU-07: Valida la aplicación del FeatureEngineer sobre el lote real de 10k contratos.
    """
    from src.etl.etl_pipeline import SecopETLPipeline
    pipeline = SecopETLPipeline()

    df_extraido = pipeline.extraer_csv("data/raw/secop muestra 10k 2022.csv")
    df_res, resumen = FeatureEngineer.aplicar_feature_engineering_lote(df_extraido)

    assert len(df_res) == 10000
    assert (df_res["plazo_dias"] > 0).all(), "Todos los plazos del dataset real deben ser > 0"
    assert (df_res["cuantia_final"] >= df_res["cuantia_inicial"]).all()
    assert resumen["total_registros"] == 10000
    assert resumen["plazo_promedio_dias"] > 0
    assert resumen["plazo_mediana_dias"] > 0
