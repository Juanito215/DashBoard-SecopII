"""
Suite de Pruebas Automatizadas para MultiDatasetManager y Excepciones de Ingesta
Cubre: Ingesta Dual CSV/Parquet, Criptografía SHA-256 (8 MB), Detección de Duplicados,
Consistencia de Formato, Límite Máximo de 10 Archivos, Consolidación y Reseteo.
SECOP Analytics | Universidad del Valle - Sede Tuluá
"""
import io
import pytest
import pandas as pd
import numpy as np

from src.database.dataset_manager import MultiDatasetManager, get_dataset_manager
from src.database.data_repository import DataRepositorySingleton
from src.utils.exceptions import (
    SecopAnalyticsError,
    DatasetDuplicadoError,
    FormatoInconsistenteError,
    LimiteDatasetsExcedidoError,
)


@pytest.fixture(autouse=True)
def aislar_gestor():
    """Aísla la instancia del gestor de datasets y del repositorio antes y después de cada prueba."""
    MultiDatasetManager.reset_instance()
    DataRepositorySingleton.reset_instance()
    yield
    MultiDatasetManager.reset_instance()
    DataRepositorySingleton.reset_instance()


def crear_buffer_csv(registros: int = 5, prefijo_id: str = "P1", anio: int = 2022) -> io.BytesIO:
    """Genera un archivo CSV en memoria con estructura válida para SECOP II."""
    df = pd.DataFrame({
        "id_contrato": [f"CO1.PCONTR.{prefijo_id}_{i}" for i in range(registros)],
        "proceso_de_compra": [f"PROC_{prefijo_id}_{i}" for i in range(registros)],
        "valor_del_contrato": [1000000.0 * (i + 1) for i in range(registros)],
        "valor_adiciones": [50000.0 * i for i in range(registros)],
        "duracion_dias": [30 * (i + 1) for i in range(registros)],
        "departamento": ["VALLE DEL CAUCA"] * registros,
        "ciudad": ["TULUÁ"] * registros,
        "fecha_de_firma": [f"{anio}-03-15"] * registros,
        "modalidad_de_contratacion": ["CONTRATACIÓN DIRECTA"] * registros,
        "tipo_de_contrato": ["PRESTACIÓN DE SERVICIOS"] * registros,
        "estado_contrato": ["EN EJECUCIÓN"] * registros,
        "codigo_de_categoria_principal": ["V1.80101500"] * registros,
        "nombre_entidad": ["ALCALDÍA MUNICIPAL DE TULUÁ"] * registros,
        "nit_entidad": ["891900441"] * registros,
        "proveedor": ["CONSULTORES DEL VALLE SAS"] * registros,
        "documento_proveedor": ["900123456"] * registros,
        "es_pyme": ["Sí"] * registros,
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    buf.name = f"secop_{anio}_{prefijo_id}.csv"
    return buf


def crear_buffer_parquet(registros: int = 5, prefijo_id: str = "PQ1", anio: int = 2023) -> io.BytesIO:
    """Genera un archivo Parquet en memoria con motor pyarrow."""
    df = pd.DataFrame({
        "id_contrato": [f"CO1.PCONTR.{prefijo_id}_{i}" for i in range(registros)],
        "proceso_de_compra": [f"PROC_{prefijo_id}_{i}" for i in range(registros)],
        "valor_del_contrato": [2500000.0 * (i + 1) for i in range(registros)],
        "valor_adiciones": [100000.0 * i for i in range(registros)],
        "duracion_dias": [60 * (i + 1) for i in range(registros)],
        "departamento": ["ANTIOQUIA"] * registros,
        "ciudad": ["MEDELLÍN"] * registros,
        "fecha_de_firma": [f"{anio}-06-20"] * registros,
        "modalidad_de_contratacion": ["LICITACIÓN PÚBLICA"] * registros,
        "tipo_de_contrato": ["OBRA"] * registros,
        "estado_contrato": ["EN EJECUCIÓN"] * registros,
        "codigo_de_categoria_principal": ["V1.72101500"] * registros,
        "nombre_entidad": ["MUNICIPIO DE MEDELLÍN"] * registros,
        "nit_entidad": ["890905211"] * registros,
        "proveedor": ["CONSTRUCTORA ANDINA SAS"] * registros,
        "documento_proveedor": ["800987654"] * registros,
        "es_pyme": ["No"] * registros,
    })
    buf = io.BytesIO()
    df.to_parquet(buf, engine="pyarrow", index=False)
    buf.seek(0)
    buf.name = f"secop_{anio}_{prefijo_id}.parquet"
    return buf


class TestMultiDatasetManager:
    """Pruebas unitarias y de integración para MultiDatasetManager."""

    def test_singleton_get_instance_y_reset(self):
        """Verifica el comportamiento del patrón creacional Singleton y su reseteo."""
        mgr1 = MultiDatasetManager.get_instance()
        mgr2 = get_dataset_manager()
        assert mgr1 is mgr2
        assert mgr1.total_datasets() == 0

        MultiDatasetManager.reset_instance()
        mgr3 = MultiDatasetManager.get_instance()
        assert mgr3 is not mgr1

    def test_calculo_hash_sha256_bloques_8mb(self):
        """Verifica el cálculo consistente de huella criptográfica SHA-256."""
        contenido = b"DATOS_SECOP_ANALYTICS_TEST_HASH" * 1000
        buf = io.BytesIO(contenido)
        hash1 = MultiDatasetManager.calcular_hash_sha256(buf, chunk_size=1024)
        buf.seek(0)
        hash2 = MultiDatasetManager.calcular_hash_sha256(buf, chunk_size=8 * 1024 * 1024)
        assert hash1 == hash2
        assert len(hash1) == 64
        # Comprobar que el puntero se preserva
        assert buf.tell() == 0

    def test_ingesta_exitosa_csv_individual(self):
        """Verifica la carga, normalización y cálculo de métricas de un dataset CSV."""
        mgr = MultiDatasetManager.get_instance()
        buf = crear_buffer_csv(registros=8, prefijo_id="L1", anio=2021)

        df_consolidado, meta = mgr.cargar_archivo(buf)
        assert df_consolidado is not None
        assert len(df_consolidado) == 8
        assert meta["formato"] == "csv"
        assert meta["registros"] == 8
        assert mgr.obtener_formato_activo() == "csv"
        assert mgr.total_datasets() == 1

        # Verificación de integración con DataRepositorySingleton
        repo = DataRepositorySingleton.get_instance()
        assert repo.esta_cargado()
        assert len(repo.obtener_dataframe()) == 8

    def test_ingesta_exitosa_parquet_pyarrow(self):
        """Verifica la carga y procesamiento de un dataset en formato Parquet."""
        mgr = MultiDatasetManager.get_instance()
        buf = crear_buffer_parquet(registros=6, prefijo_id="PQ_TEST", anio=2023)

        df_consolidado, meta = mgr.cargar_archivo(buf)
        assert df_consolidado is not None
        assert len(df_consolidado) == 6
        assert meta["formato"] == "parquet"
        assert mgr.obtener_formato_activo() == "parquet"

    def test_excepcion_dataset_duplicado_por_nombre(self):
        """Lanza DatasetDuplicadoError si se intenta cargar un archivo con el mismo nombre."""
        mgr = MultiDatasetManager.get_instance()
        buf1 = crear_buffer_csv(registros=4, prefijo_id="D1", anio=2022)
        buf1.name = "lote_anual_2022.csv"
        mgr.cargar_archivo(buf1)

        # Segundo buffer con diferente contenido pero mismo nombre
        buf2 = crear_buffer_csv(registros=7, prefijo_id="D2", anio=2022)
        buf2.name = "lote_anual_2022.csv"

        with pytest.raises(DatasetDuplicadoError) as exc_info:
            mgr.cargar_archivo(buf2)

        assert "lote_anual_2022.csv" in str(exc_info.value)

    def test_excepcion_dataset_duplicado_por_sha256(self):
        """Lanza DatasetDuplicadoError si se intenta cargar un archivo idéntico con diferente nombre."""
        mgr = MultiDatasetManager.get_instance()
        contenido = crear_buffer_csv(registros=5, prefijo_id="D3", anio=2022).getvalue()

        buf1 = io.BytesIO(contenido)
        buf1.name = "archivo_original.csv"
        mgr.cargar_archivo(buf1)

        buf2 = io.BytesIO(contenido)
        buf2.name = "copia_con_otro_nombre.csv"

        with pytest.raises(DatasetDuplicadoError) as exc_info:
            mgr.cargar_archivo(buf2)

        assert "copia_con_otro_nombre.csv" in str(exc_info.value)

    def test_excepcion_formato_inconsistente_csv_luego_parquet(self):
        """Lanza FormatoInconsistenteError si se intenta mezclar Parquet en un repositorio CSV."""
        mgr = MultiDatasetManager.get_instance()
        buf_csv = crear_buffer_csv(registros=3, prefijo_id="F1", anio=2022)
        mgr.cargar_archivo(buf_csv)

        buf_pq = crear_buffer_parquet(registros=3, prefijo_id="F2", anio=2023)
        with pytest.raises(FormatoInconsistenteError) as exc_info:
            mgr.cargar_archivo(buf_pq)

        assert "Inconsistencia de formato" in str(exc_info.value)
        assert exc_info.value.formato_esperado == "csv"
        assert exc_info.value.formato_recibido == "parquet"

    def test_excepcion_formato_inconsistente_parquet_luego_csv(self):
        """Lanza FormatoInconsistenteError si se intenta mezclar CSV en un repositorio Parquet."""
        mgr = MultiDatasetManager.get_instance()
        buf_pq = crear_buffer_parquet(registros=3, prefijo_id="F1", anio=2023)
        mgr.cargar_archivo(buf_pq)

        buf_csv = crear_buffer_csv(registros=3, prefijo_id="F2", anio=2022)
        with pytest.raises(FormatoInconsistenteError) as exc_info:
            mgr.cargar_archivo(buf_csv)

        assert exc_info.value.formato_esperado == "parquet"
        assert exc_info.value.formato_recibido == "csv"

    def test_excepcion_limite_maximo_10_datasets_excedido(self):
        """Lanza LimiteDatasetsExcedidoError al intentar cargar el archivo número 11."""
        mgr = MultiDatasetManager.get_instance()

        # Cargar 10 archivos distintos
        for i in range(10):
            buf = crear_buffer_csv(registros=2, prefijo_id=f"LOTE_{i}", anio=2020 + (i % 5))
            buf.name = f"lote_{i}.csv"
            mgr.cargar_archivo(buf)

        assert mgr.total_datasets() == 10

        # Intentar cargar el archivo número 11
        buf_11 = crear_buffer_csv(registros=2, prefijo_id="LOTE_11", anio=2026)
        buf_11.name = "lote_11_excedente.csv"

        with pytest.raises(LimiteDatasetsExcedidoError) as exc_info:
            mgr.cargar_archivo(buf_11)

        assert exc_info.value.total_actual == 10
        assert exc_info.value.limite_maximo == 10
        assert "Límite máximo de 10 datasets excedido" in str(exc_info.value)

    def test_consolidacion_multi_ano_y_deduplicacion_por_id_proceso(self):
        """Verifica la consolidación global de múltiples años y deduplicación por id_proceso."""
        mgr = MultiDatasetManager.get_instance()

        # Dataset 1: Contratos 2021 (4 registros)
        buf1 = crear_buffer_csv(registros=4, prefijo_id="COMUN", anio=2021)
        buf1.name = "secop_2021.csv"
        mgr.cargar_archivo(buf1)

        # Dataset 2: Contratos 2022 con 2 registros repetidos (mismo proceso_de_compra) y 2 nuevos
        # Se genera un DataFrame con 2 IDs repetidos de COMUN y 2 nuevos
        df_repetido = pd.DataFrame({
            "id_contrato": ["CO1.PCONTR.COMUN_0", "CO1.PCONTR.COMUN_1", "CO1.PCONTR.NUEVO_0", "CO1.PCONTR.NUEVO_1"],
            "proceso_de_compra": ["PROC_COMUN_0", "PROC_COMUN_1", "PROC_NUEVO_0", "PROC_NUEVO_1"],
            "valor_del_contrato": [1500000.0, 2500000.0, 3000000.0, 4000000.0],
            "valor_adiciones": [0.0, 10000.0, 20000.0, 0.0],
            "duracion_dias": [45, 90, 120, 60],
            "departamento": ["VALLE DEL CAUCA"] * 4,
            "ciudad": ["TULUÁ"] * 4,
            "fecha_de_firma": ["2022-04-10"] * 4,
            "modalidad_de_contratacion": ["CONTRATACIÓN DIRECTA"] * 4,
            "tipo_de_contrato": ["PRESTACIÓN DE SERVICIOS"] * 4,
            "estado_contrato": ["EN EJECUCIÓN"] * 4,
            "codigo_de_categoria_principal": ["V1.80101500"] * 4,
            "nombre_entidad": ["ALCALDÍA MUNICIPAL DE TULUÁ"] * 4,
            "nit_entidad": ["891900441"] * 4,
            "proveedor": ["CONSULTORES DEL VALLE SAS"] * 4,
            "documento_proveedor": ["900123456"] * 4,
            "es_pyme": ["Sí"] * 4,
        })
        buf2 = io.BytesIO()
        df_repetido.to_csv(buf2, index=False)
        buf2.seek(0)
        buf2.name = "secop_2022.csv"

        df_consolidado, _ = mgr.cargar_archivo(buf2)

        # Deberían ser 4 originales + 4 cargados - 2 duplicados = 6 registros consolidados
        assert len(df_consolidado) == 6
        assert mgr.total_datasets() == 2

    def test_optimizacion_tipos_memoria(self):
        """Verifica el casting a category, float64 e int32 para ahorro en RAM."""
        mgr = MultiDatasetManager.get_instance()
        buf = crear_buffer_csv(registros=5, prefijo_id="OPT", anio=2024)
        df_cons, _ = mgr.cargar_archivo(buf)

        assert str(df_cons["departamento"].dtype) == "category"
        assert str(df_cons["modalidad"].dtype) == "category"
        assert str(df_cons["tipo_contrato"].dtype) == "category"
        assert str(df_cons["cuantia_inicial"].dtype) == "float64"
        assert str(df_cons["cuantia_final"].dtype) == "float64"
        assert str(df_cons["plazo_ejecucion_dias"].dtype) == "int32"
        assert str(df_cons["anio_vigencia"].dtype) == "int32"

    def test_limpiar_repositorio_purga_y_resetea(self):
        """Verifica que limpiar_repositorio vacíe la memoria y permita reiniciar el formato."""
        mgr = MultiDatasetManager.get_instance()
        buf_csv = crear_buffer_csv(registros=5, prefijo_id="PURGA", anio=2022)
        mgr.cargar_archivo(buf_csv)

        assert mgr.total_datasets() == 1
        assert mgr.obtener_formato_activo() == "csv"
        assert mgr.obtener_dataframe_consolidado() is not None

        # Limpiar repositorio
        mgr.limpiar_repositorio()

        assert mgr.total_datasets() == 0
        assert mgr.obtener_formato_activo() is None
        assert mgr.obtener_dataframe_consolidado() is None

        # Ahora debe permitir cargar Parquet sin lanzar FormatoInconsistenteError
        buf_pq = crear_buffer_parquet(registros=4, prefijo_id="POST_PURGA", anio=2025)
        df_cons_pq, meta_pq = mgr.cargar_archivo(buf_pq)
        assert df_cons_pq is not None
        assert mgr.obtener_formato_activo() == "parquet"
        assert mgr.total_datasets() == 1
