"""
Controlador de Analítica Descriptiva y Agregación Financiera
Historia de Usuario: HU-19 (Tarjetas KPI de Volumen y Presupuesto Global)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
from typing import Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.database.connection import MongoConnectionSingleton


class AnalyticsController:
    """
    Controlador de Analítica Descriptiva.
    Calcula KPIs gerenciales y valida consistencia con Aggregation Pipelines de MongoDB.
    """

    @staticmethod
    def formatear_cop(valor: float, compacto: bool = False) -> str:
        """
        Formatea valores numéricos a Pesos Colombianos (COP).
        
        Args:
            valor (float): Monto numérico.
            compacto (bool): Si es True, abrevia cifras grandes (M, Mil M, Billones).
            
        Returns:
            str: Cadena formateada en Pesos Colombianos.
        """
        if pd.isna(valor) or valor == 0:
            return "$ 0 COP"
        if compacto:
            if abs(valor) >= 1_000_000_000_000:
                return f"$ {valor / 1_000_000_000_000:,.2f} Billones"
            if abs(valor) >= 1_000_000_000:
                return f"$ {valor / 1_000_000_000:,.2f} Mil M"
            if abs(valor) >= 1_000_000:
                return f"$ {valor / 1_000_000:,.1f} M"
        return f"$ {valor:,.0f} COP"

    @classmethod
    def calcular_kpis_volumen_presupuesto(cls, df: pd.DataFrame | None) -> dict[str, Any]:
        """
        Calcula las métricas de volumen contractual y presupuesto global
        sobre el DataFrame activo (filtrado o completo).
        
        Args:
            df (pd.DataFrame | None): DataFrame con los contratos a dimensionar.
            
        Returns:
            dict[str, Any]: Indicadores de volumen y cuantías consolidadas.
        """
        if df is None or df.empty:
            return {
                "total_contratos": 0,
                "cuantia_inicial_total": 0.0,
                "valor_adiciones_total": 0.0,
                "cuantia_final_total": 0.0,
                "cuantia_inicial_fmt": "$ 0 COP",
                "valor_adiciones_fmt": "$ 0 COP",
                "cuantia_final_fmt": "$ 0 COP",
                "cuantia_inicial_exacta": "$ 0 COP",
                "cuantia_final_exacta": "$ 0 COP",
            }

        total_contratos = int(len(df))

        col_inicial = None
        for c in ["cuantia_inicial", "valor_inicial", "cuantia"]:
            if c in df.columns:
                col_inicial = c
                break

        col_adiciones = None
        for c in ["valor_adiciones", "adiciones", "adiciones_presupuestales"]:
            if c in df.columns:
                col_adiciones = c
                break

        col_final = None
        for c in ["cuantia_final", "valor_final", "cuantia_total", "monto_total"]:
            if c in df.columns:
                col_final = c
                break

        cuantia_inicial = float(pd.to_numeric(df[col_inicial], errors="coerce").fillna(0.0).sum()) if col_inicial else 0.0
        valor_adiciones = float(pd.to_numeric(df[col_adiciones], errors="coerce").fillna(0.0).sum()) if col_adiciones else 0.0

        if col_final and col_final in df.columns:
            cuantia_final = float(pd.to_numeric(df[col_final], errors="coerce").fillna(0.0).sum())
        else:
            cuantia_final = cuantia_inicial + valor_adiciones

        return {
            "total_contratos": total_contratos,
            "cuantia_inicial_total": cuantia_inicial,
            "valor_adiciones_total": valor_adiciones,
            "cuantia_final_total": cuantia_final,
            "cuantia_inicial_fmt": cls.formatear_cop(cuantia_inicial, compacto=True),
            "valor_adiciones_fmt": cls.formatear_cop(valor_adiciones, compacto=True),
            "cuantia_final_fmt": cls.formatear_cop(cuantia_final, compacto=True),
            "cuantia_inicial_exacta": cls.formatear_cop(cuantia_inicial, compacto=False),
            "cuantia_final_exacta": cls.formatear_cop(cuantia_final, compacto=False),
        }

    @classmethod
    def agregar_volumen_presupuesto_mongo(cls, query_match: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Ejecuta el Aggregation Pipeline directamente en MongoDB ($match -> $group)
        para garantizar paridad matemática con el motor NoSQL.
        
        Args:
            query_match (dict[str, Any] | None): Filtro $match para acotar documentos.
            
        Returns:
            dict[str, Any]: Agregaciones consolidadas en base de datos.
        """
        try:
            col = MongoConnectionSingleton.get_collection("contratos")
            pipeline: list[dict[str, Any]] = []
            if query_match:
                pipeline.append({"$match": query_match})
            pipeline.append({
                "$group": {
                    "_id": None,
                    "total_contratos": {"$sum": 1},
                    "cuantia_inicial_total": {"$sum": "$cuantia_inicial"},
                    "valor_adiciones_total": {"$sum": "$valor_adiciones"},
                    "cuantia_final_total": {"$sum": "$cuantia_final"},
                }
            })
            resultado = list(col.aggregate(pipeline))
            if not resultado:
                return {
                    "total_contratos": 0,
                    "cuantia_inicial_total": 0.0,
                    "valor_adiciones_total": 0.0,
                    "cuantia_final_total": 0.0,
                }
            doc = resultado[0]
            doc.pop("_id", None)
            return {
                "total_contratos": int(doc.get("total_contratos", 0)),
                "cuantia_inicial_total": float(doc.get("cuantia_inicial_total", 0.0)),
                "valor_adiciones_total": float(doc.get("valor_adiciones_total", 0.0)),
                "cuantia_final_total": float(doc.get("cuantia_final_total", 0.0)),
            }
        except Exception:
            return {
                "total_contratos": 0,
                "cuantia_inicial_total": 0.0,
                "valor_adiciones_total": 0.0,
                "cuantia_final_total": 0.0,
            }

    @classmethod
    def calcular_kpis_sobrecostos_adiciones(cls, df: pd.DataFrame | None) -> dict[str, Any]:
        """
        HU-20: Calcula indicadores gerenciales de precisión en planeación fiscal:
        - Monto total de adiciones presupuestales (COP).
        - Porcentaje y conteo de contratos con adición.
        - Porcentaje promedio de incremento (sobrecosto) en contratos adicionados.
        - Valor promedio de cada adición ejecutada (COP).
        """
        if df is None or df.empty:
            return {
                "monto_adiciones_total": 0.0,
                "monto_adiciones_fmt": "$ 0 COP",
                "monto_adiciones_exacto": "$ 0 COP",
                "total_contratos": 0,
                "contratos_con_adicion": 0,
                "porcentaje_contratos_adicionados": 0.0,
                "porcentaje_adicionados_fmt": "0.0%",
                "incremento_promedio_pct": 0.0,
                "incremento_promedio_fmt": "0.0%",
                "adicion_promedio_cop": 0.0,
                "adicion_promedio_fmt": "$ 0 COP",
            }

        total_contratos = int(len(df))
        col_adiciones = None
        for c in ["valor_adiciones", "adiciones", "adiciones_presupuestales"]:
            if c in df.columns:
                col_adiciones = c
                break

        if col_adiciones and col_adiciones in df.columns:
            serie_adiciones = pd.to_numeric(df[col_adiciones], errors="coerce").fillna(0.0)
        else:
            serie_adiciones = pd.Series([0.0] * total_contratos, index=df.index)

        if "tiene_adicion" in df.columns:
            mascara_adicion = df["tiene_adicion"].astype(bool)
        else:
            mascara_adicion = serie_adiciones > 0

        contratos_con_adicion = int(mascara_adicion.sum())
        monto_adiciones_total = float(serie_adiciones.sum())
        porcentaje_adicionados = (contratos_con_adicion / total_contratos * 100.0) if total_contratos > 0 else 0.0

        # Cálculo de severidad del sobrecosto únicamente sobre los contratos que tuvieron adición
        if contratos_con_adicion > 0:
            df_adicionados = df[mascara_adicion]
            serie_adiciones_filtradas = serie_adiciones[mascara_adicion]
            adicion_promedio_cop = float(serie_adiciones_filtradas.mean())

            col_inicial = None
            for c in ["cuantia_inicial", "valor_inicial", "cuantia"]:
                if c in df_adicionados.columns:
                    col_inicial = c
                    break

            if col_inicial and col_inicial in df_adicionados.columns:
                cuantias_iniciales = pd.to_numeric(df_adicionados[col_inicial], errors="coerce").replace(0, pd.NA).dropna()
                if not cuantias_iniciales.empty:
                    adiciones_alineadas = serie_adiciones_filtradas.loc[cuantias_iniciales.index]
                    ratios = (adiciones_alineadas / cuantias_iniciales) * 100.0
                    incremento_promedio_pct = float(ratios.mean())
                else:
                    incremento_promedio_pct = 0.0
            else:
                incremento_promedio_pct = 0.0
        else:
            adicion_promedio_cop = 0.0
            incremento_promedio_pct = 0.0

        return {
            "monto_adiciones_total": monto_adiciones_total,
            "monto_adiciones_fmt": cls.formatear_cop(monto_adiciones_total, compacto=True),
            "monto_adiciones_exacto": cls.formatear_cop(monto_adiciones_total, compacto=False),
            "total_contratos": total_contratos,
            "contratos_con_adicion": contratos_con_adicion,
            "porcentaje_contratos_adicionados": round(porcentaje_adicionados, 2),
            "porcentaje_adicionados_fmt": f"{porcentaje_adicionados:.1f}%",
            "incremento_promedio_pct": round(incremento_promedio_pct, 2),
            "incremento_promedio_fmt": f"+{incremento_promedio_pct:.1f}%",
            "adicion_promedio_cop": adicion_promedio_cop,
            "adicion_promedio_fmt": cls.formatear_cop(adicion_promedio_cop, compacto=True),
        }

    @classmethod
    def agregar_sobrecostos_mongo(cls, query_match: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        HU-20: Ejecuta el Aggregation Pipeline en MongoDB para auditar adiciones presupuestales
        garantizando consistencia exacta con el cálculo en memoria.
        """
        try:
            col = MongoConnectionSingleton.get_collection("contratos")
            pipeline: list[dict[str, Any]] = []
            if query_match:
                pipeline.append({"$match": query_match})
            pipeline.append({
                "$group": {
                    "_id": None,
                    "total_contratos": {"$sum": 1},
                    "monto_adiciones_total": {"$sum": "$valor_adiciones"},
                    "contratos_con_adicion": {
                        "$sum": {"$cond": [{"$gt": ["$valor_adiciones", 0]}, 1, 0]}
                    }
                }
            })
            resultado = list(col.aggregate(pipeline))
            if not resultado:
                return {
                    "total_contratos": 0,
                    "monto_adiciones_total": 0.0,
                    "contratos_con_adicion": 0,
                    "porcentaje_contratos_adicionados": 0.0
                }

            doc = resultado[0]
            total = int(doc.get("total_contratos", 0))
            con_adic = int(doc.get("contratos_con_adicion", 0))
            pct = round((con_adic / total * 100.0), 2) if total > 0 else 0.0
            return {
                "total_contratos": total,
                "monto_adiciones_total": float(doc.get("monto_adiciones_total", 0.0)),
                "contratos_con_adicion": con_adic,
                "porcentaje_contratos_adicionados": pct
            }
        except Exception:
            return {
                "total_contratos": 0,
                "monto_adiciones_total": 0.0,
                "contratos_con_adicion": 0,
                "porcentaje_contratos_adicionados": 0.0
            }

    @classmethod
    def calcular_kpis_promedio_mediana(
        cls, df: pd.DataFrame | None, columna_cuantia: str = "cuantia_final"
    ) -> dict[str, Any]:
        """
        HU-21: Calcula indicadores de tendencia central y dispersión de cuantías contractuales:
        - Cuantía promedio por contrato (Media aritmética - COP).
        - Mediana contractual (Percentil 50 representativo - COP).
        - Ratio de distorsión / asimetría (Media / Mediana) con etiqueta cualitativa de sesgo.
        - Mayor cuantía adjudicada (Megaproyecto techo de contratación - COP).
        - Rango intercuartílico (IQR = Q75 - Q25) para análisis de dispersión robusta.
        """
        if df is None or df.empty:
            return {
                "cuantia_promedio": 0.0,
                "cuantia_promedio_fmt": "$ 0 COP",
                "cuantia_promedio_exacta": "$ 0 COP",
                "cuantia_mediana": 0.0,
                "cuantia_mediana_fmt": "$ 0 COP",
                "cuantia_mediana_exacta": "$ 0 COP",
                "ratio_distorsion": 0.0,
                "ratio_distorsion_fmt": "0.0x",
                "nivel_sesgo": "Sin datos",
                "cuantia_maxima": 0.0,
                "cuantia_maxima_fmt": "$ 0 COP",
                "cuantia_maxima_exacta": "$ 0 COP",
                "iqr_cop": 0.0,
                "iqr_fmt": "$ 0 COP",
            }

        col = None
        if columna_cuantia and columna_cuantia in df.columns:
            col = columna_cuantia
        else:
            for c in ["cuantia_final", "cuantia_inicial", "valor_del_contrato", "cuantia", "valor_total"]:
                if c in df.columns:
                    col = c
                    break

        if not col:
            return cls.calcular_kpis_promedio_mediana(pd.DataFrame())

        serie = pd.to_numeric(df[col], errors="coerce").dropna()
        if serie.empty:
            return cls.calcular_kpis_promedio_mediana(pd.DataFrame())

        promedio = float(serie.mean())
        mediana = float(serie.median())
        maximo = float(serie.max())
        q25 = float(serie.quantile(0.25))
        q75 = float(serie.quantile(0.75))
        iqr = float(q75 - q25)

        ratio = (promedio / mediana) if mediana > 0 else 0.0
        ratio_redondeado = round(ratio, 2)

        if ratio >= 3.0:
            nivel_sesgo = "Alta distorsión por atípicos"
        elif ratio >= 1.5:
            nivel_sesgo = "Sesgo moderado a la derecha"
        elif ratio > 0.0:
            nivel_sesgo = "Distribución equilibrada"
        else:
            nivel_sesgo = "Sin datos"

        return {
            "cuantia_promedio": promedio,
            "cuantia_promedio_fmt": cls.formatear_cop(promedio, compacto=True),
            "cuantia_promedio_exacta": cls.formatear_cop(promedio, compacto=False),
            "cuantia_mediana": mediana,
            "cuantia_mediana_fmt": cls.formatear_cop(mediana, compacto=True),
            "cuantia_mediana_exacta": cls.formatear_cop(mediana, compacto=False),
            "ratio_distorsion": ratio_redondeado,
            "ratio_distorsion_fmt": f"{ratio:.1f}x",
            "nivel_sesgo": nivel_sesgo,
            "cuantia_maxima": maximo,
            "cuantia_maxima_fmt": cls.formatear_cop(maximo, compacto=True),
            "cuantia_maxima_exacta": cls.formatear_cop(maximo, compacto=False),
            "iqr_cop": iqr,
            "iqr_fmt": cls.formatear_cop(iqr, compacto=True),
        }

    @classmethod
    def agregar_tendencia_central_mongo(cls, query_match: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        HU-21: Ejecuta el Aggregation Pipeline en MongoDB para calcular promedio,
        mediana (vía $percentile o fallback algorítmico) y valor máximo sobre la colección contratos.
        """
        col = MongoConnectionSingleton.get_collection("contratos")
        match_stage = [{"$match": query_match}] if query_match else []

        # 1. Agregación estándar para promedio, máximo y conteo
        try:
            pipeline_basico = match_stage + [
                {
                    "$group": {
                        "_id": None,
                        "cuantia_promedio": {"$avg": "$cuantia_final"},
                        "cuantia_maxima": {"$max": "$cuantia_final"},
                        "total": {"$sum": 1},
                    }
                }
            ]
            res_basico = list(col.aggregate(pipeline_basico))
            if not res_basico or res_basico[0].get("total", 0) == 0:
                return {
                    "cuantia_promedio": 0.0,
                    "cuantia_mediana": 0.0,
                    "cuantia_maxima": 0.0,
                }

            doc_basico = res_basico[0]
            total = int(doc_basico.get("total", 0))
            promedio = float(doc_basico.get("cuantia_promedio") or 0.0)
            maximo = float(doc_basico.get("cuantia_maxima") or 0.0)

            # 2. Intento de obtención de mediana mediante $percentile nativo
            try:
                pipeline_percentile = match_stage + [
                    {
                        "$group": {
                            "_id": None,
                            "mediana_arr": {
                                "$percentile": {
                                    "input": "$cuantia_final",
                                    "p": [0.5],
                                    "method": "approximate",
                                }
                            },
                        }
                    }
                ]
                res_p = list(col.aggregate(pipeline_percentile))
                if res_p and res_p[0].get("mediana_arr") and res_p[0]["mediana_arr"][0] is not None:
                    mediana = float(res_p[0]["mediana_arr"][0])
                    return {
                        "cuantia_promedio": promedio,
                        "cuantia_mediana": mediana,
                        "cuantia_maxima": maximo,
                    }
            except Exception:
                pass

            # 3. Fallback determinista para mediana usando skip y limit
            skip_count = total // 2
            cursor = (
                col.find(query_match or {}, {"cuantia_final": 1})
                .sort("cuantia_final", 1)
                .skip(skip_count)
                .limit(1)
            )
            doc_med = list(cursor)
            mediana = float(doc_med[0].get("cuantia_final", 0.0)) if doc_med else 0.0

            return {
                "cuantia_promedio": promedio,
                "cuantia_mediana": mediana,
                "cuantia_maxima": maximo,
            }
        except Exception:
            return {
                "cuantia_promedio": 0.0,
                "cuantia_mediana": 0.0,
                "cuantia_maxima": 0.0,
            }

    @classmethod
    def obtener_gasto_por_modalidad(cls, df: pd.DataFrame | None) -> pd.DataFrame:
        """
        HU-22: Agrupa el conjunto activo por modalidad de contratación, calculando
        cuantía acumulada, cantidad de contratos y porcentaje de participación.
        """
        columnas_salida = ["modalidad", "monto_total", "cantidad_contratos", "participacion_pct", "monto_fmt"]
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_salida)

        col_mod = None
        for c in ["modalidad", "clasificacion.modalidad", "modalidad_de_contratacion", "modalidad_contratacion"]:
            if c in df.columns:
                col_mod = c
                break

        col_cuantia = None
        for c in ["cuantia_final", "cuantia_inicial", "valor_del_contrato", "cuantia", "valor_total", "monto_total"]:
            if c in df.columns:
                col_cuantia = c
                break

        if not col_mod or not col_cuantia:
            return pd.DataFrame(columns=columnas_salida)

        df_temp = df[[col_mod, col_cuantia]].copy()
        df_temp[col_mod] = df_temp[col_mod].astype(object).fillna("NO REGISTRA").astype(str).str.strip()
        df_temp[col_cuantia] = pd.to_numeric(df_temp[col_cuantia], errors="coerce").fillna(0.0)

        agrupado = (
            df_temp.groupby(col_mod, as_index=False)
            .agg(
                monto_total=(col_cuantia, "sum"),
                cantidad_contratos=(col_cuantia, "count")
            )
            .sort_values(by="monto_total", ascending=False)
            .reset_index(drop=True)
        )

        agrupado["monto_total"] = agrupado["monto_total"].astype(float)
        agrupado["cantidad_contratos"] = agrupado["cantidad_contratos"].astype(int)

        gran_total = agrupado["monto_total"].sum()
        agrupado["participacion_pct"] = (
            (agrupado["monto_total"] / gran_total * 100.0) if gran_total > 0 else 0.0
        )
        agrupado["monto_fmt"] = agrupado["monto_total"].apply(lambda x: cls.formatear_cop(float(x), compacto=True))

        if col_mod != "modalidad":
            agrupado = agrupado.rename(columns={col_mod: "modalidad"})

        return agrupado[columnas_salida]

    @classmethod
    def generar_grafica_gasto_modalidad(cls, df: pd.DataFrame | None, es_oscuro: bool = False) -> go.Figure:
        """
        HU-22: Construye la gráfica interactiva de barras horizontales con estética ejecutiva
        para auditar el gasto acumulado según la modalidad de selección.
        """
        df_mod = cls.obtener_gasto_por_modalidad(df)

        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_eje = "#CBD5E1" if es_oscuro else "#334155"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_grid = "#334155" if es_oscuro else "#F1F5F9"

        if df_mod.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin registros disponibles para los filtros seleccionados",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color=color_texto_sub)
            )
            fig.update_layout(
                plot_bgcolor=color_bg, paper_bgcolor=color_bg,
                xaxis=dict(visible=False), yaxis=dict(visible=False), height=360
            )
            return fig

        # Invertir orden para que la barra de mayor monto quede en la parte superior
        df_plot = df_mod.iloc[::-1].copy()

        # Resaltar Contratación Directa en índigo intenso y las demás en azul corporativo suave
        colores = [
            "#4F46E5" if "DIRECTA" in str(m).upper() else "#93C5FD"
            for m in df_plot["modalidad"]
        ]

        fig = go.Figure(
            go.Bar(
                x=df_plot["monto_total"],
                y=df_plot["modalidad"],
                orientation="h",
                marker=dict(color=colores, cornerradius=6),
                text=df_plot.apply(lambda r: f"{r['monto_fmt']} ({r['participacion_pct']:.1f}%)", axis=1),
                textposition="outside",
                cliponaxis=False,
                customdata=df_plot[["cantidad_contratos", "participacion_pct"]],
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Cuantía Acumulada: $ %{x:,.0f} COP<br>"
                    "Contratos Adjudicados: %{customdata[0]:,}<br>"
                    "Participación del Gasto: %{customdata[1]:.2f}%"
                    "<extra></extra>"
                ),
            )
        )

        max_x = df_plot["monto_total"].max()
        fig.update_layout(
            title=dict(
                text="Gasto Público Acumulado por Modalidad de Selección (COP)",
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            margin=dict(l=10, r=90, t=48, b=20),
            height=max(360, len(df_plot) * 44 + 80),
            xaxis=dict(
                showgrid=True,
                gridcolor=color_grid,
                zeroline=False,
                tickprefix="$ ",
                tickformat="~s",
                range=[0, max_x * 1.28] if max_x > 0 else [0, 1],
                tickfont=dict(color=color_texto_sub, size=11)
            ),
            yaxis=dict(
                showgrid=False,
                tickfont=dict(color=color_texto_eje, size=12)
            ),
            hoverlabel=dict(
                bgcolor="#0F172A",
                font_size=12,
                font_color="#FFFFFF"
            )
        )
        return fig

    @classmethod
    def agregar_gasto_modalidad_mongo(cls, query_match: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        HU-22: Ejecuta el Aggregation Pipeline directamente en MongoDB ($match -> $group -> $sort)
        sobre clasificacion.modalidad para garantizar paridad con la vista.
        """
        try:
            col = MongoConnectionSingleton.get_collection("contratos")
            pipeline: list[dict[str, Any]] = []
            if query_match:
                pipeline.append({"$match": query_match})
            pipeline.extend([
                {
                    "$group": {
                        "_id": "$clasificacion.modalidad",
                        "monto_total": {"$sum": "$cuantia_final"},
                        "cantidad_contratos": {"$sum": 1}
                    }
                },
                {"$sort": {"monto_total": -1}}
            ])
            return list(col.aggregate(pipeline))
        except Exception:
            return []

    @classmethod
    def obtener_serie_temporal_gasto(
        cls, df: pd.DataFrame | None, granularidad: str = "Mensual"
    ) -> pd.DataFrame:
        """
        HU-23: Agrupa cronológicamente los contratos por mes o por año de vigencia (2021-2026),
        calculando cuantía consolidada, adiciones y volumen de procesos.
        """
        columnas_salida = [
            "periodo", "anio_vigencia", "mes_vigencia",
            "cuantia_total", "adiciones_total", "cantidad_contratos", "monto_fmt"
        ]
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_salida)

        df_temp = df.copy()

        col_anio = None
        for c in ["anio_vigencia", "tiempo.anio_vigencia", "anio_firma", "anno_vigencia", "anio"]:
            if c in df_temp.columns:
                col_anio = c
                break

        col_mes = None
        for c in ["mes_vigencia", "tiempo.mes_vigencia", "mes_firma", "mes"]:
            if c in df_temp.columns:
                col_mes = c
                break

        if not col_anio or not col_mes:
            for c_fec in ["fecha_firma", "fecha_de_firma", "tiempo.fecha_firma"]:
                if c_fec in df_temp.columns:
                    fec_dt = pd.to_datetime(df_temp[c_fec], errors="coerce")
                    if not col_anio:
                        df_temp["anio_vigencia"] = fec_dt.dt.year.fillna(2022).astype(int)
                        col_anio = "anio_vigencia"
                    if not col_mes:
                        df_temp["mes_vigencia"] = fec_dt.dt.month.fillna(1).astype(int)
                        col_mes = "mes_vigencia"
                    break

        col_cuantia = None
        for c in ["cuantia_final", "cuantia_inicial", "valor_del_contrato", "cuantia", "valor_total", "monto_total"]:
            if c in df_temp.columns:
                col_cuantia = c
                break

        col_adic = None
        for c in ["valor_adiciones", "adiciones", "adiciones_presupuestales"]:
            if c in df_temp.columns:
                col_adic = c
                break

        # Garantizar tipos numéricos válidos para agregación temporal
        df_temp["anio_tmp"] = (
            pd.to_numeric(df_temp[col_anio], errors="coerce").fillna(2022).astype(int)
            if col_anio and col_anio in df_temp.columns
            else 2022
        )
        df_temp["mes_tmp"] = (
            pd.to_numeric(df_temp[col_mes], errors="coerce").fillna(1).astype(int).clip(1, 12)
            if col_mes and col_mes in df_temp.columns
            else 1
        )
        df_temp["cuantia_tmp"] = (
            pd.to_numeric(df_temp[col_cuantia], errors="coerce").fillna(0.0)
            if col_cuantia and col_cuantia in df_temp.columns
            else 0.0
        )
        df_temp["adic_tmp"] = (
            pd.to_numeric(df_temp[col_adic], errors="coerce").fillna(0.0)
            if col_adic and col_adic in df_temp.columns
            else 0.0
        )

        if str(granularidad).strip().lower() in ["anual", "año", "años"]:
            agrupado = (
                df_temp.groupby("anio_tmp", as_index=False)
                .agg(
                    cuantia_total=("cuantia_tmp", "sum"),
                    adiciones_total=("adic_tmp", "sum"),
                    cantidad_contratos=("cuantia_tmp", "count")
                )
                .sort_values(by="anio_tmp", ascending=True)
                .reset_index(drop=True)
            )
            agrupado["anio_vigencia"] = agrupado["anio_tmp"]
            agrupado["mes_vigencia"] = 1
            agrupado["periodo"] = agrupado["anio_tmp"].astype(str)
        else:
            agrupado = (
                df_temp.groupby(["anio_tmp", "mes_tmp"], as_index=False)
                .agg(
                    cuantia_total=("cuantia_tmp", "sum"),
                    adiciones_total=("adic_tmp", "sum"),
                    cantidad_contratos=("cuantia_tmp", "count")
                )
                .sort_values(by=["anio_tmp", "mes_tmp"], ascending=[True, True])
                .reset_index(drop=True)
            )
            agrupado["anio_vigencia"] = agrupado["anio_tmp"]
            agrupado["mes_vigencia"] = agrupado["mes_tmp"]
            agrupado["periodo"] = agrupado.apply(
                lambda r: f"{int(r['anio_tmp'])}-{int(r['mes_tmp']):02d}", axis=1
            )

        agrupado["cuantia_total"] = agrupado["cuantia_total"].astype(float)
        agrupado["adiciones_total"] = agrupado["adiciones_total"].astype(float)
        agrupado["cantidad_contratos"] = agrupado["cantidad_contratos"].astype(int)
        agrupado["monto_fmt"] = agrupado["cuantia_total"].apply(lambda x: cls.formatear_cop(float(x), compacto=True))
        return agrupado[columnas_salida]

    @classmethod
    def generar_grafica_serie_temporal(
        cls, df: pd.DataFrame | None, granularidad: str = "Mensual", es_oscuro: bool = False
    ) -> go.Figure:
        """
        HU-23: Construye el gráfico interactivo de línea suavizada (spline) con relleno degradado
        para analizar la evolución temporal y estacionalidad del gasto público.
        """
        df_ts = cls.obtener_serie_temporal_gasto(df, granularidad=granularidad)

        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_eje = "#CBD5E1" if es_oscuro else "#475569"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_grid = "#334155" if es_oscuro else "#F1F5F9"

        if df_ts.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin datos cronológicos disponibles para los filtros seleccionados",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color=color_texto_sub)
            )
            fig.update_layout(
                plot_bgcolor=color_bg, paper_bgcolor=color_bg,
                xaxis=dict(visible=False), yaxis=dict(visible=False), height=360
            )
            return fig

        fig = go.Figure()

        # Serie principal: Cuantía Total Contratada
        fig.add_trace(
            go.Scatter(
                x=df_ts["periodo"],
                y=df_ts["cuantia_total"],
                mode="lines+markers",
                name="Cuantía Consolidada",
                line=dict(color="#4F46E5", width=3, shape="spline", smoothing=0.8),
                marker=dict(size=7, color="#FFFFFF", line=dict(color="#4F46E5", width=2.5)),
                fill="tozeroy",
                fillcolor="rgba(79, 70, 229, 0.08)",
                customdata=df_ts[["cantidad_contratos", "adiciones_total"]],
                hovertemplate=(
                    "<b>Periodo: %{x}</b><br>"
                    "Cuantía Total: $ %{y:,.0f} COP<br>"
                    "Adiciones en Periodo: $ %{customdata[1]:,.0f} COP<br>"
                    "Contratos Formalizados: %{customdata[0]:,}"
                    "<extra></extra>"
                ),
            )
        )

        # Serie secundaria: Adiciones Presupuestales
        fig.add_trace(
            go.Scatter(
                x=df_ts["periodo"],
                y=df_ts["adiciones_total"],
                mode="lines+markers",
                name="Adiciones Presupuestales",
                line=dict(color="#0EA5E9", width=2, dash="dot", shape="spline", smoothing=0.8),
                marker=dict(size=5, color="#0EA5E9"),
                hovertemplate="<b>Periodo: %{x}</b><br>Adiciones: $ %{y:,.0f} COP<extra></extra>",
            )
        )

        fig.update_layout(
            title=dict(
                text=f"Evolución {granularidad} del Gasto Contractual (COP)",
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            margin=dict(l=10, r=20, t=52, b=20),
            height=370,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=12, color=color_texto_eje)
            ),
            xaxis=dict(
                type="category",
                showgrid=False,
                tickangle=-35 if len(df_ts) > 12 else 0,
                tickfont=dict(color=color_texto_sub, size=11)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=color_grid,
                zeroline=False,
                tickprefix="$ ",
                tickformat="~s",
                tickfont=dict(color=color_texto_sub, size=11)
            ),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="#0F172A",
                font_size=12,
                font_color="#FFFFFF"
            )
        )
        return fig

    @classmethod
    def agregar_serie_temporal_mongo(cls, query_match: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        HU-23: Ejecuta el Aggregation Pipeline en MongoDB ($match -> $group -> $sort)
        agrupando por tiempo.anio_vigencia y tiempo.mes_vigencia.
        """
        try:
            col = MongoConnectionSingleton.get_collection("contratos")
            pipeline: list[dict[str, Any]] = []
            if query_match:
                pipeline.append({"$match": query_match})
            pipeline.extend([
                {
                    "$group": {
                        "_id": {
                            "anio": "$tiempo.anio_vigencia",
                            "mes": "$tiempo.mes_vigencia"
                        },
                        "cuantia_total": {"$sum": "$cuantia_final"},
                        "adiciones_total": {"$sum": "$valor_adiciones"},
                        "cantidad_contratos": {"$sum": 1}
                    }
                },
                {"$sort": {"_id.anio": 1, "_id.mes": 1}}
            ])
            return list(col.aggregate(pipeline))
        except Exception:
            return []

    @classmethod
    def obtener_top_entidades(cls, df: pd.DataFrame | None, top_n: int = 10) -> pd.DataFrame:
        """
        HU-24: Clasifica las N entidades estatales con mayor presupuesto ejecutado (cuantia_final)
        sobre el conjunto activo, calculando volumen contractual y adiciones.
        """
        columnas_salida = [
            "entidad", "entidad_corta", "monto_total", "adiciones_total",
            "cantidad_contratos", "participacion_pct", "monto_fmt"
        ]
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_salida)

        col_entidad = None
        for c in ["entidad", "nombre_entidad", "entidad.nombre", "nombre_de_la_entidad", "entidad_compradora"]:
            if c in df.columns:
                col_entidad = c
                break

        col_cuantia = None
        for c in ["cuantia_final", "cuantia_inicial", "valor_del_contrato", "cuantia", "valor_total", "monto_total"]:
            if c in df.columns:
                col_cuantia = c
                break

        col_adic = None
        for c in ["valor_adiciones", "adiciones", "adiciones_presupuestales"]:
            if c in df.columns:
                col_adic = c
                break

        if not col_entidad or not col_cuantia:
            return pd.DataFrame(columns=columnas_salida)

        df_temp = df.copy()
        df_temp[col_entidad] = df_temp[col_entidad].astype(object).fillna("ENTIDAD NO ESPECIFICADA").astype(str).str.strip()
        df_temp[col_cuantia] = pd.to_numeric(df_temp[col_cuantia], errors="coerce").fillna(0.0)
        df_temp["adic_tmp"] = (
            pd.to_numeric(df_temp[col_adic], errors="coerce").fillna(0.0)
            if col_adic and col_adic in df_temp.columns
            else 0.0
        )

        gran_total = float(df_temp[col_cuantia].sum())

        agrupado = (
            df_temp.groupby(col_entidad, as_index=False)
            .agg(
                monto_total=(col_cuantia, "sum"),
                adiciones_total=("adic_tmp", "sum"),
                cantidad_contratos=(col_cuantia, "count")
            )
            .sort_values(by="monto_total", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

        agrupado["monto_total"] = agrupado["monto_total"].astype(float)
        agrupado["adiciones_total"] = agrupado["adiciones_total"].astype(float)
        agrupado["cantidad_contratos"] = agrupado["cantidad_contratos"].astype(int)

        agrupado["participacion_pct"] = (
            (agrupado["monto_total"] / gran_total * 100.0) if gran_total > 0 else 0.0
        )
        agrupado["monto_fmt"] = agrupado["monto_total"].apply(lambda x: cls.formatear_cop(float(x), compacto=True))

        if col_entidad != "entidad":
            agrupado = agrupado.rename(columns={col_entidad: "entidad"})

        agrupado["entidad_corta"] = agrupado["entidad"].apply(
            lambda s: s if len(s) <= 38 else s[:35].rstrip() + "..."
        )
        return agrupado[columnas_salida]

    @classmethod
    def generar_grafica_top_entidades(
        cls, df: pd.DataFrame | None, top_n: int = 10, es_oscuro: bool = False
    ) -> go.Figure:
        """
        HU-24: Construye el gráfico interactivo de barras horizontales clasificadas
        con el Top 10 de entidades estatales de mayor ejecución presupuestal.
        """
        df_top = cls.obtener_top_entidades(df, top_n=top_n)

        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_eje = "#CBD5E1" if es_oscuro else "#334155"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_grid = "#334155" if es_oscuro else "#F1F5F9"

        if df_top.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin entidades registradas para los filtros seleccionados",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color=color_texto_sub)
            )
            fig.update_layout(
                plot_bgcolor=color_bg, paper_bgcolor=color_bg,
                xaxis=dict(visible=False), yaxis=dict(visible=False), height=420
            )
            return fig

        # Invertir orden para ubicar el puesto #1 en la parte superior
        df_plot = df_top.iloc[::-1].copy()

        # Gradiente sutil corporativo destacando el Top 3 en índigo intenso
        total_barras = len(df_plot)
        colores = [
            "#4F46E5" if idx >= total_barras - 3 else "#818CF8"
            for idx in range(total_barras)
        ]

        fig = go.Figure(
            go.Bar(
                x=df_plot["monto_total"],
                y=df_plot["entidad_corta"],
                orientation="h",
                marker=dict(color=colores, cornerradius=6),
                text=df_plot["monto_fmt"],
                textposition="outside",
                cliponaxis=False,
                customdata=df_plot[["entidad", "cantidad_contratos", "adiciones_total", "participacion_pct"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Presupuesto Ejecutado: $ %{x:,.0f} COP<br>"
                    "Adiciones Acumuladas: $ %{customdata[2]:,.0f} COP<br>"
                    "Contratos Adjudicados: %{customdata[1]:,}<br>"
                    "Participación sobre Selección: %{customdata[3]:.2f}%"
                    "<extra></extra>"
                ),
            )
        )

        max_x = df_plot["monto_total"].max()
        fig.update_layout(
            title=dict(
                text=f"Top {top_n} Entidades Estatales por Presupuesto Ejecutado (COP)",
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            margin=dict(l=10, r=85, t=48, b=20),
            height=max(360, len(df_plot) * 38 + 90),
            xaxis=dict(
                showgrid=True,
                gridcolor=color_grid,
                zeroline=False,
                tickprefix="$ ",
                tickformat="~s",
                range=[0, max_x * 1.25] if max_x > 0 else [0, 1],
                tickfont=dict(color=color_texto_sub, size=11)
            ),
            yaxis=dict(
                showgrid=False,
                tickfont=dict(color=color_texto_eje, size=11)
            ),
            hoverlabel=dict(
                bgcolor="#0F172A",
                font_size=12,
                font_color="#FFFFFF"
            )
        )
        return fig

    @classmethod
    def agregar_top_entidades_mongo(
        cls, query_match: dict[str, Any] | None = None, top_n: int = 10
    ) -> list[dict[str, Any]]:
        """
        HU-24: Ejecuta el Aggregation Pipeline directamente en MongoDB ($match -> $group -> $sort -> $limit)
        sobre entidad.nombre para certificar paridad con el motor NoSQL.
        """
        try:
            col = MongoConnectionSingleton.get_collection("contratos")
            pipeline: list[dict[str, Any]] = []
            if query_match:
                pipeline.append({"$match": query_match})
            pipeline.extend([
                {
                    "$group": {
                        "_id": "$entidad.nombre",
                        "monto_total": {"$sum": "$cuantia_final"},
                        "adiciones_total": {"$sum": "$valor_adiciones"},
                        "cantidad_contratos": {"$sum": 1}
                    }
                },
                {"$sort": {"monto_total": -1}},
                {"$limit": int(top_n)}
            ])
            return list(col.aggregate(pipeline))
        except Exception:
            return []

    @classmethod
    def obtener_distribucion_estados(
        cls, df: pd.DataFrame | None, max_categorias: int = 6
    ) -> pd.DataFrame:
        """
        HU-25: Agrupa los contratos del subconjunto activo según su estado contractual
        (Terminado, En ejecución, Modificado, Celebrado, etc.), calculando conteo,
        porcentaje de participación y cuantía asociada.
        """
        columnas_salida = ["estado", "cantidad_contratos", "porcentaje", "monto_total", "monto_fmt"]
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_salida)

        col_estado = None
        for c in ["estado", "estado_contrato", "clasificacion.estado", "estado_del_contrato"]:
            if c in df.columns:
                col_estado = c
                break

        col_cuantia = None
        for c in ["cuantia_final", "cuantia_inicial", "valor_del_contrato", "cuantia", "valor_total", "monto_total"]:
            if c in df.columns:
                col_cuantia = c
                break

        df_temp = df.copy()
        if col_estado and col_estado in df_temp.columns:
            df_temp["estado_clean"] = (
                df_temp[col_estado]
                .astype(object)
                .fillna("SIN ESTADO DEFINIDO")
                .astype(str)
                .str.strip()
                .replace({"": "SIN ESTADO DEFINIDO", "nan": "SIN ESTADO DEFINIDO", "None": "SIN ESTADO DEFINIDO"})
            )
        else:
            df_temp["estado_clean"] = "SIN ESTADO DEFINIDO"

        df_temp["cuantia_tmp"] = (
            pd.to_numeric(df_temp[col_cuantia], errors="coerce").fillna(0.0)
            if col_cuantia and col_cuantia in df_temp.columns
            else 0.0
        )

        agrupado = (
            df_temp.groupby("estado_clean", as_index=False)
            .agg(
                cantidad_contratos=("estado_clean", "count"),
                monto_total=("cuantia_tmp", "sum")
            )
            .sort_values(by="cantidad_contratos", ascending=False)
            .reset_index(drop=True)
        )

        # Consolidar categorías marginales si superan max_categorias
        if len(agrupado) > max_categorias:
            principales = agrupado.iloc[: max_categorias - 1].copy()
            resto = agrupado.iloc[max_categorias - 1 :]
            fila_otros = pd.DataFrame([{
                "estado_clean": "Otros estados",
                "cantidad_contratos": int(resto["cantidad_contratos"].sum()),
                "monto_total": float(resto["monto_total"].sum()),
            }])
            agrupado = pd.concat([principales, fila_otros], ignore_index=True)

        agrupado["cantidad_contratos"] = agrupado["cantidad_contratos"].astype(int)
        agrupado["monto_total"] = agrupado["monto_total"].astype(float)

        total_contratos = agrupado["cantidad_contratos"].sum()
        agrupado["porcentaje"] = (
            (agrupado["cantidad_contratos"] / total_contratos * 100.0) if total_contratos > 0 else 0.0
        )
        agrupado["monto_fmt"] = agrupado["monto_total"].apply(lambda x: cls.formatear_cop(float(x), compacto=True))
        agrupado = agrupado.rename(columns={"estado_clean": "estado"})
        return agrupado[columnas_salida]

    @classmethod
    def generar_grafica_dona_estados(
        cls, df: pd.DataFrame | None, max_categorias: int = 6, es_oscuro: bool = False
    ) -> go.Figure:
        """
        HU-25: Construye un gráfico de dona interactivo con estética ejecutiva tipo Figma
        para vigilar la proporción de contratos por estado actual.
        """
        df_est = cls.obtener_distribucion_estados(df, max_categorias=max_categorias)

        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_centro = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_borde = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_slice = "#F8FAFC" if es_oscuro else "#334155"

        if df_est.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin registros de estado disponibles para los filtros activos",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color=color_texto_sub)
            )
            fig.update_layout(
                plot_bgcolor=color_bg, paper_bgcolor=color_bg,
                xaxis=dict(visible=False), yaxis=dict(visible=False), height=380
            )
            return fig

        total_procesos = int(df_est["cantidad_contratos"].sum())
        paleta_figma = ["#4F46E5", "#38BDF8", "#10B981", "#F59E0B", "#F43F5E", "#94A3B8"]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=df_est["estado"],
                    values=df_est["cantidad_contratos"],
                    hole=0.64,
                    sort=False,
                    marker=dict(
                        colors=paleta_figma[: len(df_est)],
                        line=dict(color=color_borde, width=3)
                    ),
                    textinfo="percent",
                    textposition="outside",
                    textfont=dict(size=12, color=color_texto_slice),
                    customdata=df_est[["monto_total", "monto_fmt"]],
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Contratos: %{value:,} (%{percent})<br>"
                        "Cuantía Asociada: $ %{customdata[0]:,.0f} COP"
                        "<extra></extra>"
                    ),
                )
            ]
        )

        # Indicador central dentro del anillo de la dona
        fig.add_annotation(
            text=f"<b>{total_procesos:,}</b><br><span style='font-size:12px; color:{color_texto_sub};'>Contratos</span>",
            x=0.5,
            y=0.5,
            font=dict(size=20, color=color_texto_centro, family="Inter, sans-serif"),
            showarrow=False,
        )

        fig.update_layout(
            title=dict(
                text="Distribución de Procesos por Estado Contractual",
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            margin=dict(l=15, r=15, t=52, b=45),
            height=390,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.08,
                xanchor="center",
                x=0.5,
                font=dict(size=12, color=color_texto_sub)
            ),
            hoverlabel=dict(
                bgcolor="#0F172A",
                font_size=12,
                font_color="#FFFFFF"
            )
        )
        return fig

    @classmethod
    def agregar_estados_mongo(cls, query_match: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        HU-25: Ejecuta el Aggregation Pipeline directamente en MongoDB ($match -> $group -> $sort)
        sobre clasificacion.estado para garantizar paridad con la vista.
        """
        try:
            col = MongoConnectionSingleton.get_collection("contratos")
            pipeline: list[dict[str, Any]] = []
            if query_match:
                pipeline.append({"$match": query_match})
            pipeline.extend([
                {
                    "$group": {
                        "_id": "$clasificacion.estado",
                        "cantidad_contratos": {"$sum": 1},
                        "monto_total": {"$sum": "$cuantia_final"}
                    }
                },
                {"$sort": {"cantidad_contratos": -1}}
            ])
            return list(col.aggregate(pipeline))
        except Exception:
            return []

    @classmethod
    def obtener_estadisticas_dispersion_tipo(
        cls,
        df: pd.DataFrame | None,
        metrica: str = "cuantia_final",
        top_tipos: int = 8
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        HU-26: Prepara los datos filtrados por las principales tipologías contractuales
        y calcula el resumen estadístico (Q1, Mediana, Q3, IQR, Máximo y Atípicos).
        Retorna: (DataFrame depurado para el Boxplot, DataFrame resumen de cuartiles).
        """
        cols_resumen = ["tipo_contrato", "cantidad", "q1", "mediana", "q3", "iqr", "maximo", "outliers_count"]
        if df is None or df.empty:
            return pd.DataFrame(), pd.DataFrame(columns=cols_resumen)

        col_tipo = None
        for c in ["tipo_contrato", "tipo_de_contrato", "clasificacion.tipo_contrato", "tipo"]:
            if c in df.columns:
                col_tipo = c
                break

        col_valor = None
        if metrica in df.columns:
            col_valor = metrica
        elif metrica in ["plazo_dias", "duracion_dias", "plazo"]:
            for c in ["plazo_dias", "duracion_dias", "plazo_ejecucion_dias", "dias_duracion"]:
                if c in df.columns:
                    col_valor = c
                    break
        else:
            for c in ["cuantia_final", "cuantia_inicial", "valor_del_contrato", "cuantia", "monto_total"]:
                if c in df.columns:
                    col_valor = c
                    break

        if not col_tipo or not col_valor or col_tipo not in df.columns or col_valor not in df.columns:
            return pd.DataFrame(), pd.DataFrame(columns=cols_resumen)

        df_temp = df[[col_tipo, col_valor]].copy()
        df_temp["tipo_clean"] = df_temp[col_tipo].astype(object).fillna("NO ESPECIFICADO").astype(str).str.strip()
        df_temp["valor_num"] = pd.to_numeric(df_temp[col_valor], errors="coerce")
        df_temp = df_temp.dropna(subset=["valor_num"])
        df_temp = df_temp[df_temp["valor_num"] > 0]

        if df_temp.empty:
            return pd.DataFrame(), pd.DataFrame(columns=cols_resumen)

        # Seleccionar los N tipos de contrato con mayor volumen de procesos para claridad visual
        top_categorias = df_temp["tipo_clean"].value_counts().head(top_tipos).index.tolist()
        df_plot = df_temp[df_temp["tipo_clean"].isin(top_categorias)].copy()

        filas_resumen = []
        for tipo, grupo in df_plot.groupby("tipo_clean"):
            vals = grupo["valor_num"]
            q1 = float(vals.quantile(0.25))
            med = float(vals.median())
            q3 = float(vals.quantile(0.75))
            iqr = q3 - q1
            limite_sup = q3 + 1.5 * iqr
            outliers = int((vals > limite_sup).sum())
            filas_resumen.append({
                "tipo_contrato": str(tipo),
                "cantidad": int(len(vals)),
                "q1": q1,
                "mediana": med,
                "q3": q3,
                "iqr": iqr,
                "maximo": float(vals.max()),
                "outliers_count": outliers,
            })

        if not filas_resumen:
            return pd.DataFrame(), pd.DataFrame(columns=cols_resumen)

        df_resumen = pd.DataFrame(filas_resumen).sort_values(by="mediana", ascending=False).reset_index(drop=True)
        return df_plot, df_resumen

    @classmethod
    def generar_grafica_boxplot_dispersion(
        cls,
        df: pd.DataFrame | None,
        metrica: str = "cuantia_final",
        escala_log: bool = True,
        top_tipos: int = 8,
        es_oscuro: bool = False
    ) -> go.Figure:
        """
        HU-26: Construye el diagrama de caja (Boxplot) interactivo en Plotly
        para analizar la dispersión y valores atípicos de cuantías o plazos por tipo de contrato.
        """
        df_plot, df_resumen = cls.obtener_estadisticas_dispersion_tipo(df, metrica=metrica, top_tipos=top_tipos)

        es_cuantia = metrica in ["cuantia_final", "cuantia_inicial", "valor_adiciones", "valor_del_contrato"]
        titulo_grafica = (
            "Dispersión de Cuantías Contractuales por Tipo de Contrato (COP)"
            if es_cuantia
            else "Dispersión de Plazos de Ejecución por Tipo de Contrato (Días)"
        )
        etiqueta_eje = "Cuantía Contractual (COP)" if es_cuantia else "Plazo de Ejecución (Días)"

        color_bg = "#1E293B" if es_oscuro else "#FFFFFF"
        color_texto_titulo = "#F8FAFC" if es_oscuro else "#0F172A"
        color_texto_eje = "#CBD5E1" if es_oscuro else "#334155"
        color_texto_sub = "#94A3B8" if es_oscuro else "#64748B"
        color_grid = "#334155" if es_oscuro else "#F1F5F9"

        if df_plot.empty or df_resumen.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin registros numéricos suficientes para construir el diagrama de caja",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color=color_texto_sub)
            )
            fig.update_layout(
                plot_bgcolor=color_bg, paper_bgcolor=color_bg,
                xaxis=dict(visible=False), yaxis=dict(visible=False), height=420
            )
            return fig

        paleta_cajas = ["#4F46E5", "#2563EB", "#0EA5E9", "#10B981", "#8B5CF6", "#F59E0B", "#6366F1", "#64748B"]
        fig = go.Figure()

        # Ordenar cajas según la mediana descendente
        for idx, fila in df_resumen.iterrows():
            tipo = fila["tipo_contrato"]
            sub_vals = df_plot[df_plot["tipo_clean"] == tipo]["valor_num"]
            color_caja = paleta_cajas[idx % len(paleta_cajas)]
            etiqueta_corta = tipo if len(tipo) <= 28 else tipo[:25].rstrip() + "..."

            fig.add_trace(
                go.Box(
                    y=sub_vals,
                    name=etiqueta_corta,
                    boxpoints="outliers",
                    jitter=0.25,
                    marker=dict(color=color_caja, size=5, opacity=0.65),
                    line=dict(color=color_caja, width=1.8),
                    fillcolor="rgba(79, 70, 229, 0.12)" if idx == 0 else "rgba(148, 163, 184, 0.12)",
                    hoverinfo="y+name",
                )
            )

        fig.update_layout(
            title=dict(
                text=titulo_grafica,
                font=dict(size=15, color=color_texto_titulo, family="Inter, sans-serif"),
                x=0
            ),
            plot_bgcolor=color_bg,
            paper_bgcolor=color_bg,
            showlegend=False,
            margin=dict(l=15, r=20, t=52, b=30),
            height=430,
            xaxis=dict(
                showgrid=False,
                tickangle=-20,
                tickfont=dict(color=color_texto_eje, size=11)
            ),
            yaxis=dict(
                title=dict(text=etiqueta_eje, font=dict(size=12, color=color_texto_sub)),
                type="log" if escala_log else "linear",
                showgrid=True,
                gridcolor=color_grid,
                zeroline=False,
                tickprefix="$ " if es_cuantia else "",
                tickfont=dict(color=color_texto_sub, size=11)
            ),
            hoverlabel=dict(
                bgcolor="#0F172A",
                font_size=12,
                font_color="#FFFFFF"
            )
        )
        return fig

    @classmethod
    def agregar_dispersion_tipo_mongo(cls, query_match: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        HU-26: Ejecuta el Aggregation Pipeline en MongoDB ($match -> $group -> $sort)
        sobre clasificacion.tipo_contrato para auditar extremos y promedios por tipología.
        """
        try:
            col = MongoConnectionSingleton.get_collection("contratos")
            pipeline: list[dict[str, Any]] = []
            if query_match:
                pipeline.append({"$match": query_match})
            pipeline.extend([
                {
                    "$group": {
                        "_id": "$clasificacion.tipo_contrato",
                        "cantidad_contratos": {"$sum": 1},
                        "cuantia_promedio": {"$avg": "$cuantia_final"},
                        "cuantia_maxima": {"$max": "$cuantia_final"},
                        "plazo_promedio_dias": {"$avg": "$plazo_dias"},
                        "plazo_maximo_dias": {"$max": "$plazo_dias"}
                    }
                },
                {"$sort": {"cantidad_contratos": -1}}
            ])
            return list(col.aggregate(pipeline))
        except Exception:
            return []

