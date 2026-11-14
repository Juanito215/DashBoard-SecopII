"""
Suite de Pruebas Automatizadas del Simulador Predictivo de Riesgo
Historia de Usuario: HU-27 (Simulador Interactivo de Inferencia de Riesgo)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.database.data_repository import DataRepositorySingleton
from src.ml.risk_predictor import RiskPredictorService


@pytest.fixture
def sample_ml_training_dataframe() -> pd.DataFrame:
    """Fixture con contratos etiquetados para entrenamiento supervisado de adiciones."""
    return pd.DataFrame({
        "id_contrato": [f"CTR-ML-{i:03d}" for i in range(1, 31)],
        "cuantia_inicial": [
            50_000_000.0, 100_000_000.0, 500_000_000.0, 1_200_000_000.0, 80_000_000.0, 250_000_000.0
        ] * 5,
        "plazo_dias": [30, 90, 180, 365, 60, 240] * 5,
        "es_pyme": [True, False, False, False, True, True] * 5,
        "departamento": ["Antioquia", "Valle del Cauca", "Bogotá D.C.", "Santander", "Atlántico", "Cundinamarca"] * 5,
        "modalidad": [
            "Contratación directa", "Licitación pública", "Contratación directa",
            "Licitación pública", "Mínima cuantía", "Selección abreviada"
        ] * 5,
        "tipo_contrato": [
            "Prestación de servicios", "Obra pública", "Obra pública",
            "Obra pública", "Suministro", "Consultoría"
        ] * 5,
        "tiene_adicion": [0, 1, 1, 1, 0, 0] * 5,
        "valor_adiciones": [0.0, 25_000_000.0, 120_000_000.0, 350_000_000.0, 0.0, 0.0] * 5,
    })


def test_risk_predictor_singleton_instance():
    """Valida el patrón Singleton para la instancia de RiskPredictorService."""
    inst1 = RiskPredictorService.get_instance()
    inst2 = RiskPredictorService.get_instance()
    assert inst1 is inst2


def test_risk_predictor_entrenamiento_valido(sample_ml_training_dataframe: pd.DataFrame):
    """
    HU-27 / Criterio 1: Valida el entrenamiento supervisado sobre dataset válido,
    alcanzando precisión y estado entrenado.
    """
    service = RiskPredictorService()
    res = service.entrenar(sample_ml_training_dataframe)

    assert res["entrenado"] is True
    assert service.entrenado is True
    assert service.pipeline is not None
    assert service.accuracy >= 0.0
    assert service.tasa_sobrecosto_media > 0.0


def test_risk_predictor_entrenamiento_dataset_pequeno():
    """
    HU-27: Valida que ante datasets insuficientes (<20 registros) el servicio no falle
    y reporte estado no entrenado de forma segura.
    """
    service = RiskPredictorService()
    df_corto = pd.DataFrame({"cuantia_inicial": [10e6, 20e6], "plazo_dias": [30, 60]})
    res = service.entrenar(df_corto)

    assert res["entrenado"] is False
    assert service.entrenado is False
    assert res["accuracy"] == 0.0

    res_none = service.entrenar(None)
    assert res_none["entrenado"] is False


def test_risk_predictor_entrenamiento_una_sola_clase(sample_ml_training_dataframe: pd.DataFrame):
    """
    HU-27: Valida manejo de respaldo sintético ante lotes con una única clase (todos 0 o todos 1).
    """
    service = RiskPredictorService()
    df_monoclase = sample_ml_training_dataframe.copy()
    df_monoclase["tiene_adicion"] = 0
    df_monoclase["valor_adiciones"] = 0.0

    res = service.entrenar(df_monoclase)
    assert res["entrenado"] is True
    assert service.entrenado is True


def test_predecir_riesgo_contrato_keys_y_metricas(sample_ml_training_dataframe: pd.DataFrame):
    """
    HU-27 / Criterio 3: Valida que la inferencia devuelva todas las métricas probabilísticas,
    financieras y clasificaciones de alerta requeridas.
    """
    service = RiskPredictorService()
    service.entrenar(sample_ml_training_dataframe)

    res = service.predecir_riesgo_contrato(
        departamento="Antioquia",
        modalidad="Contratación directa",
        tipo_contrato="Obra pública",
        es_pyme=False,
        cuantia_inicial=300_000_000.0,
        plazo_dias=200,
        usuario_auditor="auditor@secopanalytics.gov.co",
        guardar_en_mongo=False
    )

    claves_esperadas = [
        "score_riesgo_anomalia",
        "probabilidad_adicion_pct",
        "tiene_adicion_predicha",
        "nivel_alerta",
        "color_alerta",
        "porcentaje_sobrecosto_est",
        "sobrecosto_estimado_cop",
        "cuantia_final_proyectada_cop",
        "accuracy_modelo_pct",
    ]
    for c in claves_esperadas:
        assert c in res, f"Falta la clave {c} en la respuesta de predicción"

    assert 0.0 <= res["score_riesgo_anomalia"] <= 1.0
    assert 0.0 <= res["probabilidad_adicion_pct"] <= 100.0
    assert isinstance(res["tiene_adicion_predicha"], bool)
    assert res["nivel_alerta"] in ["Riesgo Alto", "Riesgo Moderado", "Riesgo Bajo"]
    assert res["color_alerta"] in ["#E11D48", "#D97706", "#059669"]
    assert res["sobrecosto_estimado_cop"] >= 0.0
    assert res["cuantia_final_proyectada_cop"] >= 300_000_000.0


def test_predecir_riesgo_contrato_sin_entrenar_heuristica():
    """
    HU-27: Valida que si el modelo no fue entrenado previamente, entregue inferencias
    consistentes mediante la heurística empírica calibrada de respaldo.
    """
    service = RiskPredictorService()
    assert service.entrenado is False

    res = service.predecir_riesgo_contrato(
        departamento="Bogotá D.C.",
        modalidad="Licitación pública",
        tipo_contrato="Prestación de servicios",
        es_pyme=True,
        cuantia_inicial=100_000_000.0,
        plazo_dias=60,
        guardar_en_mongo=False
    )

    assert 0.0 < res["score_riesgo_anomalia"] < 1.0
    assert res["nivel_alerta"] in ["Riesgo Alto", "Riesgo Moderado", "Riesgo Bajo"]
    assert res["cuantia_final_proyectada_cop"] > 100_000_000.0


def test_generar_grafica_gauge_riesgo_figura():
    """
    HU-27 / Criterio 3: Valida la construcción del gráfico de medidor (Gauge Chart) en Plotly.
    """
    fig = RiskPredictorService.generar_grafica_gauge_riesgo(
        probabilidad_pct=72.5,
        nivel_alerta="Riesgo Alto",
        color_alerta="#E11D48",
        es_oscuro=False
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "indicator"
    assert fig.data[0].value == 72.5


def test_persistir_prediccion_mongo_tolerancia_fallos():
    """
    HU-27: Valida la persistencia en MongoDB y garantiza no interrupción si la base de datos está offline.
    """
    params = {"cuantia_inicial": 200_000_000.0, "plazo_dias": 90}
    resultado = {
        "score_riesgo_anomalia": 0.45,
        "probabilidad_adicion_pct": 45.0,
        "nivel_alerta": "Riesgo Moderado",
        "sobrecosto_estimado_cop": 30_000_000.0,
        "cuantia_final_proyectada_cop": 230_000_000.0,
    }
    # Debe ejecutarse sin lanzar excepciones
    RiskPredictorService._persistir_prediccion_mongo(params, resultado, usuario="auditor_test")


def test_apptest_predictive_view_ui():
    """
    HU-27 / Criterios 2 y 3: Prueba de integración con Streamlit AppTest:
    1. Iniciar sesión como Analista_BI
    2. Navegar a 'Inteligencia Predictiva'
    3. Comprobar que se renderice el formulario del simulador y el diagnóstico predictivo
    4. Ejecutar el botón de evaluación sin errores ni excepciones.
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

    # Navegar a Inteligencia Predictiva
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Inteligencia Predictiva").run()

    assert len(at.exception) == 0

    # Verificar que el formulario y las tarjetas gerenciales se hayan renderizado
    html_predictive = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Parámetros del Proceso a Evaluar" in html_predictive
    assert "Score de Riesgo Predictivo" in html_predictive
    assert "Proyección Financiera y Sobrecosto Esperado" in html_predictive
    assert "Cuantía Final Proyectada" in html_predictive

    # Ejecutar simulación con botón
    btn_evaluar = [b for b in at.button if "Evaluar" in str(b.label)]
    if btn_evaluar:
        btn_evaluar[0].click().run()
        assert len(at.exception) == 0


