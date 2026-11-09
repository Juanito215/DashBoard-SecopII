"""
Submódulo de Calidad y Saneamiento de Datos (Data Cleansing)
Historia de Usuario: HU-05 (Depuración de Inconsistencias, Duplicados y Nulos)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import re
from typing import Any
import numpy as np
import pandas as pd


class DataCleaner:
    """
    Gestor de Calidad de Datos para el saneamiento, deduplicación e imputación
    de contratos públicos de SECOP II.
    Implementa transformaciones vectorizadas e inmutables (retornando nuevas copias).
    """

    PATRONES_NULOS = {
        "", "NAN", "NONE", "NULL", "N/A", "NA", "UNDEFINED",
        "NO DEFINIDO", "<NA>", "NO DISPONIBLE", "SIN REGISTRO"
    }

    @staticmethod
    def _limpiar_monto_a_float(serie: pd.Series) -> pd.Series:
        """
        Convierte una serie monetaria a float64 continuo en Pesos Colombianos (COP).
        Limpia símbolos monetarios, espacios y resuelve separadores decimales mixtos.
        """
        if pd.api.types.is_numeric_dtype(serie):
            return pd.to_numeric(serie, errors="coerce").astype(float)

        def _parse_monto(val: Any) -> float:
            if pd.isna(val) or val is None:
                return np.nan
            texto = str(val).strip().replace("$", "").replace("COP", "").replace("cop", "").strip()
            if not texto or texto.upper() in DataCleaner.PATRONES_NULOS:
                return np.nan

            # Manejo de formatos con comas y puntos mixtos
            if "." in texto and "," in texto:
                if texto.rfind(",") > texto.rfind("."):
                    # Formato latino/europeo: 1.000.000,50 -> 1000000.50
                    texto = texto.replace(".", "").replace(",", ".")
                else:
                    # Formato anglosajón: 1,000,000.50 -> 1000000.50
                    texto = texto.replace(",", "")
            elif "," in texto:
                partes = texto.split(",")
                if len(partes) == 2 and len(partes[1]) in [1, 2]:
                    texto = partes[0] + "." + partes[1]
                else:
                    texto = texto.replace(",", "")

            try:
                num = float(texto)
                return num
            except ValueError:
                return np.nan

        return serie.apply(_parse_monto).astype(float)

    @classmethod
    def eliminar_duplicados(
        cls, df: pd.DataFrame, col_id: str = "id_contrato"
    ) -> tuple[pd.DataFrame, int]:
        """
        Criterio 1: Identifica y remueve registros redundantes basándose en la clave única.

        Args:
            df: DataFrame a deduplicar.
            col_id: Columna identificadora única del contrato.

        Returns:
            tuple[pd.DataFrame, int]: DataFrame sin duplicados y cantidad de duplicados removidos.
        """
        if col_id not in df.columns:
            return df.copy(), 0

        total_inicial = len(df)
        df_dedup = df.drop_duplicates(subset=[col_id], keep="first").copy()
        duplicados_eliminados = total_inicial - len(df_dedup)

        return df_dedup, duplicados_eliminados

    @classmethod
    def filtrar_cuantias_validas(
        cls, df: pd.DataFrame, col_cuantia: str = "cuantia_inicial"
    ) -> tuple[pd.DataFrame, int]:
        """
        Criterio 2: Descarta registros con cuantías corruptas, nulas o menores/iguales a cero.

        Args:
            df: DataFrame a depurar.
            col_cuantia: Nombre de la columna monetaria base.

        Returns:
            tuple[pd.DataFrame, int]: DataFrame depurado y cantidad de registros descartados.
        """
        if col_cuantia not in df.columns:
            return df.copy(), 0

        total_inicial = len(df)
        df_copia = df.copy()

        # Casteo y limpieza monetaria
        df_copia[col_cuantia] = cls._limpiar_monto_a_float(df_copia[col_cuantia])

        # Filtrado de cuantías estrictamente positivas (> 0) y no nulas
        mascara_valida = df_copia[col_cuantia].notna() & (df_copia[col_cuantia] > 0)
        df_filtrado = df_copia[mascara_valida].copy()

        descartados = total_inicial - len(df_filtrado)
        return df_filtrado, descartados

    @classmethod
    def normalizar_textos_y_nulos(
        cls,
        df: pd.DataFrame,
        columnas_texto: list[str] | None = None,
        valor_reemplazo: str = "NO REGISTRA"
    ) -> tuple[pd.DataFrame, int]:
        """
        Criterio 3: Homogeneiza mayúsculas, elimina espacios redundantes y reemplaza
        patrones de ausencia por 'NO REGISTRA'.

        Args:
            df: DataFrame a normalizar.
            columnas_texto: Lista de columnas textuales a procesar. Si es None, toma las de tipo object/string.
            valor_reemplazo: Cadena por defecto para celdas nulas o vacías.

        Returns:
            tuple[pd.DataFrame, int]: DataFrame normalizado y total de celdas imputadas.
        """
        df_norm = df.copy()
        if columnas_texto is None:
            columnas_texto = [
                col for col in df_norm.columns
                if pd.api.types.is_string_dtype(df_norm[col]) or pd.api.types.is_object_dtype(df_norm[col])
            ]

        celdas_imputadas = 0

        for col in columnas_texto:
            if col not in df_norm.columns:
                continue

            serie = df_norm[col].fillna("").astype(str).str.strip()
            # Reducción de espacios intermedios múltiples a un único espacio
            serie = serie.str.replace(r"\s+", " ", regex=True)
            serie_upper = serie.str.upper()

            # Máscara para detectar celdas vacías o representaciones de nulos
            mascara_nulos = serie_upper.isin(cls.PATRONES_NULOS) | (serie == "")
            conteo_nulos = int(mascara_nulos.sum())
            celdas_imputadas += conteo_nulos

            # Aplicar valor tipificado y mayúsculas
            serie_limpia = serie_upper.mask(mascara_nulos, valor_reemplazo)
            df_norm[col] = serie_limpia

        return df_norm, celdas_imputadas

    @classmethod
    def ejecutar_limpieza_completa(
        cls,
        df: pd.DataFrame,
        col_id: str = "id_contrato",
        col_cuantia: str = "cuantia_inicial",
        columnas_texto: list[str] | None = None
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Criterio 4: Orquesta la secuencia completa de calidad de datos y genera el reporte auditable.

        Returns:
            tuple[pd.DataFrame, dict]: DataFrame limpio y diccionario de métricas de calidad.
        """
        total_inicial = len(df)

        # 1. Eliminación de duplicados por ID único
        df_sin_duplicados, dup_eliminados = cls.eliminar_duplicados(df, col_id=col_id)

        # 2. Filtrado de cuantías válidas (> 0)
        df_cuantias_validas, cuantias_descartadas = cls.filtrar_cuantias_validas(
            df_sin_duplicados, col_cuantia=col_cuantia
        )

        # 3. Normalización tipográfica y sustitución de nulos
        if columnas_texto is None:
            # Columnas clave de texto del Esquema en Estrella
            columnas_clave = [
                "nombre_entidad", "proveedor", "departamento", "municipio",
                "modalidad", "tipo_contrato", "estado", "sector", "orden_entidad"
            ]
            columnas_texto = [c for c in columnas_clave if c in df_cuantias_validas.columns]
            if not columnas_texto:
                columnas_texto = [
                    c for c in df_cuantias_validas.columns
                    if pd.api.types.is_object_dtype(df_cuantias_validas[c]) or pd.api.types.is_string_dtype(df_cuantias_validas[c])
                ]

        df_final_limpio, celdas_imputadas = cls.normalizar_textos_y_nulos(
            df_cuantias_validas, columnas_texto=columnas_texto
        )

        total_final = len(df_final_limpio)
        tasa_retencion = round((total_final / total_inicial * 100.0), 2) if total_inicial > 0 else 0.0

        metricas = {
            "total_inicial": total_inicial,
            "duplicados_eliminados": dup_eliminados,
            "cuantias_invalidas_descartadas": cuantias_descartadas,
            "celdas_imputadas": celdas_imputadas,
            "total_final_limpio": total_final,
            "tasa_retencion_pct": tasa_retencion
        }

        return df_final_limpio, metricas
