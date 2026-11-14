"""
Gestor de Ingesta Multi-Dataset Corporativo (CSV y Parquet)
Soporte de consolidación multi-año, optimización columnar de memoria y validación criptográfica.
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import hashlib
import io
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import numpy as np

from src.utils.exceptions import (
    DatasetDuplicadoError,
    FormatoInconsistenteError,
    LimiteDatasetsExcedidoError,
)
from src.database.data_repository import DataRepositorySingleton
from src.etl.etl_pipeline import SecopETLPipeline


class MultiDatasetManager:
    """
    Gestor centralizado de datasets múltiples para SECOP Analytics.
    Permite la ingesta incremental de hasta 10 archivos (CSV o Parquet),
    garantizando consistencia de formato, unicidad por SHA-256 y consolidación
    con deduplicación y optimización de memoria RAM.
    """
    _instance: MultiDatasetManager | None = None
    CHUNK_SIZE: int = 8 * 1024 * 1024  # Bloques de 8 MB
    LIMITE_MAXIMO_DATASETS: int = 10

    def __new__(cls) -> MultiDatasetManager:
        if cls._instance is None:
            cls._instance = super(MultiDatasetManager, cls).__new__(cls)
            cls._instance._inicializar_estado()
        return cls._instance

    def _inicializar_estado(self) -> None:
        """Inicializa las estructuras internas de almacenamiento y metadatos."""
        self._datasets_cargados: list[dict[str, Any]] = []
        self._formato_activo: str | None = None
        self._df_consolidado: pd.DataFrame | None = None
        self._pipeline_etl = SecopETLPipeline()

    @classmethod
    def get_instance(cls) -> MultiDatasetManager:
        """Retorna la instancia Singleton activa del gestor."""
        if cls._instance is None:
            cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reinicia por completo la instancia Singleton (útil para pruebas unitarias)."""
        if cls._instance is not None:
            cls._instance._inicializar_estado()
        cls._instance = None

    @classmethod
    def calcular_hash_sha256(cls, fuente: Any, chunk_size: int | None = None) -> str:
        """
        Calcula la huella criptográfica SHA-256 de un archivo o stream en bloques de 8 MB.

        Args:
            fuente: Ruta str/Path, BytesIO, Streamlit UploadedFile o bytes.
            chunk_size: Tamaño de bloque en bytes (por defecto 8 MB).

        Returns:
            str: Hash hexadecimal SHA-256 en minúsculas.
        """
        tam_bloque = chunk_size or cls.CHUNK_SIZE
        hasher = hashlib.sha256()

        if isinstance(fuente, (str, Path)):
            ruta = Path(fuente)
            if not ruta.exists():
                ruta_raw = Path("data") / "raw" / ruta.name
                if ruta_raw.exists():
                    ruta = ruta_raw
                else:
                    raise FileNotFoundError(f"No se encontró el archivo para calcular hash: {ruta.resolve()}")
            with open(ruta, "rb") as f:
                while True:
                    bloque = f.read(tam_bloque)
                    if not bloque:
                        break
                    hasher.update(bloque)
        elif hasattr(fuente, "read"):
            posicion_inicial = fuente.tell() if hasattr(fuente, "tell") else None
            if hasattr(fuente, "seek"):
                fuente.seek(0)
            while True:
                bloque = fuente.read(tam_bloque)
                if not bloque:
                    break
                if isinstance(bloque, str):
                    bloque = bloque.encode("utf-8")
                hasher.update(bloque)
            if hasattr(fuente, "seek") and posicion_inicial is not None:
                fuente.seek(posicion_inicial)
        elif isinstance(fuente, bytes):
            hasher.update(fuente)
        elif isinstance(fuente, pd.DataFrame):
            hasher.update(fuente.to_csv(index=False).encode("utf-8"))
        else:
            raise ValueError(f"Tipo de fuente no compatible para cálculo de hash: {type(fuente)}")

        return hasher.hexdigest()

    @staticmethod
    def detectar_formato(fuente: Any, nombre_sugerido: str | None = None) -> str:
        """
        Detecta si el archivo es CSV o Parquet a partir de su nombre o extensión.

        Returns:
            str: 'csv' o 'parquet'
        """
        nombre = nombre_sugerido or getattr(fuente, "name", None) or str(fuente)
        nombre_lower = str(nombre).lower()
        if nombre_lower.endswith(".parquet") or nombre_lower.endswith(".pq"):
            return "parquet"
        elif nombre_lower.endswith(".csv"):
            return "csv"
        # Detección por inspección si es necesario
        return "csv"

    def validar_adicion_dataset(self, nombre_archivo: str, hash_sha256: str, formato: str) -> None:
        """
        Valida las tres reglas de negocio antes de incorporar un nuevo archivo:
        1. Límite estricto de 10 datasets.
        2. Consistencia de formato (todos CSV o todos Parquet).
        3. No duplicidad por nombre ni por huella SHA-256.
        """
        # 1. Regla: Límite máximo de 10 datasets
        if len(self._datasets_cargados) >= self.LIMITE_MAXIMO_DATASETS:
            raise LimiteDatasetsExcedidoError(
                total_actual=len(self._datasets_cargados),
                limite_maximo=self.LIMITE_MAXIMO_DATASETS
            )

        # 2. Regla: Formato consistente
        if self._formato_activo is not None and self._formato_activo != formato:
            raise FormatoInconsistenteError(
                formato_esperado=self._formato_activo,
                formato_recibido=formato
            )

        # 3. Regla: No duplicidad por nombre o por hash SHA-256
        for ds in self._datasets_cargados:
            if ds["nombre"] == nombre_archivo or ds["hash_sha256"] == hash_sha256:
                raise DatasetDuplicadoError(
                    nombre_archivo=nombre_archivo,
                    hash_sha256=hash_sha256
                )

    def leer_archivo(self, fuente: Any, formato: str) -> pd.DataFrame:
        """
        Lee el archivo utilizando el motor vectorizado correspondiente:
        pyarrow para Parquet, y low_memory=False para CSV.
        """
        if hasattr(fuente, "seek"):
            fuente.seek(0)

        if formato == "parquet":
            if isinstance(fuente, (str, Path)):
                ruta = Path(fuente)
                if not ruta.exists():
                    ruta_raw = Path("data") / "raw" / ruta.name
                    if ruta_raw.exists():
                        ruta = ruta_raw
                df = pd.read_parquet(ruta, engine="pyarrow")
            else:
                df = pd.read_parquet(fuente, engine="pyarrow")
        else:
            if isinstance(fuente, (str, Path)):
                ruta = Path(fuente)
                if not ruta.exists():
                    ruta_raw = Path("data") / "raw" / ruta.name
                    if ruta_raw.exists():
                        ruta = ruta_raw
                df = pd.read_csv(ruta, low_memory=False)
            else:
                df = pd.read_csv(fuente, low_memory=False)

        return df

    def normalizar_esquema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza el esquema del DataFrame al catálogo canónico del sistema
        y aplica transformaciones y feature engineering esenciales.
        """
        # Mapeo canónico
        df_can = self._pipeline_etl.extraer_csv(df)
        df_proc, _, _ = self._pipeline_etl.transformar_datos(df_can)

        # Si viene columna id_proceso o proceso_de_compra, asegurar id_proceso
        if "id_proceso" not in df_proc.columns:
            if "codigo_proceso" in df_proc.columns and not df_proc["codigo_proceso"].empty:
                df_proc["id_proceso"] = df_proc["codigo_proceso"]
            elif "id_contrato" in df_proc.columns:
                df_proc["id_proceso"] = df_proc["id_contrato"]
            else:
                df_proc["id_proceso"] = [f"PROC-{i+1}" for i in range(len(df_proc))]

        return df_proc

    @staticmethod
    def optimizar_tipos_memoria(df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimiza el consumo de memoria RAM aplicando tipos de datos compactos:
        - category para dimensiones de baja cardinalidad
        - float64 para cuantías y valores continuos
        - int32 para plazos, años, meses y trimestres
        """
        df_opt = df.copy()

        # Columnas categóricas
        columnas_categoricas = [
            "departamento", "municipio", "modalidad", "tipo_contrato",
            "estado", "orden_entidad", "sector"
        ]
        for col in columnas_categoricas:
            if col in df_opt.columns:
                df_opt[col] = df_opt[col].astype("category")

        # Columnas float64
        columnas_float = [
            "cuantia_inicial", "valor_adiciones", "cuantia_final",
            "tasa_gasto_diario", "score_riesgo_anomalia"
        ]
        for col in columnas_float:
            if col in df_opt.columns:
                df_opt[col] = pd.to_numeric(df_opt[col], errors="coerce").fillna(0.0).astype("float64")

        # Columnas int32
        columnas_int = [
            "plazo_ejecucion_dias", "anio_vigencia", "mes_vigencia", "trimestre"
        ]
        for col in columnas_int:
            if col in df_opt.columns:
                df_opt[col] = pd.to_numeric(df_opt[col], errors="coerce").fillna(0).astype("int32")

        return df_opt

    def cargar_archivo(
        self,
        fuente: Any,
        nombre_sugerido: str | None = None
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Carga, valida e incorpora un archivo individual al repositorio multi-dataset.

        Args:
            fuente: Ruta, BytesIO o UploadedFile.
            nombre_sugerido: Nombre opcional para el archivo.

        Returns:
            tuple[pd.DataFrame, dict]: DataFrame consolidado resultante y metadatos del lote.
        """
        inicio = time.perf_counter()

        # Determinar nombre
        if nombre_sugerido:
            nombre = nombre_sugerido
        elif hasattr(fuente, "name"):
            nombre = fuente.name
        elif isinstance(fuente, (str, Path)):
            nombre = Path(fuente).name
        else:
            nombre = f"dataset_{len(self._datasets_cargados) + 1}.csv"

        # Detectar formato y calcular hash
        formato = self.detectar_formato(fuente, nombre)
        hash_sha256 = self.calcular_hash_sha256(fuente)

        # Validar reglas de negocio (Lanza excepciones de dominio si falla)
        self.validar_adicion_dataset(nombre, hash_sha256, formato)

        # Leer archivo con motor vectorizado
        df_raw = self.leer_archivo(fuente, formato)

        # Normalizar esquema e ingeniería de variables
        df_norm = self.normalizar_esquema(df_raw)

        # Calcular métricas del archivo individual
        tiempo_carga = round(time.perf_counter() - inicio, 3)
        memoria_mb = round(df_norm.memory_usage(deep=True).sum() / (1024 * 1024), 2)

        meta = {
            "nombre": nombre,
            "formato": formato,
            "hash_sha256": hash_sha256,
            "registros": len(df_norm),
            "columnas": len(df_norm.columns),
            "memoria_mb": memoria_mb,
            "tiempo_segundos": tiempo_carga,
            "df": df_norm
        }

        # Fijar formato activo si es el primer dataset
        if self._formato_activo is None:
            self._formato_activo = formato

        self._datasets_cargados.append(meta)

        # Consolidar todos los datasets
        self._consolidar()

        return self._df_consolidado, meta

    def cargar_multiples_archivos(
        self,
        archivos: list[Any]
    ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        """
        Carga una lista de archivos secuencialmente.

        Args:
            archivos: Lista de rutas, BytesIO o UploadedFiles.

        Returns:
            tuple[pd.DataFrame, list[dict]]: DataFrame consolidado y lista de metadatos cargados.
        """
        metadatos_lote = []
        for arch in archivos:
            _, meta = self.cargar_archivo(arch)
            metadatos_lote.append(meta)

        return self._df_consolidado, metadatos_lote

    def _consolidar(self) -> None:
        """
        Consolida todos los datasets cargados en un único DataFrame global,
        aplicando concatenación, deduplicación por id_proceso y optimización de tipos.
        """
        if not self._datasets_cargados:
            self._df_consolidado = None
            return

        lista_dfs = [d["df"] for d in self._datasets_cargados]
        if len(lista_dfs) == 1:
            df_concat = lista_dfs[0].copy()
        else:
            df_concat = pd.concat(lista_dfs, ignore_index=True)

        # Deduplicación por id_proceso o id_contrato
        col_dedup = None
        if "id_proceso" in df_concat.columns and df_concat["id_proceso"].notna().any():
            col_dedup = "id_proceso"
        elif "id_contrato" in df_concat.columns:
            col_dedup = "id_contrato"

        if col_dedup:
            df_concat = df_concat.drop_duplicates(subset=[col_dedup], keep="last").reset_index(drop=True)

        # Optimización de tipos de memoria
        self._df_consolidado = self.optimizar_tipos_memoria(df_concat)

        # Actualizar DataRepositorySingleton para que toda la app opere sobre el consolidado
        repo = DataRepositorySingleton.get_instance()
        repo._df = self._df_consolidado
        total_memoria = round(self._df_consolidado.memory_usage(deep=True).sum() / (1024 * 1024), 2)
        repo._metricas = {
            "total_registros_leidos": len(self._df_consolidado),
            "columnas_detectadas": len(self._df_consolidado.columns),
            "tamano_memoria_mb": total_memoria,
            "tiempo_segundos": sum(d.get("tiempo_segundos", 0.0) for d in self._datasets_cargados),
            "origen": f"Consolidado Multi-Dataset ({len(self._datasets_cargados)} archivos)",
            "estado_singleton": "ACTIVA (Consolidado Multi-Dataset)"
        }
        repo._origen_actual = f"Consolidado ({len(self._datasets_cargados)} lotes)"

    def limpiar_repositorio(self) -> None:
        """
        Limpia y purga por completo el repositorio activo en memoria RAM,
        eliminando todos los datasets, desbloqueando el formato y reseteando el repositorio central.
        """
        self._inicializar_estado()
        repo = DataRepositorySingleton.get_instance()
        repo.reset_instance()

    def obtener_dataframe_consolidado(self) -> pd.DataFrame | None:
        """Retorna el DataFrame consolidado de todos los datasets activos."""
        return self._df_consolidado

    def obtener_datasets(self) -> list[dict[str, Any]]:
        """Retorna la lista de metadatos de los datasets cargados."""
        return [
            {
                "nombre": d["nombre"],
                "formato": d["formato"],
                "hash_sha256": d["hash_sha256"],
                "registros": d["registros"],
                "columnas": d["columnas"],
                "memoria_mb": d["memoria_mb"],
                "tiempo_segundos": d.get("tiempo_segundos", 0.0)
            }
            for d in self._datasets_cargados
        ]

    def obtener_formato_activo(self) -> str | None:
        """Retorna el formato activo ('csv' o 'parquet') o None si no hay archivos cargados."""
        return self._formato_activo

    def total_datasets(self) -> int:
        """Retorna la cantidad de datasets cargados actualmente."""
        return len(self._datasets_cargados)

    def obtener_metricas_consolidadas(self) -> dict[str, Any]:
        """Retorna métricas ejecutivas de todo el repositorio multi-dataset consolidado."""
        if self._df_consolidado is None or self._df_consolidado.empty:
            return {
                "total_archivos": 0,
                "formato_activo": "Sin Asignar",
                "total_registros": 0,
                "total_columnas": 0,
                "memoria_total_mb": 0.0
            }

        mem_mb = round(self._df_consolidado.memory_usage(deep=True).sum() / (1024 * 1024), 2)
        return {
            "total_archivos": len(self._datasets_cargados),
            "formato_activo": (self._formato_activo or "Sin Asignar").upper(),
            "total_registros": len(self._df_consolidado),
            "total_columnas": len(self._df_consolidado.columns),
            "memoria_total_mb": mem_mb
        }


def get_dataset_manager() -> MultiDatasetManager:
    """Helper funcional para obtener el Singleton de MultiDatasetManager."""
    return MultiDatasetManager.get_instance()