# ==============================================================================
# PRUEBAS HU-28: SCORE DE ANOMALÍA Y NIVEL DE ALERTA
# ==============================================================================

def test_categorizar_nivel_alerta_umbrales():
    """
    HU-28 / Criterios 1 y 2: Valida la categorización determinística en niveles
    de alerta según los umbrales de severidad (Bajo < 0.35, Moderado < 0.65, Alto >= 0.65).
    """
    # Nivel Bajo
    etq_b, col_b, bg_b = RiskPredictorService.categorizar_nivel_alerta(0.0)
    assert etq_b == "Bajo"
    assert col_b == "#047857"
    assert bg_b == "#ECFDF5"

    etq_b2, _, _ = RiskPredictorService.categorizar_nivel_alerta(0.3499)
    assert etq_b2 == "Bajo"

    # Nivel Moderado
    etq_m, col_m, bg_m = RiskPredictorService.categorizar_nivel_alerta(0.35)
    assert etq_m == "Moderado"
    assert col_m == "#B45309"
    assert bg_m == "#FEF3C7"

    etq_m2, _, _ = RiskPredictorService.categorizar_nivel_alerta(0.6499)
    assert etq_m2 == "Moderado"

    # Nivel Alto
    etq_a, col_a, bg_a = RiskPredictorService.categorizar_nivel_alerta(0.65)
    assert etq_a == "Alto"
    assert col_a == "#BE123C"
    assert bg_a == "#FFE4E6"

    etq_a2, _, _ = RiskPredictorService.categorizar_nivel_alerta(1.0)
    assert etq_a2 == "Alto"

    # Acotamiento estricto ante valores fuera de rango [0.0, 1.0]
    etq_neg, _, _ = RiskPredictorService.categorizar_nivel_alerta(-0.5)
    assert etq_neg == "Bajo"

    etq_sup, _, _ = RiskPredictorService.categorizar_nivel_alerta(1.5)
    assert etq_sup == "Alto"


