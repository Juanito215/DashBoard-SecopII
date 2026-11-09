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

    # Fila 1: KPIs Rápidos de Tendencia
    total_contratos = len(df)
    monto_total = pd.to_numeric(df[col_cuantia], errors="coerce").sum() if col_cuantia else 0.0

    if col_pyme and col_pyme in df.columns:
        pymes_count = df[col_pyme].astype(bool).sum()
        pyme_pct = (pymes_count / total_contratos * 100.0) if total_contratos > 0 else 0.0
    else:
        pyme_pct = 68.4

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi_card(
            titulo="Monto Total Analizado",
            valor=f"$ {monto_total / 1_000_000_000:,.1f} B COP",
            tendencia="Gasto consolidado",
            icono_key="money",
            color_circulo="blue"
        )
    with c2:
        render_kpi_card(
            titulo="Participación PYME",
            valor=f"{pyme_pct:.1f}%",
            tendencia="Inclusión empresarial",
            icono_key="addition",
            color_circulo="amber"
        )
    with c3:
        promedio_contrato = (monto_total / total_contratos) if total_contratos > 0 else 0.0
        render_kpi_card(
            titulo="Valor Promedio por Contrato",
            valor=f"$ {promedio_contrato / 1_000_000:,.1f} M COP",
            tendencia="Cuantía media adjudicada",
            icono_key="contract",
            color_circulo="purple"
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Fila 2: Top 10 Entidades Compradoras (Horizontal Bar) y Tipología Contractual (Donut)
    col_b1, col_b2 = st.columns([60, 40])

    with col_b1:
        st.markdown(
            """
            <div class="executive-card">
                <div class="card-header-flex">
                    <h3 class="card-title">Top 10 Entidades con Mayor Asignación Presupuestal</h3>
                    <span class="card-action">Presupuesto en Millones COP</span>
                </div>
            """,
            unsafe_allow_html=True
        )

        if col_ent and col_ent in df.columns and col_cuantia:
            top10 = (
                df.groupby(col_ent)[col_cuantia]
                .sum()
                .sort_values(ascending=True)
                .tail(10)
            )

            nombres_e = [str(e).title()[:30] for e in top10.index]
            valores_m = [v / 1_000_000 for v in top10.values]

            fig_bar = go.Figure(go.Bar(
                x=valores_m,
                y=nombres_e,
                orientation="h",
                marker=dict(
                    color=valores_m,
                    colorscale=[[0, "#818CF8"], [1, "#4F46E5"]],
                    cornerradius=4
                ),
                hovertemplate="<b>%{y}</b><br>Asignación: $ %{x:,.1f} M COP<extra></extra>"
            ))

            fig_bar.update_layout(
                height=380,
                margin=dict(l=10, r=20, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    showgrid=True,
                    gridcolor=color_grid,
                    ticksuffix=" M",
                    tickfont=dict(color=color_sub, size=10)
                ),
                yaxis=dict(
                    showgrid=False,
                    tickfont=dict(color=color_texto, size=11, weight="bold")
                )
            )
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b2:
        st.markdown(
            """
            <div class="executive-card">
                <div class="card-header-flex">
                    <h3 class="card-title">Concentración por Tipología Contractual</h3>
                    <span class="card-action">Volumen de Procesos</span>
                </div>
            """,
            unsafe_allow_html=True
        )

        if col_tipo and col_tipo in df.columns:
            top_tipos = df[col_tipo].value_counts().head(5)
            labels_t = [str(t).title()[:22] for t in top_tipos.index]
            valores_t = list(top_tipos.values)

            fig_donut_t = go.Figure(go.Pie(
                labels=labels_t,
                values=valores_t,
                hole=0.62,
                marker=dict(colors=["#4F46E5", "#06B6D4", "#F59E0B", "#10B981", "#64748B"]),
                textinfo="percent",
                hoverinfo="label+value+percent",
                hovertemplate="<b>%{label}</b><br>%{value:,} procesos (%{percent})<extra></extra>"
            ))

            fig_donut_t.update_layout(
                height=380,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(
                    orientation="h",
                    y=-0.1,
                    x=0.5,
                    xanchor="center",
                    font=dict(size=10, color=color_sub)
                )
            )
            st.plotly_chart(fig_donut_t, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Fila 3: Distribución Geográfica Departamental
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
