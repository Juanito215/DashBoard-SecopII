"""
Submódulo de Ingeniería de Características (Feature Engineering)
Historia de Usuario: HU-07 (Generación de Variables Analíticas Derivadas)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import re
from typing import Any
import numpy as np
import pandas as pd


class FeatureEngineer:
    """
    Generador de variables derivadas para el Esquema en Estrella (FACT_CONTRATOS)
    y para modelos supervisados de Machine Learning (PA-ALFA-005).
    Implementa transformaciones vectorizadas e inmutables.
    """

    @staticmethod
    def _parsear_unidad_plazo(val: Any) -> float:
        """Extrae la cantidad numérica y normaliza unidades (días, meses, años) a días calendario."""
        if pd.isna(val) or val is None:
            return np.nan

        if isinstance(val, (int, float, np.integer, np.floating)):
            return float(val) if val > 0 else np.nan

        val_str = str(val).strip().lower()
        if not val_str:
            return np.nan

        # Búsqueda de valor numérico
        match_num = re.search(r"(\d+(?:\.\d+)?)", val_str)
        if not match_num:
            return np.nan

        num = float(match_num.group(1))
        if num <= 0:
            return np.nan

        if "año" in val_str or "ano" in val_str or "year" in val_str:
            return num * 365.0
        elif "mes" in val_str or "month" in val_str:
            return num * 30.0
        else:
            # Por defecto días
            return num

    @classmethod
    def calcular_cuantias_y_etiqueta_adicion(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Criterios 1 y 2:
        - cuantia_final = cuantia_inicial + valor_adiciones
        - tiene_adicion = (valor_adiciones > 0)
        """
        df_res = df.copy()

        if "cuantia_inicial" not in df_res.columns:
            df_res["cuantia_inicial"] = 0.0
        if "valor_adiciones" not in df_res.columns:
            df_res["valor_adiciones"] = 0.0

        # Asegurar tipos float64
        c_ini = pd.to_numeric(df_res["cuantia_inicial"], errors="coerce").fillna(0.0).astype(np.float64)
        v_adi = pd.to_numeric(df_res["valor_adiciones"], errors="coerce").fillna(0.0).astype(np.float64)

        df_res["cuantia_inicial"] = c_ini
        df_res["valor_adiciones"] = v_adi
        df_res["cuantia_final"] = (c_ini + v_adi).astype(np.float64)
        df_res["tiene_adicion"] = (v_adi > 0).astype(bool)

        return df_res

    @classmethod
    def estandarizar_plazo_dias(
        cls,
        df: pd.DataFrame,
        col_plazo: str = "plazo_ejecucion_dias",
        fallback_default_dias: float = 90.0
    ) -> pd.DataFrame:
        """
        Criterio 3: Extrae, convierte unidades e imputa valores faltantes para obtener plazo_dias > 0.
        Garantiza tipo entero (int64).
        """
        df_res = df.copy()

        # Determinar columna fuente de plazo
        col_fuente = None
        for col_cand in [col_plazo, "plazo_ejecucion", "duracion_dias", "plazo_dias"]:
            if col_cand in df_res.columns:
                col_fuente = col_cand
                break

        if col_fuente is not None:
            plazos_parseados = df_res[col_fuente].apply(cls._parsear_unidad_plazo)
        else:
            plazos_parseados = pd.Series(np.nan, index=df_res.index)

        # Respaldo cronológico si existen fechas de inicio y fin
        cols_fin = [c for c in ["fecha_de_fin_del_contrato", "fecha_fin", "fecha_fin_contrato"] if c in df_res.columns]
        cols_ini = [c for c in ["fecha_de_inicio_del_contrato", "fecha_inicio", "fecha_inicio_contrato"] if c in df_res.columns]

        if cols_fin and cols_ini:
            f_fin = pd.to_datetime(df_res[cols_fin[0]], errors="coerce")
            f_ini = pd.to_datetime(df_res[cols_ini[0]], errors="coerce")
            dif_dias = (f_fin - f_ini).dt.days
            mascara_reemplazo = plazos_parseados.isna() & (dif_dias > 0)
            plazos_parseados = plazos_parseados.mask(mascara_reemplazo, dif_dias)

        # Imputación de valores faltantes o <= 0 con la mediana representativa
        valores_validos = plazos_parseados[plazos_parseados > 0]
        mediana_plazo = float(valores_validos.median()) if not valores_validos.empty else fallback_default_dias
        if np.isnan(mediana_plazo) or mediana_plazo <= 0:
            mediana_plazo = fallback_default_dias

        plazos_limpios = plazos_parseados.fillna(mediana_plazo)
        # Descartar cualquier residuo menor o igual a 0
        plazos_limpios = plazos_limpios.mask(plazos_limpios <= 0, mediana_plazo)

        plazos_enteros = plazos_limpios.round().astype(np.int64)

        df_res["plazo_dias"] = plazos_enteros
        df_res["plazo_ejecucion_dias"] = plazos_enteros

        return df_res

    @classmethod
    def generar_features_adicionales_ml(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Genera variables analíticas y predictivas para enriquecer los modelos de Machine Learning (PA-ALFA-005):
        - porcentaje_adicion
        - tasa_gasto_diario
        - es_cuantia_alta
        """
        df_res = df.copy()

        # 1. Porcentaje de adición sobre la cuantía original
        c_ini = df_res["cuantia_inicial"].replace(0.0, np.nan)
        pct_adi = (df_res["valor_adiciones"] / c_ini).fillna(0.0)
        df_res["porcentaje_adicion"] = pct_adi.clip(lower=0.0).astype(np.float64)

        # 2. Tasa de gasto o ejecución diaria (COP / día)
        plazo = df_res["plazo_dias"].replace(0, np.nan)
        gasto_dia = (df_res["cuantia_final"] / plazo).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        df_res["tasa_gasto_diario"] = gasto_dia.round(2).astype(np.float64)

        # 3. Indicador de alta cuantía (Percentil 75)
        umbral_p75 = df_res["cuantia_final"].quantile(0.75) if not df_res.empty else 0.0
        df_res["es_cuantia_alta"] = (df_res["cuantia_final"] > umbral_p75).astype(bool)

        return df_res

    @classmethod
    def aplicar_feature_engineering_lote(
        cls,
        df: pd.DataFrame,
        col_plazo: str = "plazo_ejecucion_dias"
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Criterio 4: Ejecuta la secuencia completa de Feature Engineering y reporta métricas analíticas.

        Returns:
            tuple[pd.DataFrame, dict]: DataFrame con features calculadas y resumen analítico.
        """
        # Paso 1: Cuantías y etiqueta de adición
        df_cuantias = cls.calcular_cuantias_y_etiqueta_adicion(df)

        # Paso 2: Estandarización de plazos en días enteros
        df_plazos = cls.estandarizar_plazo_dias(df_cuantias, col_plazo=col_plazo)

        # Paso 3: Features adicionales para analítica y ML
        df_final = cls.generar_features_adicionales_ml(df_plazos)

        total_filas = len(df_final)
        total_adic = int(df_final["tiene_adicion"].sum())
        tasa_adic = round(float(df_final["tiene_adicion"].mean() * 100), 2) if total_filas > 0 else 0.0
        plazo_prom = round(float(df_final["plazo_dias"].mean()), 1) if total_filas > 0 else 0.0
        plazo_med = round(float(df_final["plazo_dias"].median()), 1) if total_filas > 0 else 0.0
        cuantia_tot = round(float(df_final["cuantia_final"].sum()), 2) if total_filas > 0 else 0.0

        resumen = {
            "total_registros": total_filas,
            "total_con_adicion": total_adic,
            "tasa_adicion_pct": tasa_adic,
            "plazo_promedio_dias": plazo_prom,
            "plazo_mediana_dias": plazo_med,
            "cuantia_final_total": cuantia_tot
        }

        return df_final, resumen
