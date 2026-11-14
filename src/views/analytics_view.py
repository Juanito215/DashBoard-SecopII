"""
Vista de Analítica y Tendencias de Contratación
Gráficas de Concentración del Gasto, Tipologías Contractuales y Participación PYME
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
from typing import Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.database.data_repository import get_data_repository
from src.controllers.analytics_controller import AnalyticsController
from src.views.components import render_topbar, render_kpi_card


def render_analytics_view(usuario: dict[str, Any]) -> None:
    """
    Renderiza el módulo de Analítica y Tendencias con gráficos corporativos de alta fidelidad.
    """
    render_topbar(
        titulo="Analítica y Tendencias",
        subtitulo="Patrones de concentración presupuestal, tipologías y participación de proveedores",
        etiqueta_fecha="Vigencias 2021 – 2026"
    )

    repo = get_data_repository()
    if not repo.esta_cargado():
        with st.spinner("Cargando repositorio analítico..."):
            repo.cargar_fuente()

    df = repo.obtener_dataframe()
    if df is None or df.empty:
        st.warning("No hay datos disponibles para el análisis de tendencias.")
        return

    # Columnas numéricas y categóricas
    col_cuantia = None
    for c in ["cuantia_final", "cuantia_inicial", "valor_del_contrato"]:
        if c in df.columns:
            col_cuantia = c
            break

    col_ent = "nombre_entidad" if "nombre_entidad" in df.columns else "entidad"
    col_tipo = "tipo_contrato" if "tipo_contrato" in df.columns else "tipo_de_contrato"
    col_depto = "departamento" if "departamento" in df.columns else "geografia.departamento"
    col_pyme = "es_pyme" if "es_pyme" in df.columns else None

    es_oscuro = st.session_state.get("tema", "claro") == "oscuro"
    color_texto = "#F8FAFC" if es_oscuro else "#0F172A"
    color_sub = "#94A3B8" if es_oscuro else "#475569"
    color_grid = "#334155" if es_oscuro else "#F1F5F9"

    # Fila 1: KPIs de Sobrecostos y Adiciones Presupuestales (HU-20)
    kpis_adiciones = AnalyticsController.calcular_kpis_sobrecostos_adiciones(df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            titulo="Monto Total de Adiciones",
            valor=kpis_adiciones["monto_adiciones_fmt"],
            tendencia="Recursos suplementarios ejecutados",
            icono_key="money",
            color_circulo="amber"
        )
    with c2:
        render_kpi_card(
            titulo="Contratos Adicionados",
            valor=kpis_adiciones["porcentaje_adicionados_fmt"],
            tendencia=f"{kpis_adiciones['contratos_con_adicion']:,} de {kpis_adiciones['total_contratos']:,} procesos".replace(",", "."),
            icono_key="risk",
            color_circulo="orange"
        )
    with c3:
        render_kpi_card(
            titulo="Incremento Promedio",
            valor=kpis_adiciones["incremento_promedio_fmt"],
            tendencia="Sobrecosto sobre valor base",
            icono_key="analytics",
            color_circulo="purple"
        )
    with c4:
        render_kpi_card(
            titulo="Valor Promedio por Adición",
            valor=kpis_adiciones["adicion_promedio_fmt"],
            tendencia="Ticket medio adicionado",
            icono_key="addition",
            color_circulo="blue"
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Fila 2: Tendencia Central y Dispersión de Cuantías (HU-21)
    kpis_tendencia = AnalyticsController.calcular_kpis_promedio_mediana(df)

    t1, t2, t3, t4 = st.columns(4)
    with t1:
        render_kpi_card(
            titulo="Cuantía Promedio",
            valor=kpis_tendencia["cuantia_promedio_fmt"],
            tendencia="Media aritmética por proceso",
            icono_key="money",
            color_circulo="blue"
        )
    with t2:
        render_kpi_card(
            titulo="Mediana Contractual",
            valor=kpis_tendencia["cuantia_mediana_fmt"],
            tendencia=f"IQR: {kpis_tendencia['iqr_fmt']}",
            icono_key="contract",
            color_circulo="amber"
        )
    with t3:
        render_kpi_card(
            titulo="Ratio de Distorsión",
            valor=kpis_tendencia["ratio_distorsion_fmt"],
            tendencia=kpis_tendencia["nivel_sesgo"],
            icono_key="risk",
            color_circulo="orange"
        )
    with t4:
        render_kpi_card(
            titulo="Mayor Cuantía Adjudicada",
            valor=kpis_tendencia["cuantia_maxima_fmt"],
            tendencia="Techo de contratación (Megaproyecto)",
            icono_key="data",
            color_circulo="purple"
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Gráfica Descriptiva 1: Gasto Público Acumulado por Modalidad de Contratación (HU-22)
    st.markdown(
        """
        <div class="executive-card">
            <div class="card-header-flex">
                <h3 class="card-title">Distribución del Gasto por Modalidad de Selección</h3>
                <span class="card-action">Auditoría de Concentración Presupuestal</span>
            </div>
        """,
        unsafe_allow_html=True
    )
    fig_modalidad = AnalyticsController.generar_grafica_gasto_modalidad(df, es_oscuro=es_oscuro)
    st.plotly_chart(fig_modalidad, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Gráfica Descriptiva 2: Serie Temporal del Gasto 2021-2026 (HU-23)
    st.markdown(
        """
        <div class="executive-card">
            <div class="card-header-flex">
                <h3 class="card-title">Evolución Cronológica del Gasto Contractual</h3>
                <span class="card-action">Serie Histórica y Estacionalidad Presupuestal</span>
            </div>
        """,
        unsafe_allow_html=True
    )
    col_ctrl_left, col_ctrl_right = st.columns([7, 3])
    with col_ctrl_right:
        granularidad_sel = st.radio(
            "Escala Temporal:",
            options=["Mensual", "Anual"],
            horizontal=True,
            key="radio_granularidad_analytics",
            label_visibility="collapsed"
        )
    fig_ts = AnalyticsController.generar_grafica_serie_temporal(
        df, granularidad=granularidad_sel, es_oscuro=es_oscuro
    )
    st.plotly_chart(fig_ts, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Fila 3: Top 10 Entidades Compradoras (Horizontal Bar) y Tipología Contractual (Donut)
    col_b1, col_b2 = st.columns([60, 40])

    with col_b1:
        st.markdown(
            """
            <div class="executive-card">
                <div class="card-header-flex">
                    <h3 class="card-title">Top 10 Entidades con Mayor Ejecución Presupuestal</h3>
                    <span class="card-action">Control de Gestión y Auditoría</span>
                </div>
            """,
            unsafe_allow_html=True
        )
        fig_top_ent = AnalyticsController.generar_grafica_top_entidades(df, top_n=10, es_oscuro=es_oscuro)
        st.plotly_chart(fig_top_ent, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b2:
        st.markdown(
            """
            <div class="executive-card">
                <div class="card-header-flex">
                    <h3 class="card-title">Distribución por Estado de los Procesos</h3>
                    <span class="card-action">Ciclo de Vida Contractual</span>
                </div>
            """,
            unsafe_allow_html=True
        )
        fig_dona_estados = AnalyticsController.generar_grafica_dona_estados(df, es_oscuro=es_oscuro)
        st.plotly_chart(fig_dona_estados, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Gráfica Descriptiva 5: Diagramas de Caja (Boxplot) de Dispersión de Cuantías y Plazos (HU-26)
    st.markdown(
        """
        <div class="executive-card">
            <div class="card-header-flex">
                <h3 class="card-title">Dispersión y Valores Atípicos por Tipología Contractual</h3>
                <span class="card-action">Diagnóstico de Cuartiles y Outliers</span>
            </div>
        """,
        unsafe_allow_html=True
    )
    col_ctrl_metrica, col_ctrl_escala = st.columns([1, 1])
    with col_ctrl_metrica:
        sel_metrica = st.radio(
            "Variable de Dispersión:",
            options=["Cuantía Contractual (COP)", "Plazo de Ejecución (Días)"],
            horizontal=True,
            key="radio_metrica_boxplot_analytics",
            label_visibility="collapsed"
        )
    with col_ctrl_escala:
        sel_escala = st.radio(
            "Escala Numérica:",
            options=["Escala Logarítmica", "Escala Lineal"],
            horizontal=True,
            key="radio_escala_boxplot_analytics",
            label_visibility="collapsed"
        )

    metrica_cod = "cuantia_final" if "Cuantía" in sel_metrica else "plazo_dias"
    escala_log_val = ("Logarítmica" in sel_escala)

    fig_box = AnalyticsController.generar_grafica_boxplot_dispersion(
        df,
        metrica=metrica_cod,
        escala_log=escala_log_val,
        es_oscuro=es_oscuro
    )
    st.plotly_chart(fig_box, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Fila 4: Distribución Geográfica Departamental
    st.markdown(
        """
        <div class="executive-card">
            <div class="card-header-flex">
                <h3 class="card-title">Concentración Territorial de la Contratación Estatal</h3>
                <span class="card-action">Departamentos Líderes</span>
            </div>
        """,
        unsafe_allow_html=True
    )

    if col_depto and col_depto in df.columns and col_cuantia:
        depto_agg = (
            df.groupby(col_depto)
            .agg(Total_COP=(col_cuantia, "sum"), Procesos=(col_cuantia, "count"))
            .sort_values(by="Total_COP", ascending=False)
            .head(8)
            .reset_index()
        )

        col_g1, col_g2 = st.columns([65, 35])

        with col_g1:
            depto_agg["Total_Millones"] = depto_agg["Total_COP"] / 1_000_000
            fig_depto = px.bar(
                depto_agg,
                x=col_depto,
                y="Total_Millones",
                color="Total_Millones",
                color_continuous_scale="Purples",
                labels={col_depto: "Departamento", "Total_Millones": "Millones COP"}
            )
            fig_depto.update_layout(
                height=290,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                xaxis=dict(showgrid=False, tickfont=dict(color=color_texto, size=10)),
                yaxis=dict(showgrid=True, gridcolor=color_grid, tickfont=dict(color=color_sub, size=10))
            )
            st.plotly_chart(fig_depto, use_container_width=True, config={"displayModeBar": False})

        with col_g2:
            st.markdown("<div style='padding-top: 10px;'>", unsafe_allow_html=True)
            for _, r in depto_agg.head(5).iterrows():
                nom = str(r[col_depto]).title()
                proc = int(r["Procesos"])
                monto = float(r["Total_COP"])
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-color); font-size: 0.84rem;">
                        <span style="font-weight: 600; color: var(--text-primary);">{nom}</span>
                        <span style="color: #4F46E5; font-weight: 700;">$ {monto/1_000_000:,.0f} M <small style='color:var(--text-muted);'>({proc:,} proc)</small></span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