def test_entrenar_detector_anomalias_aislamiento(sample_ml_training_dataframe: pd.DataFrame):
    """
    HU-28 / Criterio 1: Valida el ajuste del detector no supervisado IsolationForest.
    """
    from sklearn.ensemble import IsolationForest

    service = RiskPredictorService()
    service.entrenar_detector_anomalias(sample_ml_training_dataframe)

    assert service.detector_anomalias is not None
    assert isinstance(service.detector_anomalias, IsolationForest)

    # Tolerancia ante muestras insuficientes
    service.entrenar_detector_anomalias(None)
    assert service.detector_anomalias is None


def test_calcular_score_hibrido_lote_ordenamiento_y_acotamiento(sample_ml_training_dataframe: pd.DataFrame):
    """
    HU-28 / Criterios 1, 2 y 3: Valida el cálculo del score híbrido continuo [0.0, 1.0],
    la asignación de nivel de alerta y el ordenamiento descendente por severidad.
    """
    service = RiskPredictorService()
    service.entrenar(sample_ml_training_dataframe)

    df_eval = service.calcular_score_hibrido_lote(sample_ml_training_dataframe)

    assert not df_eval.empty
    assert "score_riesgo_anomalia" in df_eval.columns
    assert "nivel_alerta" in df_eval.columns

    # Todos los scores deben estar estrictamente acotados en [0.0, 1.0]
    assert (df_eval["score_riesgo_anomalia"] >= 0.0).all()
    assert (df_eval["score_riesgo_anomalia"] <= 1.0).all()

    # Niveles de alerta válidos
    assert df_eval["nivel_alerta"].isin(["Bajo", "Moderado", "Alto"]).all()

    # Priorización: orden descendente de mayor a menor anomalía
    scores = df_eval["score_riesgo_anomalia"].tolist()
    assert scores == sorted(scores, reverse=True)


