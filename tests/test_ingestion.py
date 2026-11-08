"""
Suite de Pruebas Automatizadas de Ingesta Masiva y Patrón Singleton
Historia de Usuario: HU-04 (Ingesta y Lectura de Datos Masivos)
Caso de Prueba de Aceptación: PA-ALFA-002
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from pathlib import Path
import pytest
from src.database.data_repository import DataRepositorySingleton


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reinicia la instancia del singleton antes de cada prueba para garantizar aislamiento."""
    DataRepositorySingleton.reset_instance()
    yield
    DataRepositorySingleton.reset_instance()


def test_singleton_instancia_unica():
    """
    HU-04 / Criterio 1: Verifica que múltiples llamadas a DataRepositorySingleton
    retornen exactamente la misma referencia en memoria (Patrón Creacional Singleton).
    """
    repo1 = DataRepositorySingleton()
    repo2 = DataRepositorySingleton()
    repo3 = DataRepositorySingleton.get_instance()

    assert repo1 is repo2, "repo1 y repo2 deben ser la misma instancia en memoria"
    assert repo2 is repo3, "La instancia obtenida por get_instance debe coincidir"
    assert id(repo1) == id(repo2) == id(repo3)


def test_carga_datos_metricas():
    """
    HU-04 / Criterio 2: Valida que al cargar la fuente se obtenga un DataFrame no vacío
    y que las métricas operativas se calculen adecuadamente.
    """
    repo = DataRepositorySingleton()
    df, metricas = repo.cargar_fuente()

    assert df is not None, "El DataFrame no debe ser None"
    assert len(df) > 0, "El DataFrame no debe estar vacío"
    assert metricas["total_registros_leidos"] == len(df)
    assert metricas["total_registros_leidos"] == 10000, "Deben haberse leído 10.000 registros de la muestra"
    assert metricas["columnas_detectadas"] > 0
    assert metricas["tamano_memoria_mb"] > 0.0
    assert metricas["tiempo_segundos"] > 0.0
    assert metricas["estado_singleton"] == "ACTIVA (En Memoria)"
    assert repo.esta_cargado() is True


def test_tiempo_carga_limite():
    """
    HU-04 / Regla 4: Rendimiento y Eficiencia.
    Asegura que la ingesta y puesta en memoria de 10.000 registros tome menos de 3.0 segundos.
    """
    repo = DataRepositorySingleton()
    _, metricas = repo.cargar_fuente()

    assert metricas["tiempo_segundos"] < 3.0, (
        f"El tiempo de carga ({metricas['tiempo_segundos']} s) excedió el límite de 3.0 segundos"
    )


def test_persistencia_en_memoria_entre_llamadas():
    """
    HU-04: Verifica que una vez cargados los datos, cualquier otro acceso
    al repositorio Singleton tenga acceso inmediato al DataFrame sin releer de disco.
    """
    repo1 = DataRepositorySingleton()
    repo1.cargar_fuente()

    # Segunda llamada sin ejecutar cargar_fuente
    repo2 = DataRepositorySingleton()
    df_persistido = repo2.obtener_dataframe()
    metricas = repo2.obtener_metricas()

    assert df_persistido is not None
    assert len(df_persistido) == 10000
    assert metricas["estado_singleton"] == "ACTIVA (En Memoria)"
    assert repo2.esta_cargado() is True


def test_sincronizacion_mongo_repositorio():
    """
    HU-04: Valida la conectividad del repositorio con MongoDB mediante MongoConnectionSingleton.
    """
    repo = DataRepositorySingleton()
    resultado = repo.sincronizar_con_mongo()

    assert "contratos_en_mongo" in resultado
    assert "sincronizado" in resultado
    assert isinstance(resultado["contratos_en_mongo"], int)
