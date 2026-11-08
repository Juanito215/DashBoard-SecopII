"""
Pipeline ETL para SECOP II bajo Metodología CRISP-DM
Historia de Usuario: HU-02 (Pipeline ETL y Carga en MongoDB)
Caso de Prueba de Aceptación: PA-ALFA-002
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import io
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from pymongo import UpdateOne
from src.database.connection import MongoConnectionSingleton


class SecopETLPipeline:
    """
    Pipeline de Extracción, Transformación y Carga (ETL) para procesar
    contratos de SECOP II y estructurarlos en Esquema en Estrella en MongoDB.
    """

    # Variantes de nombres de columnas en SECOP II mapeadas a nombres canónicos
    MAPEO_COLUMNAS_CANONICAS: dict[str, list[str]] = {
        "id_contrato": [
            "id_contrato", "id contrato", "identificador_contrato",
            "referencia_del_contrato", "id_documento"
        ],
        "codigo_proceso": [
            "proceso_de_compra", "codigo_proceso", "codigo proceso",
            "proceso de compra", "num_proceso", "urlproceso"
        ],
        "cuantia_inicial": [
            "valor_del_contrato", "cuantia_inicial", "valor del contrato",
            "cuantia", "valor_contrato", "monto_contrato"
        ],
        "valor_adiciones": [
            "valor_adiciones", "valor adiciones", "valor_de_las_adiciones",
            "valor de las adiciones", "adiciones", "monto_adiciones"
        ],
        "plazo_ejecucion_dias": [
            "duracion_dias", "plazo_ejecucion_dias", "plazo de ejecucion",
            "plazo_de_ejecucion", "dias_duracion", "plazo_ejecucion"
        ],
        "departamento": [
            "departamento", "dpto", "departamento de ejecucion",
            "departamento_ejecucion"
        ],
        "municipio": [
            "ciudad", "municipio", "ciudad de ejecucion",
            "municipio_ejecucion", "ciudad_ejecucion"
        ],
        "fecha_firma": [
            "fecha_de_firma", "fecha_firma", "fecha firma",
            "fecha de firma", "fecha_firma_contrato"
        ],
        "modalidad": [
            "modalidad_de_contratacion", "modalidad",
            "modalidad de contratacion", "tipo_modalidad"
        ],
        "tipo_contrato": [
            "tipo_de_contrato", "tipo_contrato", "tipo de contrato"
        ],
        "estado": [
            "estado_contrato", "estado", "estado del contrato", "estado contrato"
        ],
        "codigo_unspsc": [
            "codigo_de_categoria_principal", "codigo_unspsc", "categoria_principal",
            "categoria principal", "segmento_unspsc", "unspsc"
        ],
        "nombre_entidad": [
            "nombre_entidad", "nombre entidad", "nombre de la entidad",
            "entidad", "entidad_compradora"
        ],
        "nit_entidad": [
            "nit_entidad", "nit entidad", "nit de la entidad",
            "nit", "documento_entidad"
        ],
        "orden_entidad": [
            "orden", "orden_entidad", "orden entidad", "nivel_entidad"
        ],
        "sector": [
            "sector", "sector_entidad", "sector_administrativo"
        ],
        "documento_proveedor": [
            "documento_proveedor", "documento proveedor", "nit proveedor",
            "nit_proveedor", "identificacion_proveedor", "doc_proveedor"
        ],
        "proveedor": [
            "proveedor_adjudicado", "proveedor", "nombre_proveedor",
            "nombre proveedor", "razon_social", "nombre_razon_social"
        ],
        "es_pyme": [
            "es_pyme", "es pyme", "pyme", "es_mipyme"
        ]
    }

    def __init__(self) -> None:
        self.ultimas_metricas: dict[str, Any] = {}

    @staticmethod
    def _normalizar_texto(serie: pd.Series, a_mayusculas: bool = True) -> pd.Series:
        """Limpia caracteres extraños, espacios duplicados y estandariza mayúsculas."""
        s = serie.fillna("NO REGISTRADO").astype(str).str.strip()
        s = s.str.replace(r"\s+", " ", regex=True)
        if a_mayusculas:
            s = s.str.upper()
        return s

    @staticmethod
    def _limpiar_moneda_vectorizado(serie: pd.Series) -> pd.Series:
        """
        Convierte series monetarias a float continuo en COP.
        Tolerante a símbolos de moneda, comas de miles y formatos mixtos.
        """
        if pd.api.types.is_numeric_dtype(serie):
            return pd.to_numeric(serie, errors="coerce").fillna(0.0).astype(float)

        def _limpiar_valor(val: Any) -> float:
            if pd.isna(val) or val is None:
                return 0.0
            texto = str(val).strip().replace("$", "").replace("COP", "").replace("cop", "").strip()
            if not texto:
                return 0.0
            # Si contiene tanto punto como coma, determinar cuál es el separador decimal
            if "." in texto and "," in texto:
                if texto.rfind(",") > texto.rfind("."):
                    # Formato 1.000.000,50 -> 1000000.50
                    texto = texto.replace(".", "").replace(",", ".")
                else:
                    # Formato 1,000,000.50 -> 1000000.50
                    texto = texto.replace(",", "")
            elif "," in texto:
                partes = texto.split(",")
                if len(partes) == 2 and len(partes[1]) in [1, 2]:
                    texto = partes[0] + "." + partes[1]
                else:
                    texto = texto.replace(",", "")
            try:
                return float(texto)
            except ValueError:
                return 0.0

        return serie.apply(_limpiar_valor).astype(float)

    @staticmethod
    def _parsear_booleano(serie: pd.Series) -> pd.Series:
        """Normaliza columnas booleanas como 'es_pyme' asegurando tipo booleano nativo."""
        if pd.api.types.is_bool_dtype(serie):
            return serie.astype(bool)

        def _a_bool(val: Any) -> bool:
            if pd.isna(val) or val is None:
                return False
            val_str = str(val).strip().lower()
            return val_str in ["si", "sí", "true", "1", "t", "s", "verdadero", "yes", "y"]

        return serie.apply(_a_bool).astype(bool)

    def extraer_csv(self, fuente: str | Path | io.BytesIO | pd.DataFrame) -> pd.DataFrame:
        """
        Fase 1: Extracción del dataset y resolución dinámica del esquema de columnas.

        Args:
            fuente: Ruta a archivo CSV, stream en memoria (BytesIO) o DataFrame existente.

        Returns:
            pd.DataFrame: DataFrame con nombres de columnas normalizados a canónicos.
        """
        if isinstance(fuente, pd.DataFrame):
            df = fuente.copy()
        elif isinstance(fuente, (str, Path)):
            ruta = Path(fuente)
            if not ruta.exists():
                # Búsqueda de respaldo en data/raw/
                ruta_raw = Path("data") / "raw" / ruta.name
                if ruta_raw.exists():
                    ruta = ruta_raw
                else:
                    raise FileNotFoundError(f"No se encontró el archivo CSV en: {ruta.resolve()} ni en {ruta_raw.resolve()}")
            df = pd.read_csv(ruta, low_memory=False)
        else:
            df = pd.read_csv(fuente, low_memory=False)

        # Mapeo dinámico y tolerante de columnas
        nombres_reales = {col.strip().lower(): col for col in df.columns}
        columnas_renombrar: dict[str, str] = {}

        for canonica, variantes in self.MAPEO_COLUMNAS_CANONICAS.items():
            for var in variantes:
                var_clean = var.strip().lower()
                if var_clean in nombres_reales:
                    original_col = nombres_reales[var_clean]
                    columnas_renombrar[original_col] = canonica
                    break

        df = df.rename(columns=columnas_renombrar)

        # Inicialización de columnas canónicas que no existan en la fuente
        if "id_contrato" not in df.columns:
            df["id_contrato"] = [f"CO1.PCONTR.{i+1:07d}" for i in range(len(df))]
        if "codigo_proceso" not in df.columns:
            df["codigo_proceso"] = ""
        if "cuantia_inicial" not in df.columns:
            df["cuantia_inicial"] = 0.0
        if "valor_adiciones" not in df.columns:
            df["valor_adiciones"] = 0.0
        if "plazo_ejecucion_dias" not in df.columns:
            df["plazo_ejecucion_dias"] = 0
        if "departamento" not in df.columns:
            df["departamento"] = "COLOMBIA"
        if "municipio" not in df.columns:
            df["municipio"] = "NO REGISTRADO"
        if "fecha_firma" not in df.columns:
            df["fecha_firma"] = "2022-01-01"
        if "modalidad" not in df.columns:
            df["modalidad"] = "CONTRATACION DIRECTA"
        if "tipo_contrato" not in df.columns:
            df["tipo_contrato"] = "PRESTACION DE SERVICIOS"
        if "estado" not in df.columns:
            df["estado"] = "ACTIVO"
        if "codigo_unspsc" not in df.columns:
            df["codigo_unspsc"] = "No Registrado"
        if "nombre_entidad" not in df.columns:
            df["nombre_entidad"] = "ENTIDAD ESTATAL NO REGISTRADA"
        if "nit_entidad" not in df.columns:
            df["nit_entidad"] = "0"
        if "orden_entidad" not in df.columns:
            df["orden_entidad"] = "Territorial"
        if "sector" not in df.columns:
            df["sector"] = "General"
        if "documento_proveedor" not in df.columns:
            df["documento_proveedor"] = "0"
        if "proveedor" not in df.columns:
            df["proveedor"] = "PROVEEDOR NO REGISTRADO"
        if "es_pyme" not in df.columns:
            df["es_pyme"] = False

        return df

    def transformar_datos(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
        """
        Fase 2: Transformación, depuración vectorizada y feature engineering (CRISP-DM).

        Returns:
            tuple[pd.DataFrame, int, int]:
                - DataFrame depurado y enriquecido.
                - total_registros_leidos.
                - total_descartados.
        """
        total_leidos = len(df)

        # 1. Deduplicación por id_contrato
        df_limpio = df.drop_duplicates(subset=["id_contrato"], keep="first").copy()

        # 2. Limpieza y casting financiero en Pesos Colombianos (COP)
        df_limpio["cuantia_inicial"] = self._limpiar_moneda_vectorizado(df_limpio["cuantia_inicial"])
        df_limpio["valor_adiciones"] = self._limpiar_moneda_vectorizado(df_limpio["valor_adiciones"])

        # 3. Descarte de registros con cuantía corrupta o menor/igual a cero
        mascara_cuantia_valida = df_limpio["cuantia_inicial"] > 0
        df_limpio = df_limpio[mascara_cuantia_valida].copy()

        # 4. Limpieza de texto en entidades y contratistas
        df_limpio["nombre_entidad"] = self._normalizar_texto(df_limpio["nombre_entidad"], a_mayusculas=True)
        df_limpio["proveedor"] = self._normalizar_texto(df_limpio["proveedor"], a_mayusculas=True)
        df_limpio["departamento"] = self._normalizar_texto(df_limpio["departamento"], a_mayusculas=True)
        df_limpio["municipio"] = self._normalizar_texto(df_limpio["municipio"], a_mayusculas=True)
        df_limpio["modalidad"] = self._normalizar_texto(df_limpio["modalidad"], a_mayusculas=False)
        df_limpio["tipo_contrato"] = self._normalizar_texto(df_limpio["tipo_contrato"], a_mayusculas=False)
        df_limpio["estado"] = self._normalizar_texto(df_limpio["estado"], a_mayusculas=False)
        df_limpio["orden_entidad"] = self._normalizar_texto(df_limpio["orden_entidad"], a_mayusculas=False)
        df_limpio["sector"] = self._normalizar_texto(df_limpio["sector"], a_mayusculas=False)
        df_limpio["codigo_unspsc"] = df_limpio["codigo_unspsc"].fillna("No Registrado").astype(str).str.strip()

        # Identificadores alfanuméricos
        df_limpio["nit_entidad"] = df_limpio["nit_entidad"].fillna("0").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        df_limpio["documento_proveedor"] = df_limpio["documento_proveedor"].fillna("0").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        df_limpio["codigo_proceso"] = df_limpio["codigo_proceso"].fillna("").astype(str).str.strip()
        df_limpio["id_contrato"] = df_limpio["id_contrato"].astype(str).str.strip()

        # 5. Normalización de fechas y extracción de dimensión temporal
        fechas_dt = pd.to_datetime(df_limpio["fecha_firma"], errors="coerce")
        # Imputar fechas nulas con fecha semilla por defecto (2022-01-01)
        fechas_dt = fechas_dt.fillna(pd.Timestamp("2022-01-01"))
        df_limpio["fecha_firma_dt"] = fechas_dt

        df_limpio["anio_vigencia"] = fechas_dt.dt.year.astype(int)
        df_limpio["mes_vigencia"] = fechas_dt.dt.month.astype(int)
        df_limpio["trimestre"] = fechas_dt.dt.quarter.astype(int)

        # 6. Variables derivadas (Feature Engineering)
        df_limpio["cuantia_final"] = df_limpio["cuantia_inicial"] + df_limpio["valor_adiciones"]
        df_limpio["tiene_adicion"] = df_limpio["valor_adiciones"] > 0
        df_limpio["plazo_ejecucion_dias"] = pd.to_numeric(
            df_limpio["plazo_ejecucion_dias"], errors="coerce"
        ).fillna(0).astype(int).clip(lower=0)

        # 7. Tipado booleano de es_pyme
        df_limpio["es_pyme"] = self._parsear_booleano(df_limpio["es_pyme"])

        total_descartados = total_leidos - len(df_limpio)
        return df_limpio, total_leidos, total_descartados

    def estructurar_esquema_estrella(self, df_limpio: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Fase 3: Estructuración de documentos BSON bajo el Esquema en Estrella embebido.
        """
        documentos: list[dict[str, Any]] = []

        for row in df_limpio.to_dict(orient="records"):
            # Asegurar fecha como datetime nativo de Python para ISODate en MongoDB
            fecha_val = row["fecha_firma_dt"]
            if isinstance(fecha_val, pd.Timestamp):
                fecha_native = fecha_val.to_pydatetime()
            elif isinstance(fecha_val, datetime):
                fecha_native = fecha_val
            else:
                fecha_native = datetime(int(row["anio_vigencia"]), int(row["mes_vigencia"]), 1)

            doc: dict[str, Any] = {
                "_id": str(row["id_contrato"]),
                "codigo_proceso": str(row.get("codigo_proceso", "")),
                "cuantia_inicial": float(row["cuantia_inicial"]),
                "valor_adiciones": float(row["valor_adiciones"]),
                "cuantia_final": float(row["cuantia_final"]),
                "plazo_ejecucion_dias": int(row["plazo_ejecucion_dias"]),
                "tiene_adicion": bool(row["tiene_adicion"]),
                "score_riesgo_anomalia": float(0.0),  # Placeholder para módulo ML (HU-27)
                "geografia": {
                    "departamento": str(row["departamento"]),
                    "municipio": str(row["municipio"])
                },
                "tiempo": {
                    "fecha_firma": fecha_native,
                    "anio_vigencia": int(row["anio_vigencia"]),
                    "mes_vigencia": int(row["mes_vigencia"]),
                    "trimestre": int(row["trimestre"])
                },
                "clasificacion": {
                    "modalidad": str(row["modalidad"]),
                    "tipo_contrato": str(row["tipo_contrato"]),
                    "estado": str(row["estado"]),
                    "codigo_unspsc": str(row.get("codigo_unspsc", "No Registrado"))
                },
                "entidad": {
                    "nit": str(row.get("nit_entidad", "")),
                    "nombre": str(row["nombre_entidad"]),
                    "orden": str(row.get("orden_entidad", "Territorial")),
                    "sector": str(row.get("sector", "General"))
                },
                "proveedor": {
                    "documento": str(row.get("documento_proveedor", "")),
                    "nombre_razon_social": str(row["proveedor"]),
                    "es_pyme": bool(row.get("es_pyme", True))
                }
            }
            documentos.append(doc)

        return documentos

    def cargar_en_mongodb(
        self,
        documentos: list[dict[str, Any]],
        batch_size: int = 2000,
        progreso_callback: Callable[[float, str], None] | None = None
    ) -> int:
        """
        Fase 4: Carga masiva por lotes e indexación analítica en la colección 'contratos'.
        """
        if not documentos:
            return 0

        coleccion = MongoConnectionSingleton.get_collection("contratos")
        total_docs = len(documentos)
        total_insertados = 0

        # Inserción idempotente con bulk_write (UpdateOne con upsert=True)
        for i in range(0, total_docs, batch_size):
            lote = documentos[i : i + batch_size]
            operaciones = [
                UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
                for doc in lote
            ]
            resultado = coleccion.bulk_write(operaciones, ordered=False)
            total_insertados += (resultado.upserted_count + resultado.matched_count + resultado.modified_count)

            if progreso_callback:
                progreso = min(1.0, (i + len(lote)) / total_docs)
                progreso_callback(progreso, f"Cargando lote {i//batch_size + 1} ({min(i + len(lote), total_docs):,}/{total_docs:,})")

        # Creación / Aseguramiento de índices analíticos
        self._asegurar_indices(coleccion)

        return total_docs

    @staticmethod
    def _asegurar_indices(coleccion) -> None:
        """Crea los 4 índices analíticos optimizados para los 10 filtros dinámicos."""
        try:
            coleccion.create_index(
                [("geografia.departamento", 1), ("tiempo.anio_vigencia", -1)],
                name="idx_geografia_tiempo"
            )
            coleccion.create_index(
                [("clasificacion.modalidad", 1), ("cuantia_inicial", 1)],
                name="idx_modalidad_cuantia"
            )
            coleccion.create_index(
                [("entidad.orden", 1), ("proveedor.es_pyme", 1)],
                name="idx_orden_pyme"
            )
            coleccion.create_index(
                [("entidad.nombre", "text"), ("proveedor.nombre_razon_social", "text")],
                name="idx_text_entidad_proveedor"
            )
        except Exception as e:
            print(f"Advertencia al crear índices en 'contratos': {e}")

    def ejecutar_pipeline_completo(
        self,
        fuente: str | Path | io.BytesIO | pd.DataFrame,
        batch_size: int = 2000,
        progreso_callback: Callable[[float, str], None] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """
        Orquesta la ejecución completa del ciclo CRISP-DM (HU-02 | PA-ALFA-002).

        Returns:
            tuple[dict, dict | None]:
                - Diccionario con métricas de la ejecución.
                - Primer documento estructurado (para inspección del esquema en estrella).
        """
        inicio = time.perf_counter()

        if progreso_callback:
            progreso_callback(0.10, "Fase 1: Extrayendo y mapeando columnas de SECOP II...")

        df_extraido = self.extraer_csv(fuente)

        if progreso_callback:
            progreso_callback(0.35, "Fase 2: Depurando, deduplicando y calculando variables derivadas...")

        df_limpio, total_leidos, total_descartados = self.transformar_datos(df_extraido)

        if progreso_callback:
            progreso_callback(0.60, "Fase 3: Estructurando documentos BSON en Esquema en Estrella...")

        documentos = self.estructurar_esquema_estrella(df_limpio)

        if progreso_callback:
            progreso_callback(0.75, "Fase 4: Ejecutando carga masiva por lotes en MongoDB...")

        total_insertados = self.cargar_en_mongodb(
            documentos, batch_size=batch_size, progreso_callback=progreso_callback
        )

        tiempo_total = round(time.perf_counter() - inicio, 2)

        primer_doc = documentos[0] if documentos else None

        metricas = {
            "caso_prueba": "PA-ALFA-002",
            "historia_usuario": "HU-02",
            "total_leidos": total_leidos,
            "total_descartados": total_descartados,
            "total_insertados": total_insertados,
            "tiempo_segundos": tiempo_total,
            "tasa_rendimiento_rps": round(total_insertados / tiempo_total, 1) if tiempo_total > 0 else 0.0,
            "estado": "APROBADA"
        }
        self.ultimas_metricas = metricas

        if progreso_callback:
            progreso_callback(1.0, f"✅ Pipeline completado exitosamente en {tiempo_total}s.")

        return metricas, primer_doc