def test_calcular_score_hibrido_lote_vacio_o_none():
    """
    HU-28: Valida robustez ante DataFrames vacíos o nulos en evaluación por lotes.
    """
    service = RiskPredictorService()
    assert service.calcular_score_hibrido_lote(None).empty
    assert service.calcular_score_hibrido_lote(pd.DataFrame()).empty


def test_generar_grafica_dispersion_anomalias_figura_valida(sample_ml_training_dataframe: pd.DataFrame):
    """
    HU-28 / Criterio 3: Valida la construcción del gráfico de dispersión (Scatter Plot)
    de anomalías coloreado por nivel de alerta.
    """
    service = RiskPredictorService()
    service.entrenar(sample_ml_training_dataframe)
    df_eval = service.calcular_score_hibrido_lote(sample_ml_training_dataframe)

    fig = RiskPredictorService.generar_grafica_dispersion_anomalias(df_eval, max_puntos=50)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1
    assert fig.data[0].type == "scatter"
    assert "Mapa de Dispersión de Anomalías" in fig.layout.title.text
    assert fig.layout.yaxis.type == "log"


def test_generar_grafica_dispersion_anomalias_figura_vacia():
    """
    HU-28: Valida mensaje informativo ante ausencia de datos para el gráfico de dispersión.
    """
    fig = RiskPredictorService.generar_grafica_dispersion_anomalias(pd.DataFrame())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0
    assert len(fig.layout.annotations) > 0
    assert "Sin registros evaluados" in fig.layout.annotations[0].text


