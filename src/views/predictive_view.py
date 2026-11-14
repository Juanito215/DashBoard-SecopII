"""
Vista de Inteligencia Predictiva y Simulación de Riesgo de Sobrecosto
Historia de Usuario: HU-27 (Simulador Interactivo de Inferencia de Riesgo)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations

import time
from typing import Any
import streamlit as st

from src.database.data_repository import DataRepositorySingleton
from src.ml.risk_predictor import RiskPredictorService
from src.views.components import render_topbar


@st.cache_resource(show_spinner=False)
def _obtener_servicio_predictivo() -> RiskPredictorService:
    """
    Inicializa y entrena el servicio predictivo sobre el dataset curado activo en caché.
    """
    service = RiskPredictorService.get_instance()
    repo = DataRepositorySingleton.get_instance()
    if not repo.esta_cargado():
        repo.cargar_fuente()
    df = repo.obtener_dataframe()
    if df is not None and not df.empty and not service.entrenado:
        service.entrenar(df)
    return service


def render_predictive_view(usuario: dict[str, Any] | None = None) -> None:
    """
    Renderiza el simulador de riesgo predictivo y estimación de sobrecostos contractuales (HU-27).
    """
    render_topbar(
        titulo="Inteligencia Predictiva",
        subtitulo="Simulador de riesgo de sobrecosto y adiciones presupuestales para auditoría preventiva",
        etiqueta_fecha="Modelo Predictivo Supervisado"
    )

    es_oscuro = st.session_state.get("tema", "claro") == "oscuro"
    predictor = _obtener_servicio_predictivo()

    # Opciones dinámicas extraídas del repositorio activo
    repo = DataRepositorySingleton.get_instance()
    df_activo = repo.obtener_dataframe() if repo.esta_cargado() else None

    if df_activo is not None and not df_activo.empty:
        deptos_raw = df_activo["departamento"].dropna().unique() if "departamento" in df_activo.columns else []
        deptos_opc = sorted([str(d).strip() for d in deptos_raw if str(d).strip() != ""])
        if not deptos_opc:
            deptos_opc = ["Valle del Cauca", "Antioquia", "Bogotá D.C.", "Cundinamarca", "Santander", "Atlántico", "Bolívar", "Boyacá"]

        mods_raw = df_activo["modalidad"].dropna().unique() if "modalidad" in df_activo.columns else []
        mods_opc = sorted([str(m).strip() for m in mods_raw if str(m).strip() != ""])
        if not mods_opc:
            mods_opc = ["Contratación directa", "Licitación pública", "Selección abreviada de menor cuantía", "Mínima cuantía", "Concurso de méritos", "Régimen especial"]

        tipos_raw = df_activo["tipo_contrato"].dropna().unique() if "tipo_contrato" in df_activo.columns else []
        tipos_opc = sorted([str(t).strip() for t in tipos_raw if str(t).strip() != ""])
        if not tipos_opc:
            tipos_opc = ["Prestación de servicios", "Obra pública", "Suministro", "Consultoría", "Interventoría", "Arrendamiento"]
    else:
        deptos_opc = ["Valle del Cauca", "Antioquia", "Bogotá D.C.", "Cundinamarca", "Santander", "Atlántico", "Bolívar", "Boyacá"]
        mods_opc = ["Contratación directa", "Licitación pública", "Selección abreviada de menor cuantía", "Mínima cuantía", "Concurso de méritos", "Régimen especial"]
        tipos_opc = ["Prestación de servicios", "Obra pública", "Suministro", "Consultoría", "Interventoría", "Arrendamiento"]

    # 1. Contenedor de Parámetros del Proceso Contractual
    st.markdown(
        """
        <div class="executive-card">
            <div class="card-header-flex">
                <h3 class="card-title">Parámetros del Proceso a Evaluar</h3>
                <span class="card-action">Evaluación Ex-Ante</span>
            </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        departamento = st.selectbox(
            "Departamento de Ejecución:",
            options=deptos_opc,
            key="sim_depto"
        )

        modalidad = st.selectbox(
            "Modalidad de Contratación:",
            options=mods_opc,
            key="sim_modalidad"
        )

        tipo_contrato = st.selectbox(
            "Tipo de Contrato:",
            options=tipos_opc,
            key="sim_tipo"
        )

    with col2:
        cuantia_cop = st.number_input(
            "Cuantía Inicial Estimada (COP):",
            min_value=1_000_000.0,
            max_value=100_000_000_000.0,
            value=250_000_000.0,
            step=25_000_000.0,
            format="%.0f",
            key="sim_cuantia"
        )
        st.caption(f"Presupuesto base a simular: **$ {cuantia_cop:,.0f} COP**")

        plazo_dias = st.slider(
            "Plazo Estimado de Ejecución (Días):",
            min_value=15,
            max_value=1095,
            value=180,
            step=15,
            key="sim_plazo"
        )

        pyme_radio = st.radio(
            "Participación de PYMES (Fomento Productivo):",
            options=["No", "Sí"],
            index=0,
            horizontal=True,
            key="sim_pyme_radio"
        )
        es_pyme = (pyme_radio == "Sí")

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    calcular_btn = st.button("Evaluar Probabilidad de Riesgo", type="primary", use_container_width=True, key="btn_evaluar_riesgo")
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. Inferencia y Cálculo Probabilístico en Tiempo Real (< 1.0s)
    usuario_str = usuario.get("email", "auditor@secopanalytics.gov.co") if isinstance(usuario, dict) else "auditor"

    t_inicio = time.perf_counter()
    resultado = predictor.predecir_riesgo_contrato(
        departamento=departamento,
        modalidad=modalidad,
        tipo_contrato=tipo_contrato,
        es_pyme=es_pyme,
        cuantia_inicial=cuantia_cop,
        plazo_dias=plazo_dias,
        usuario_auditor=usuario_str,
        guardar_en_mongo=bool(calcular_btn)
    )
    latencia_ms = (time.perf_counter() - t_inicio) * 1000.0

    score_riesgo_pct = resultado["probabilidad_adicion_pct"]
    nivel_texto = resultado["nivel_alerta"]
    nivel_color = resultado["color_alerta"]
    sobrecosto_est = resultado["sobrecosto_estimado_cop"]
    cuantia_proy = resultado["cuantia_final_proyectada_cop"]
    pct_sobrecosto = resultado["porcentaje_sobrecosto_est"]
    acc_modelo = resultado["accuracy_modelo_pct"]

    # 3. Presentación del Diagnóstico Predictivo (Bento Grid)
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    col_res1, col_res2 = st.columns([45, 55])

    badge_bg = "#FEF2F2" if nivel_color == "#E11D48" else ("#FFFBEB" if nivel_color == "#D97706" else "#ECFDF5")

    with col_res1:
        st.markdown(
            f"""
            <div class="executive-card">
                <div class="card-header-flex">
                    <h3 class="card-title">Score de Riesgo Predictivo</h3>
                    <span style="background-color: {badge_bg}; color: {nivel_color}; font-weight: 700; font-size: 0.75rem; padding: 3px 10px; border-radius: 20px;">
                        {nivel_texto}
                    </span>
                </div>
            """,
            unsafe_allow_html=True
        )

        fig_gauge = RiskPredictorService.generar_grafica_gauge_riesgo(
            probabilidad_pct=score_riesgo_pct,
            nivel_alerta=nivel_texto,
            color_alerta=nivel_color,
            es_oscuro=es_oscuro
        )
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

        st.caption(f"Exactitud del Modelo: **{acc_modelo:.1f}%** | Inferencia calculada en **{latencia_ms:.1f} ms**")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_res2:
        st.markdown(
            """
            <div class="executive-card">
                <div class="card-header-flex">
                    <h3 class="card-title">Proyección Financiera y Sobrecosto Esperado</h3>
                    <span class="card-action">Modelo Predictivo Supervisado</span>
                </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px;">
                <div style="background-color: var(--card-bg, #F8FAFC); border: 1px solid var(--border-color, #E2E8F0); border-radius: 12px; padding: 14px;">
                    <div style="font-size: 0.78rem; color: #64748B; font-weight: 500;">Cuantía Inicial</div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">$ {cuantia_cop:,.0f}</div>
                    <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">Valor contractual base</div>
                </div>
                <div style="background-color: {badge_bg}; border: 1px solid {badge_bg}; border-radius: 12px; padding: 14px;">
                    <div style="font-size: 0.78rem; color: {nivel_color}; font-weight: 600;">Sobrecosto Estimado</div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: {nivel_color};">+ $ {sobrecosto_est:,.0f}</div>
                    <div style="font-size: 0.72rem; color: {nivel_color}; margin-top: 2px;">Adición probable (+{pct_sobrecosto:.1f}%)</div>
                </div>
            </div>

            <div style="background-color: #EEF2FF; border: 1px solid #E0E7FF; border-radius: 12px; padding: 14px; margin-bottom: 14px;">
                <div style="font-size: 0.82rem; color: #4F46E5; font-weight: 600;">Cuantía Final Proyectada:</div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #3730A3;">$ {cuantia_proy:,.0f} COP</div>
            </div>

            <div style="font-size: 0.82rem; color: #475569; line-height: 1.5;">
                <strong>Recomendación de Control Fiscal:</strong> 
                {"Se sugiere auditoría rigurosa a los estudios previos, justificación de plazos y seguimiento quincenal a la ejecución del proceso." if score_riesgo_pct >= 65 else ("Se sugiere seguimiento preventivo y revisión de la matriz de riesgos contractuales para contingencias presupuestales." if score_riesgo_pct >= 35 else "El proceso se encuentra dentro de parámetros habituales de estabilidad presupuestal para su tipología y modalidad.")}
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # 4. Gráficas Probabilísticas y Curvas de Riesgo Presupuestal (HU-29)
    col_p1, col_p2 = st.columns([60, 40])

    with col_p1:
        st.markdown(
            """
            <div class="executive-card">
                <div class="card-header-flex">
                    <h3 class="card-title">Proyección de Sobrecosto e Intervalo de Confianza</h3>
                    <span class="card-action">Banda de Confianza 95%</span>
                </div>
            """,
            unsafe_allow_html=True
        )
        fig_curva_ic = predictor.generar_grafica_proyeccion_ic(
            departamento=departamento,
            modalidad=modalidad,
            tipo_contrato=tipo_contrato,
            es_pyme=es_pyme,
            cuantia_inicial=cuantia_cop,
            es_oscuro=es_oscuro
        )
        st.plotly_chart(fig_curva_ic, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_p2:
        st.markdown(
            """
            <div class="executive-card">
                <div class="card-header-flex">
                    <h3 class="card-title">Distribución de Escenarios de Contingencia</h3>
                    <span class="card-action">Reserva de Tesorería</span>
                </div>
            """,
            unsafe_allow_html=True
        )
        fig_escenarios = RiskPredictorService.generar_grafica_escenarios_contingencia(
            score_riesgo=resultado["score_riesgo_anomalia"],
            cuantia_inicial=cuantia_cop,
            es_oscuro=es_oscuro
        )
        st.plotly_chart(fig_escenarios, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Factores Determinantes de Riesgo Presupuestal (Feature Importance)
    st.markdown(
        """
        <div class="executive-card">
            <div class="card-header-flex">
                <h3 class="card-title">Factores Determinantes del Riesgo Presupuestal</h3>
                <span class="card-action">Explicabilidad del Modelo</span>
            </div>
        """,
        unsafe_allow_html=True
    )
    fig_importancia = predictor.generar_grafica_importancia_variables(es_oscuro=es_oscuro)
    st.plotly_chart(fig_importancia, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # 5. Priorización de Auditorías Preventivas y Mapa de Anomalías (Lote Activo)
    st.markdown(
        """
        <div class="executive-card">
            <div class="card-header-flex">
                <h3 class="card-title">Priorización de Auditorías Preventivas (Lote Activo)</h3>
                <span class="card-action">Score de Anomalía Continuo (0.00 a 1.00)</span>
            </div>
        """,
        unsafe_allow_html=True
    )

    if df_activo is not None and not df_activo.empty:
        df_evaluado = predictor.calcular_score_hibrido_lote(df_activo)

        total_proc = len(df_evaluado)
        total_alto = int((df_evaluado["nivel_alerta"] == "Alto").sum())
        total_mod = int((df_evaluado["nivel_alerta"] == "Moderado").sum())
        total_bajo = int((df_evaluado["nivel_alerta"] == "Bajo").sum())

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Contratos Evaluados", f"{total_proc:,}".replace(",", "."))
        with m2:
            st.metric("Alerta Alta (Prioridad Inmediata)", f"{total_alto:,}".replace(",", "."), f"{(total_alto/total_proc*100.0) if total_proc else 0:.1f}%")
        with m3:
            st.metric("Alerta Moderada (Seguimiento)", f"{total_mod:,}".replace(",", "."), f"{(total_mod/total_proc*100.0) if total_proc else 0:.1f}%")
        with m4:
            st.metric("Alerta Baja (Riesgo Habitual)", f"{total_bajo:,}".replace(",", "."), f"{(total_bajo/total_proc*100.0) if total_proc else 0:.1f}%")

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        # Mapa de dispersión de anomalías
        fig_dispersion = RiskPredictorService.generar_grafica_dispersion_anomalias(
            df_evaluado, max_puntos=800, es_oscuro=es_oscuro
        )
        st.plotly_chart(fig_dispersion, use_container_width=True, config={"displayModeBar": False})

        # Tabla priorizada de contratos
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("**Listado Priorizado para Control Preventivo (Top 100 Procesos con Mayor Anomalía):**")

        cols_mostrar_pref = [
            "id_contrato", "entidad", "nombre_entidad", "departamento", "modalidad",
            "tipo_contrato", "cuantia_inicial", "plazo_dias", "score_riesgo_anomalia", "nivel_alerta"
        ]
        cols_mostrar = [c for c in cols_mostrar_pref if c in df_evaluado.columns]

        df_tabla = df_evaluado[cols_mostrar].head(100)
        st.dataframe(
            df_tabla,
            use_container_width=True,
            height=340
        )
    else:
        st.info("Sin registros disponibles en la fuente activa para evaluar el lote de contratos.")

    st.markdown("</div>", unsafe_allow_html=True)
