"""
Servicio de Exportación de Datos y Reportes Gerenciales (CSV con UTF-8 BOM)
Historia de Usuario: HU-30 (Exportación de Datos Filtrados y Reportes a CSV)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import pandas as pd

from src.database.connection import MongoConnectionSingleton


class ExportService:
    """
    Servicio encargado de preparar, normalizar y serializar los subconjuntos
    de contratos filtrados hacia formatos de exportación externa (CSV).
    """

    MAPEO_COLUMNAS_EJECUTIVAS = {
        "id_proceso": "ID_Proceso",
        "id_contrato": "ID_Proceso",
        "proceso_de_compra": "ID_Proceso",
        "anio_vigencia": "Vigencia_Fiscal",
        "ano_firma": "Vigencia_Fiscal",
        "departamento": "Departamento",
        "municipio": "Municipio",
        "ciudad": "Municipio",
        "entidad": "Entidad_Compradora",
        "nombre_entidad": "Entidad_Compradora",
        "nit_entidad": "NIT_Entidad",
        "modalidad": "Modalidad_Seleccion",
        "modalidad_de_contratacion": "Modalidad_Seleccion",
        "tipo_contrato": "Tipo_Contrato",
        "tipo_de_contrato": "Tipo_Contrato",
        "estado": "Estado_Proceso",
        "estado_contrato": "Estado_Proceso",
        "proveedor": "Contratista_Adjudicado",
        "proveedor_adjudicado": "Contratista_Adjudicado",
        "documento_proveedor": "Documento_Contratista",
        "es_pyme": "Es_PYME",
        "codigo_unspsc": "Codigo_UNSPSC",
        "codigo_de_categoria_principal": "Codigo_UNSPSC",
        "cuantia_inicial": "Cuantia_Inicial_COP",
        "valor_del_contrato": "Cuantia_Inicial_COP",
        "valor_adiciones": "Valor_Adiciones_COP",
        "cuantia_final": "Cuantia_Final_COP",
        "plazo_dias": "Plazo_Ejecucion_Dias",
        "duracion_dias": "Plazo_Ejecucion_Dias",
        "tiene_adicion": "Tiene_Adicion",
        "score_riesgo_anomalia": "Score_Riesgo_ML",
        "nivel_alerta": "Nivel_Alerta_ML",
    }

    @classmethod
    def preparar_dataframe_exportacion(
        cls,
        df: pd.DataFrame | None,
        solo_columnas_clave: bool = True
    ) -> pd.DataFrame:
        """
        Prepara una copia limpia del DataFrame activo para exportación gerencial:
        - Filtra y renombra columnas clave si solo_columnas_clave=True.
        - Elimina columnas internas o auxiliares de UI si existen (_id, etc.).
        """
        if df is None or df.empty:
            return pd.DataFrame()

        df_export = df.copy()

        # Excluir identificador interno de MongoDB si estuviera presente
        if "_id" in df_export.columns:
            df_export = df_export.drop(columns=["_id"])

        if solo_columnas_clave:
            cols_presentes = []
            nombres_destino = set()
            for orig, dest in cls.MAPEO_COLUMNAS_EJECUTIVAS.items():
                if orig in df_export.columns and dest not in nombres_destino:
                    cols_presentes.append(orig)
                    nombres_destino.add(dest)

            if cols_presentes:
                mapeo_activo = {c: cls.MAPEO_COLUMNAS_EJECUTIVAS[c] for c in cols_presentes}
                df_export = df_export[cols_presentes].rename(columns=mapeo_activo)

        return df_export

    @classmethod
    def generar_csv_bytes(
        cls,
        df: pd.DataFrame | None,
        solo_columnas_clave: bool = True,
        separador: str = ",",
    ) -> bytes:
        """
        Convierte el DataFrame filtrado a bytes codificados en UTF-8 con BOM (utf-8-sig)
        para garantizar compatibilidad directa con Microsoft Excel y herramientas de auditoría.
        """
        if df is None or df.empty:
            return b""

        df_listo = cls.preparar_dataframe_exportacion(df, solo_columnas_clave=solo_columnas_clave)
        if df_listo.empty:
            return b""

        contenido_csv = df_listo.to_csv(index=False, sep=separador)
        return contenido_csv.encode("utf-8-sig")

    @staticmethod
    def generar_nombre_archivo(prefijo: str = "SECOP_Analytics_Reporte") -> str:
        """Genera un nombre de archivo estandarizado con sello temporal."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefijo}_{timestamp}.csv"

    @staticmethod
    def registrar_auditoria_exportacion(
        usuario: str,
        total_registros: int,
        query_match: dict[str, Any] | None = None
    ) -> None:
        """Persiste la trazabilidad de descarga en MongoDB sin bloquear la interfaz."""
        try:
            col = MongoConnectionSingleton.get_collection("auditoria_descargas")
            col.insert_one({
                "fecha_descarga": datetime.now(timezone.utc),
                "usuario": usuario,
                "formato": "CSV",
                "registros_exportados": int(total_registros),
                "filtros_aplicados": query_match or {},
            })
        except Exception:
            pass