def test_apptest_predictive_view_batch_prioritization_ui():
    """
    HU-28 / Criterios 2 y 3: Prueba de integración con Streamlit AppTest para
    la priorización por lotes y mapa de anomalías en la vista predictiva.
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

    # Navegar a Inteligencia Predictiva
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Inteligencia Predictiva").run()

    assert len(at.exception) == 0

    # Comprobar componentes de HU-28 en la vista
    html_predictive = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Priorización de Auditorías Preventivas (Lote Activo)" in html_predictive
    assert "Score de Anomalía Continuo" in html_predictive
    assert "Listado Priorizado para Control Preventivo" in html_predictive


# ==============================================================================
# PRUEBAS HU-29: GRÁFICAS PROBABILÍSTICAS Y CURVAS DE RIESGO
# ==============================================================================

def test_calcular_curva_proyeccion_contingencia_ic95(sample_ml_training_dataframe: pd.DataFrame):
    """
    HU-29 / Criterio 1: Valida el cálculo de la curva de sobrecosto esperado
    e intervalo de confianza (IC 95%) acotado a valores no negativos.
    """
    service = RiskPredictorService()
    service.entrenar(sample_ml_training_dataframe)

    df_proj = service.calcular_curva_proyeccion_contingencia(
        departamento="Antioquia",
        modalidad="Contratación directa",
        tipo_contrato="Obra pública",
        es_pyme=False,
        cuantia_inicial=200_000_000.0
    )

    columnas_esperadas = ["plazo_dias", "probabilidad_pct", "sobrecosto_esperado", "ic_inferior", "ic_superior"]
    for col in columnas_esperadas:
        assert col in df_proj.columns

    assert len(df_proj) == 12  # Rango de 30 a 360 días (paso 30)
    assert (df_proj["ic_inferior"] >= 0.0).all()  # No negatividad
    assert (df_proj["ic_inferior"] <= df_proj["sobrecosto_esperado"]).all()
    assert (df_proj["sobrecosto_esperado"] <= df_proj["ic_superior"]).all()


def test_generar_grafica_proyeccion_ic():
    """
    HU-29 / Criterio 1: Valida la construcción de la figura Plotly con banda de incertidumbre y línea central.
    """
    service = RiskPredictorService()
    fig = service.generar_grafica_proyeccion_ic(
        departamento="Valle del Cauca",
        modalidad="Licitación pública",
        tipo_contrato="Prestación de servicios",
        es_pyme=True,
        cuantia_inicial=150_000_000.0,
        es_oscuro=False
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # Banda IC 95% + Línea central
    assert fig.data[0].fill == "toself"
    assert "Intervalo de Confianza (95%)" in fig.data[0].name
    assert "Sobrecosto Esperado" in fig.data[1].name
    assert "Proyección de Sobrecosto Esperado" in fig.layout.title.text


def test_generar_grafica_escenarios_contingencia():
    """
    HU-29 / Criterio 2: Valida la distribución probabilística en 3 escenarios operativos
    y cálculo de reservas recomendadas.
    """
    fig = RiskPredictorService.generar_grafica_escenarios_contingencia(
        score_riesgo=0.45,
        cuantia_inicial=300_000_000.0,
        es_oscuro=False
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "bar"
    assert len(fig.data[0].x) == 3
    assert "Ejecución Normal (0%)" in fig.data[0].x
    assert "Adición Moderada (5% - 15%)" in fig.data[0].x
    assert "Adición Crítica (> 20%)" in fig.data[0].x

    # Probabilidades coherentes
    probs = fig.data[0].y
    assert pytest.approx(sum(probs), rel=1e-1) == 100.0


def test_generar_grafica_importancia_variables(sample_ml_training_dataframe: pd.DataFrame):
    """
    HU-29 / Criterio 3: Valida la extracción de la importancia relativa de variables (Feature Importance)
    tanto con modelo entrenado como con pesos base de respaldo.
    """
    # 1. Sin entrenar (pesos heurísticos de respaldo)
    svc_base = RiskPredictorService()
    fig_base = svc_base.generar_grafica_importancia_variables()
    assert isinstance(fig_base, go.Figure)
    assert len(fig_base.data) == 1
    assert fig_base.data[0].orientation == "h"
    assert len(fig_base.data[0].y) == 6

    # 2. Con modelo entrenado
    svc_ent = RiskPredictorService()
    svc_ent.entrenar(sample_ml_training_dataframe)
    fig_ent = svc_ent.generar_grafica_importancia_variables()
    assert isinstance(fig_ent, go.Figure)
    assert len(fig_ent.data) == 1
    assert fig_ent.data[0].orientation == "h"
    assert "Factores Determinantes del Riesgo" in fig_ent.layout.title.text


def test_apptest_predictive_view_probabilistic_charts_ui():
    """
    HU-29 / Criterio 4: Prueba de integración con Streamlit AppTest para
    las curvas probabilísticas, distribución de contingencia y explicabilidad en la vista predictiva.
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

    # Navegar a Inteligencia Predictiva
    if at.sidebar.radio:
        at.sidebar.radio[0].set_value("Inteligencia Predictiva").run()

    assert len(at.exception) == 0

    # Comprobar componentes de HU-29 en la vista
    html_predictive = " ".join([m.value for m in at.markdown if hasattr(m, "value")])
    assert "Proyección de Sobrecosto e Intervalo de Confianza" in html_predictive
    assert "Banda de Confianza 95%" in html_predictive
    assert "Distribución de Escenarios de Contingencia" in html_predictive
    assert "Reserva de Tesorería" in html_predictive
    assert "Factores Determinantes del Riesgo Presupuestal" in html_predictive
    assert "Explicabilidad del Modelo" in html_predictive


