"""
Submódulo de Transformación de Formatos Financieros y Cronológicos
Historia de Usuario: HU-06 (Transformación de Formatos Financieros y Cronológicos)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import re
from typing import Any
import numpy as np
import pandas as pd


class DataTransformer:
    """
    Transformador de datos para estandarización de tipos monetarios continuos (Double / Float64),
    fechas a formato ISODate/datetime64 y cálculo vectorizado de variables derivadas.
    """

    @classmethod
    def limpiar_columna_monetaria(cls, serie: pd.Series) -> pd.Series:
        """
        Criterio 1: Convierte series monetarias heterogéneas a tipo numérico continuo float64.
        Limpia signos de pesos, comas, puntos, espacios y caracteres no numéricos.

        Args:
            serie: Serie de Pandas con valores numéricos o cadenas monetarias.

        Returns:
            pd.Series: Serie tipada estrictamente en float64.
        """
        if pd.api.types.is_numeric_dtype(serie):
            return pd.to_numeric(serie, errors="coerce").fillna(0.0).astype(np.float64)

        def _limpiar_valor(val: Any) -> float:
            if pd.isna(val) or val is None:
                return 0.0

            texto = str(val).strip().replace("$", "").replace("COP", "").replace("cop", "").replace("'", "").strip()
            if not texto:
                return 0.0

            # 1. Caso: Contiene tanto punto como coma
            if "." in texto and "," in texto:
                if texto.rfind(",") > texto.rfind("."):
                    # Formato europeo/latino: 150.000.000,50 -> 150000000.50
                    texto = texto.replace(".", "").replace(",", ".")
                else:
                    # Formato anglosajón: 150,000,000.50 -> 150000000.50
                    texto = texto.replace(",", "")
            # 2. Caso: Contiene comas pero no puntos
            elif "," in texto:
                partes = texto.split(",")
                # Si hay solo una coma y 1 o 2 dígitos al final, es separador decimal
                if len(partes) == 2 and len(partes[1]) in [1, 2]:
                    texto = partes[0] + "." + partes[1]
                else:
                    texto = texto.replace(",", "")
            # 3. Caso: Contiene puntos pero no comas
            elif "." in texto:
                partes = texto.split(".")
                # Múltiples puntos son separadores de miles: 150.000.000
                if len(partes) > 2:
                    texto = texto.replace(".", "")
                elif len(partes) == 2:
                    # Si tiene 3 dígitos al final y la parte entera es corta, son miles: 150.000 -> 150000
                    if len(partes[1]) == 3 and len(partes[0]) <= 3:
                        texto = texto.replace(".", "")
                    # En caso contrario, se interpreta como decimal: 45.50 -> 45.50

            # Retirar cualquier caracter extraño remanente excepto dígitos, punto y signo menos
            texto = re.sub(r"[^\d.-]", "", texto)

            try:
                return float(texto)
            except ValueError:
                return 0.0

        return serie.apply(_limpiar_valor).astype(np.float64)

    @classmethod
    def parsear_fechas_y_derivar_tiempo(
        cls,
        df: pd.DataFrame,
        col_fecha: str = "fecha_firma",
        fecha_fallback: str = "2022-01-01"
    ) -> pd.DataFrame:
        """
        Criterio 2: Parsea fechas a datetime64[ns] y extrae variables temporales
        del Esquema en Estrella: anio_vigencia, mes_vigencia y trimestre.

        Args:
            df: DataFrame con la columna de fecha.
            col_fecha: Nombre de la columna de fecha.
            fecha_fallback: Fecha por defecto en caso de valores no parseables.

        Returns:
            pd.DataFrame: DataFrame enriquecido con columnas temporales.
        """
        df_res = df.copy()

        if col_fecha not in df_res.columns:
            df_res[col_fecha] = pd.Timestamp(fecha_fallback)

        try:
            fechas_dt = pd.to_datetime(df_res[col_fecha], format="mixed", errors="coerce", dayfirst=True)
        except Exception:
            fechas_dt = pd.to_datetime(df_res[col_fecha], errors="coerce", dayfirst=True)
        # Imputación segura de fechas faltantes
        fechas_dt = fechas_dt.fillna(pd.Timestamp(fecha_fallback))
        df_res[col_fecha] = fechas_dt

        # Variables temporales derivadas (enteros nativos)
        df_res["anio_vigencia"] = fechas_dt.dt.year.astype(int)
        df_res["mes_vigencia"] = fechas_dt.dt.month.astype(int)
        df_res["trimestre"] = fechas_dt.dt.quarter.astype(int)

        return df_res

    @classmethod
    def calcular_variables_financieras(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Criterio 3: Calcula variables financieras derivadas:
        - cuantia_final = cuantia_inicial + valor_adiciones
        - tiene_adicion = (valor_adiciones > 0)

        Args:
            df: DataFrame con cuantia_inicial y valor_adiciones.

        Returns:
            pd.DataFrame: DataFrame enriquecido con cuantia_final y tiene_adicion.
        """
        df_res = df.copy()

        if "cuantia_inicial" not in df_res.columns:
            df_res["cuantia_inicial"] = 0.0
        if "valor_adiciones" not in df_res.columns:
            df_res["valor_adiciones"] = 0.0

        # Asegurar tipado float64 antes del cálculo
        df_res["cuantia_inicial"] = cls.limpiar_columna_monetaria(df_res["cuantia_inicial"])
        df_res["valor_adiciones"] = cls.limpiar_columna_monetaria(df_res["valor_adiciones"])

        # Cálculo vectorizado
        df_res["cuantia_final"] = (df_res["cuantia_inicial"] + df_res["valor_adiciones"]).astype(np.float64)
        df_res["tiene_adicion"] = (df_res["valor_adiciones"] > 0).astype(bool)

        return df_res

    @classmethod
    def transformar_lote_completo(
        cls,
        df: pd.DataFrame,
        col_fecha: str = "fecha_firma"
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Criterio 4: Orquesta la transformación completa de formatos financieros y cronológicos.

        Returns:
            tuple[pd.DataFrame, dict]: DataFrame transformado y métricas de transformación.
        """
        # 1. Transformación cronológica
        df_tiempo = cls.parsear_fechas_y_derivar_tiempo(df, col_fecha=col_fecha)

        # 2. Transformación y variables financieras
        df_final = cls.calcular_variables_financieras(df_tiempo)

        # 3. Métricas de transformación
        cols_monetarias = [c for c in ["cuantia_inicial", "valor_adiciones", "cuantia_final"] if c in df_final.columns]
        total_adicion = int(df_final["tiene_adicion"].sum())
        total_filas = len(df_final)
        pct_adicion = round((total_adicion / total_filas * 100), 2) if total_filas > 0 else 0.0

        rango_min = str(df_final[col_fecha].min()) if not df_final.empty else "N/A"
        rango_max = str(df_final[col_fecha].max()) if not df_final.empty else "N/A"
        anios = sorted(df_final["anio_vigencia"].unique().tolist()) if not df_final.empty else []

        metricas = {
            "columnas_monetarias_procesadas": cols_monetarias,
            "dtypes_monetarios": str(df_final["cuantia_inicial"].dtype),
            "rango_fechas_min": rango_min,
            "rango_fechas_max": rango_max,
            "anios_detectados": anios,
            "total_con_adicion": total_adicion,
            "pct_con_adicion": pct_adicion
        }

        return df_final, metricas
