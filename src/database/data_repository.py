"""
Repositorio Central de Datos aplicando el Patrón Creacional Singleton
Historia de Usuario: HU-04 (Ingesta y Lectura de Datos Masivos)
Caso de Prueba de Aceptación: PA-ALFA-002
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Any
import pandas as pd
import streamlit as st
from src.database.connection import MongoConnectionSingleton


class DataRepositorySingleton:
    """
    Repositorio centralizado de datos bajo el Patrón Singleton.
    Mantiene una única instancia en memoria para la ingesta y acceso al dataset,
    evitando lecturas repetitivas a disco y saturación de memoria RAM.
    """
    _instance: DataRepositorySingleton | None = None
    _df: pd.DataFrame | None = None
    _metricas: dict[str, Any] = {}
    _origen_actual: str = ""

    def __new__(cls) -> DataRepositorySingleton:
        if cls._instance is None:
            cls._instance = super(DataRepositorySingleton, cls).__new__(cls)
            cls._df = None
            cls._metricas = {
                "total_registros_leidos": 0,
                "columnas_detectadas": 0,
                "tamano_memoria_mb": 0.0,
                "tiempo_segundos": 0.0,
                "origen": "Ninguno",
                "estado_singleton": "INACTIVO"
            }
            cls._origen_actual = ""
        return cls._instance

    @classmethod
    def get_instance(cls) -> DataRepositorySingleton:
        """Retorna la instancia Singleton activa."""
        if cls._instance is None:
            cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reinicia la instancia única (utilizado principalmente para aislamiento en pruebas)."""
        cls._instance = None
        cls._df = None
        cls._metricas = {
            "total_registros_leidos": 0,
            "columnas_detectadas": 0,
            "tamano_memoria_mb": 0.0,
            "tiempo_segundos": 0.0,
            "origen": "Ninguno",
            "estado_singleton": "INACTIVO"
        }
        cls._origen_actual = ""

    def cargar_fuente(self, origen: Any = None) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Carga e ingesta la fuente de datos midiendo tiempos y memoria ocupada.

        Args:
            origen: Ruta str/Path, UploadedFile de Streamlit, o None para usar ruta por defecto.

        Returns:
            tuple[pd.DataFrame, dict]: DataFrame cargado y métricas operativas de la ingesta.
        """
        inicio = time.perf_counter()

        # 1. Resolución de la fuente de datos
        if origen is None:
            ruta_posible = Path("data") / "raw" / "secop muestra 10k 2022.csv"
            if not ruta_posible.exists():
                ruta_posible = Path("secop muestra 10k 2022.csv")
            if not ruta_posible.exists():
                raise FileNotFoundError(f"No se encontró el dataset en '{ruta_posible.resolve()}'")
            fuente = ruta_posible
            nombre_origen = ruta_posible.name
        elif isinstance(origen, (str, Path)):
            ruta = Path(origen)
            if not ruta.exists():
                ruta_raw = Path("data") / "raw" / ruta.name
                if ruta_raw.exists():
                    ruta = ruta_raw
                else:
                    raise FileNotFoundError(f"No se encontró el archivo: {ruta.resolve()}")
            fuente = ruta
            nombre_origen = ruta.name
        else:
            fuente = origen
            nombre_origen = getattr(origen, "name", "dataset_interactivo.csv")

        # 2. Lectura vectorizada de alto rendimiento con Pandas
        df = pd.read_csv(fuente, low_memory=False)

        # 3. Cálculo de métricas operativas de ingesta
        tiempo_lectura = round(time.perf_counter() - inicio, 3)
        memoria_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)

        metricas = {
            "total_registros_leidos": len(df),
            "columnas_detectadas": len(df.columns),
            "tamano_memoria_mb": memoria_mb,
            "tiempo_segundos": tiempo_lectura,
            "origen": nombre_origen,
            "estado_singleton": "ACTIVA (En Memoria)"
        }

        # 4. Almacenamiento en la instancia Singleton
        self._df = df
        self._metricas = metricas
        self._origen_actual = nombre_origen

        return df, metricas

    def obtener_dataframe(self) -> pd.DataFrame | None:
        """Retorna el DataFrame persistido en la instancia Singleton."""
        return self._df

    def obtener_metricas(self) -> dict[str, Any]:
        """Retorna las métricas operativas de la última ingesta."""
        return self._metricas

    def esta_cargado(self) -> bool:
        """Indica si el dataset ya se encuentra cargado en memoria."""
        return self._df is not None and not self._df.empty

    def sincronizar_con_mongo(self, limite: int | None = None) -> dict[str, Any]:
        """
        Verifica y sincroniza la disponibilidad de los contratos en MongoDB.
        Reutiliza MongoConnectionSingleton para no saturar sockets.
        """
        try:
            col = MongoConnectionSingleton.get_collection("contratos")
            total_mongo = col.count_documents({})
            return {
                "contratos_en_mongo": total_mongo,
                "sincronizado": total_mongo > 0,
                "coleccion": "contratos",
                "estado": "Conectado"
            }
        except Exception as e:
            return {
                "contratos_en_mongo": 0,
                "sincronizado": False,
                "coleccion": "contratos",
                "estado": f"Error: {e}"
            }


@st.cache_resource(show_spinner=False)
def get_data_repository() -> DataRepositorySingleton:
    """
    Función cacheada para Streamlit que garantiza una única instancia en memoria
    persistente a través de los ciclos de recarga de la aplicación.
    """
    return DataRepositorySingleton.get_instance()
