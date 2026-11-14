"""
Vista del Explorador de Contratos y Filtrado Dinámico Multi-Criterio
Patrón Builder Integrado (ConsultaSecopBuilder)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import time
from typing import Any
import pandas as pd
import streamlit as st

from src.database.data_repository import get_data_repository
from src.controllers.analytics_controller import AnalyticsController
from src.queries.query_builder import ConsultaSecopBuilder
from src.utils.export_service import ExportService
from src.views.components import render_topbar, render_kpi_card, get_status_badge_html


def render_consultas_view(usuario: dict[str, Any]) -> None:
    """
    Renderiza la interfaz analítica del Explorador de Contratos con diseño corporativo SaaS.
    """
    render_topbar(
        titulo="Explorador de Contratos",
        subtitulo="Búsqueda analítica multi-criterio y auditoría focalizada sobre contratación pública",
        etiqueta_fecha="Vigencias 2021 – 2026"
    )

    # 1. Validación de Control de Acceso RBAC
    permisos = usuario.get("permisos", [])
    if "consultas_bi" not in permisos:
        st.error(
            "Acceso Restringido: Su rol actual no dispone del permiso 'consultas_bi' "
            "para ejecutar consultas sobre el repositorio analítico."
        )
        return

    # 2. Obtención del Repositorio Central Singleton
    repo = get_data_repository()
    if not repo.esta_cargado():
        with st.spinner("Cargando repositorio analítico central..."):
            try:
                repo.cargar_fuente()
            except Exception as err:
                st.error(f"Error al inicializar el repositorio: {err}")
                return

    df_base = repo.obtener_dataframe()
    if df_base is None or df_base.empty:
        st.error("El repositorio analítico se encuentra vacío o no disponible.")
        return

    # 3. Resolución de columnas territoriales, temporales, procedimentales, tipológicas y de cuantía
    col_depto = None
    for cand_dep in ["departamento", "geografia.departamento"]:
        if cand_dep in df_base.columns:
            col_depto = cand_dep
            break

    col_mpio = None
    for cand_mpio in ["municipio", "ciudad", "geografia.municipio"]:
        if cand_mpio in df_base.columns:
            col_mpio = cand_mpio
            break

    col_anio = None
    for cand_anio in ["anio_vigencia", "tiempo.anio_vigencia", "ano_firma", "anio"]:
        if cand_anio in df_base.columns:
            col_anio = cand_anio
            break

    col_mod = None
    for cand_mod in ["modalidad", "clasificacion.modalidad", "modalidad_de_contratacion", "tipo_modalidad"]:
        if cand_mod in df_base.columns:
            col_mod = cand_mod
            break

    col_tipo = None
    for cand_tipo in ["tipo_contrato", "clasificacion.tipo_contrato", "tipo_de_contrato", "tipo contrato"]:
        if cand_tipo in df_base.columns:
            col_tipo = cand_tipo
            break

    col_cuantia = None
    for cand_c in ["cuantia_inicial", "valor_del_contrato", "cuantia", "valor_contrato", "monto_contrato"]:
        if cand_c in df_base.columns:
            col_cuantia = cand_c
            break

    # Si falta anio_vigencia pero está fecha_firma, normalizar columna en memoria
    if "anio_vigencia" not in df_base.columns:
        if col_anio is not None:
            df_base["anio_vigencia"] = pd.to_numeric(df_base[col_anio], errors="coerce").fillna(2022).astype(int)
        elif "fecha_firma" in df_base.columns:
            df_base["anio_vigencia"] = pd.to_datetime(df_base["fecha_firma"], errors="coerce").dt.year.fillna(2022).astype(int)
        elif "fecha_de_firma" in df_base.columns:
            df_base["anio_vigencia"] = pd.to_datetime(df_base["fecha_de_firma"], errors="coerce").dt.year.fillna(2022).astype(int)
        col_anio = "anio_vigencia"

    if col_depto is None:
        st.error("No se encontró la dimensión de departamento en el repositorio.")
        return

    # 4. Calibración dinámica de límites de Cuantía Inicial en COP
    if col_cuantia is not None:
        serie_cuantia = pd.to_numeric(df_base[col_cuantia], errors="coerce").dropna()
        min_cuantia_data = float(serie_cuantia.min()) if not serie_cuantia.empty else 0.0
        max_cuantia_data = float(serie_cuantia.max()) if not serie_cuantia.empty else 1000000000.0
    else:
        min_cuantia_data = 0.0
        max_cuantia_data = 1000000000.0

    # 5. Extracción Dinámica de Opciones Ordenadas A-Z
    deptos_unicos = sorted(list({
        str(val).strip() for val in df_base[col_depto].dropna().unique()
        if str(val).strip() and str(val).strip().upper() not in ["NAN", "NONE", "NULL", "NO REGISTRADO"]
    }))

    modalidades_unicas = sorted(list({
        str(val).strip() for val in df_base[col_mod].dropna().unique()
        if str(val).strip() and str(val).strip().upper() not in ["NAN", "NONE", "NULL", "NO REGISTRADO"]
    })) if col_mod is not None else []

    tipos_contrato_unicos = sorted(list({
        str(val).strip() for val in df_base[col_tipo].dropna().unique()
        if str(val).strip() and str(val).strip().upper() not in ["NAN", "NONE", "NULL", "NO REGISTRADO"]
    })) if col_tipo is not None else []

    # 6. Formulario de Parámetros de Búsqueda (Tarjeta Ejecutiva)
    st.markdown(
        """
        <div class="executive-card">
            <div class="card-header-flex">
                <h3 class="card-title">Parámetros de Búsqueda y Filtrado</h3>
                <span class="card-action">Búsqueda Parametrizada</span>
            </div>
        """,
        unsafe_allow_html=True
    )

    # Función de restablecimiento global de filtros (HU-18)
    def _restablecer_todos_los_filtros() -> None:
        st.session_state["filtro_deptos_multiselect"] = []
        st.session_state["filtro_mpios_state"] = []
        st.session_state["filtro_mpios_multiselect"] = []
        st.session_state["filtro_modalidades_multiselect"] = []
        st.session_state["filtro_tipos_multiselect"] = []
        st.session_state["filtro_cuantia_min_input"] = 0.0
        st.session_state["filtro_cuantia_max_input"] = float(max_cuantia_data)
        st.session_state["filtro_modo_tiempo_radio"] = "Rango Continuo"
        st.session_state["filtro_rango_anios_slider"] = (2021, 2026)
        st.session_state["filtro_anios_discretos_multiselect"] = [2021, 2022, 2023, 2024, 2025, 2026]
        st.session_state["filtro_entidad_input"] = ""
        st.session_state["filtro_proveedor_input"] = ""
        st.session_state["filtro_pyme_radio"] = "Todas las empresas"
        st.session_state["filtro_unspsc_input"] = ""

    # Fila 1: Filtros Territoriales y Acción de Restablecimiento Global
    col_dep, col_mpio_ui, col_reset = st.columns([3, 3, 1.5])

    with col_dep:
        deptos_seleccionados = st.multiselect(
            label="1. Departamento(s):",
            options=deptos_unicos,
            default=[],
            placeholder="Todos los departamentos (sin restricción)...",
            help="Seleccione uno o varios departamentos. Acotará automáticamente los municipios disponibles.",
            key="filtro_deptos_multiselect"
        )

    # Lógica en Cascada para Municipios
    if deptos_seleccionados:
        deptos_limpios = [str(d).strip().upper() for d in deptos_seleccionados]
        col_depto_s = df_base[col_depto].astype(str)
        mascara_deptos = (
            col_depto_s.isin(deptos_seleccionados)
            | col_depto_s.str.upper().isin(deptos_limpios)
        )
        df_mpios_base = df_base[mascara_deptos]
    else:
        df_mpios_base = df_base

    if col_mpio is not None and col_mpio in df_mpios_base.columns:
        mpios_unicos = sorted(list({
            str(val).strip() for val in df_mpios_base[col_mpio].dropna().unique()
            if str(val).strip() and str(val).strip().upper() not in ["NAN", "NONE", "NULL", "NO REGISTRADO"]
        }))
    else:
        mpios_unicos = []

    if "filtro_mpios_state" not in st.session_state:
        st.session_state.filtro_mpios_state = []

    mpios_validos_previos = [
        m for m in st.session_state.filtro_mpios_state if m in mpios_unicos
    ]
    st.session_state.filtro_mpios_state = mpios_validos_previos

    with col_mpio_ui:
        placeholder_mpio = (
            f"Municipios de {len(deptos_seleccionados)} departamento(s)..."
            if deptos_seleccionados
            else "Todos los municipios (sin restricción)..."
        )
        mpios_seleccionados = st.multiselect(
            label="2. Municipio(s) (En Cascada):",
            options=mpios_unicos,
            default=mpios_validos_previos,
            placeholder=placeholder_mpio,
            help="Lista reactiva acotada al departamento seleccionado y ordenada estrictamente A-Z.",
            key="filtro_mpios_multiselect"
        )
        st.session_state.filtro_mpios_state = mpios_seleccionados

    with col_reset:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.button(
            "Restablecer Filtros",
            key="btn_restablecer_filtros",
            on_click=_restablecer_todos_los_filtros,
            use_container_width=True,
            help="Restaura todos los parámetros de filtrado a sus valores iniciales sin recargar la sesión."
        )

    # Fila 2: Modalidad y Tipo de Contrato
    st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
    col_mod_ui, col_tipo_ui = st.columns([1, 1])

    with col_mod_ui:
        modalidades_seleccionadas = st.multiselect(
            label="3. Modalidad(es) de Selección:",
            options=modalidades_unicas,
            default=[],
            placeholder="Todas las modalidades (sin restricción)...",
            help="Contratación Directa, Licitación Pública, Mínima Cuantía, etc.",
            key="filtro_modalidades_multiselect"
        )

    with col_tipo_ui:
        tipos_seleccionados = st.multiselect(
            label="4. Tipo(s) de Contrato:",
            options=tipos_contrato_unicos,
            default=[],
            placeholder="Todos los tipos de contrato (sin restricción)...",
            help="Prestación de servicios, Obra, Suministro, Consultoría, etc.",
            key="filtro_tipos_multiselect"
        )

    # Fila 3: Filtro Presupuestal por Rango de Cuantía Inicial
    st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
    st.markdown("**5. Rango Presupuestal de Cuantía Inicial (Pesos Colombianos - COP)**")
    col_q1, col_q2 = st.columns(2)

    with col_q1:
        cuantia_min_input = st.number_input(
            label="Monto Mínimo (COP):",
            min_value=0.0,
            max_value=float(max_cuantia_data),
            value=0.0,
            step=5000000.0,
            format="%.0f",
            key="filtro_cuantia_min_input",
            help=f"Límite inferior. Mínimo registrado: ${min_cuantia_data:,.0f} COP"
        )

    with col_q2:
        cuantia_max_input = st.number_input(
            label="Monto Máximo (COP):",
            min_value=0.0,
            max_value=float(max_cuantia_data),
            value=float(max_cuantia_data),
            step=5000000.0,
            format="%.0f",
            key="filtro_cuantia_max_input",
            help=f"Límite superior. Máximo registrado: ${max_cuantia_data:,.0f} COP"
        )

    st.caption(
        f"Rango presupuestal seleccionado: **COP {cuantia_min_input:,.0f}** hasta **COP {cuantia_max_input:,.0f}**"
    )

    # Fila 4: Filtro Temporal por Año de Vigencia Fiscal
    st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
    col_t1, col_t2 = st.columns([2, 5])

    with col_t1:
        modo_tiempo = st.radio(
            "6. Modalidad Temporal:",
            options=["Rango Continuo", "Años Específicos"],
            horizontal=True,
            key="filtro_modo_tiempo_radio",
            help="Intervalo continuo o selección discreta de años."
        )

    with col_t2:
        if modo_tiempo == "Rango Continuo":
            rango_anios = st.slider(
                label="Intervalo de Vigencia Fiscal (Años):",
                min_value=2021,
                max_value=2026,
                value=(2021, 2026),
                step=1,
                key="filtro_rango_anios_slider",
                help="Ventana cronológica analizada."
            )
            anios_filtro = rango_anios
        else:
            anios_disponibles_default = [2021, 2022, 2023, 2024, 2025, 2026]
            anios_seleccionados = st.multiselect(
                label="Seleccione Años de Formalización:",
                options=anios_disponibles_default,
                default=anios_disponibles_default,
                key="filtro_anios_discretos_multiselect",
                help="Uno o varios años de formalización."
            )
            anios_filtro = anios_seleccionados

    # Fila 5: Búsqueda por Entidad Compradora y Proveedor Contratista
    st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
    col_ent, col_prov = st.columns([1, 1])

    with col_ent:
        entidad_query = st.text_input(
            label="7. Entidad Compradora (Nombre o NIT):",
            value="",
            placeholder="Ej: Alcaldía de Tuluá, Gobernación, Hospital, 890399045...",
            help="Búsqueda insensible a mayúsculas y acentos sobre la entidad estatal o su NIT.",
            key="filtro_entidad_input"
        )

    with col_prov:
        proveedor_query = st.text_input(
            label="8. Proveedor Contratista (Razón Social o Documento):",
            value="",
            placeholder="Ej: Rivera Martinez, Consorcio, 1036640178...",
            help="Búsqueda insensible a mayúsculas y acentos sobre el contratista o su cédula/NIT.",
            key="filtro_proveedor_input"
        )

    # Fila 6: Participación de PYMES y Clasificador UNSPSC
    st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
    col_pyme_ui, col_unspsc_ui = st.columns([1, 1])

    with col_pyme_ui:
        pyme_opciones = ["Todas las empresas", "Solo PYMES", "No PYMES / Gran Empresa"]
        pyme_seleccion = st.radio(
            label="9. Participación de PYMES (Fomento Productivo):",
            options=pyme_opciones,
            index=0,
            horizontal=True,
            key="filtro_pyme_radio",
            help="Filtra procesos adjudicados a micro, pequeñas y medianas empresas o grandes corporaciones."
        )

    with col_unspsc_ui:
        unspsc_query = st.text_input(
            label="10. Clasificador de Bienes y Servicios (UNSPSC):",
            value="",
            placeholder="Ej: 72, 7214, 80111600, V1.72141103...",
            help="Búsqueda por código o familia UNSPSC. Admite segmento (2 dígitos), familia (4 dígitos), clase (6 dígitos) o producto (8 dígitos).",
            key="filtro_unspsc_input"
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # 7. Resolución de parámetros de cuantía para el Builder
    min_cop_param = cuantia_min_input if cuantia_min_input > 0 else None
    max_cop_param = cuantia_max_input if cuantia_max_input < max_cuantia_data else None

    # 8. Ejecución Encadenada del Patrón Builder
    inicio_ejecucion = time.perf_counter()
    builder = ConsultaSecopBuilder(df_base)
    (
        builder
        .filtrar_departamento(deptos_seleccionados)
        .filtrar_municipio(mpios_seleccionados)
        .filtrar_anio(anios_filtro)
        .filtrar_modalidad(modalidades_seleccionadas)
        .con_tipo_contrato(tipos_seleccionados)
        .con_rango_cuantia(min_cop=min_cop_param, max_cop=max_cop_param)
        .con_entidad_o_nit(entidad_query)
        .con_proveedor(proveedor_query)
        .con_es_pyme(pyme_seleccion)
        .con_codigo_unspsc(unspsc_query)
    )
    df_filtrado, query_mongo, latencia_ms = builder.build()
    latencia_total_ms = (time.perf_counter() - inicio_ejecucion) * 1000.0

    # 9. Telemetría Operativa y Tarjetas Resumen
    total_original = len(df_base)
    total_filtrados = len(df_filtrado)
    porcentaje_visibles = (total_filtrados / total_original * 100.0) if total_original > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_kpi_card(
            titulo="Contratos Coincidentes",
            valor=f"{total_filtrados:,}".replace(",", "."),
            tendencia=f"{porcentaje_visibles:.1f}% de la muestra total",
            icono_key="contract",
            color_circulo="blue"
        )

    with c2:
        tiempo_display = latencia_ms if latencia_ms > 0 else latencia_total_ms
        render_kpi_card(
            titulo="Latencia de Consulta",
            valor=f"{tiempo_display:.1f} ms",
            tendencia="Alta velocidad (< 500 ms)",
            icono_key="analytics",
            color_circulo="amber"
        )

    with c3:
        n_deptos = len(deptos_seleccionados)
        n_mpios = len(mpios_seleccionados)
        n_mods = len(modalidades_seleccionadas)
        n_tipos = len(tipos_seleccionados)
        tiene_cuantia = min_cop_param is not None or max_cop_param is not None
        tiene_entidad = bool(entidad_query and entidad_query.strip())
        tiene_prov = bool(proveedor_query and proveedor_query.strip())
        tiene_pyme = pyme_seleccion != "Todas las empresas"
        tiene_unspsc = bool(unspsc_query and unspsc_query.strip())
        criterios_total = (
            n_deptos +
            (1 if n_mpios else 0) +
            (1 if n_mods else 0) +
            (1 if n_tipos else 0) +
            (1 if tiene_cuantia else 0) +
            (1 if tiene_entidad else 0) +
            (1 if tiene_prov else 0) +
            (1 if tiene_pyme else 0) +
            (1 if tiene_unspsc else 0)
        )
        render_kpi_card(
            titulo="Filtros Aplicados",
            valor=f"{criterios_total}",
            tendencia="Criterios activos",
            icono_key="addition",
            color_circulo="orange"
        )

    with c4:
        render_kpi_card(
            titulo="Arquitectura de Consulta",
            valor="Builder 10D",
            tendencia="Encadenamiento fluido",
            icono_key="data",
            color_circulo="purple"
        )

    # Panel de Concentración de Adjudicaciones para Veeduría
    if tiene_prov and not df_filtrado.empty:
        col_monto = None
        for cand_m in ["cuantia_final", "cuantia_inicial", "valor_del_contrato", "monto_contrato"]:
            if cand_m in df_filtrado.columns:
                col_monto = cand_m
                break

        col_est = None
        for cand_e in ["estado", "estado_contrato", "clasificacion.estado", "estado del contrato"]:
            if cand_e in df_filtrado.columns:
                col_est = cand_e
                break

        total_contratos_prov = len(df_filtrado)
        monto_total_prov = (
            pd.to_numeric(df_filtrado[col_monto], errors="coerce").sum()
            if col_monto in df_filtrado.columns
            else 0.0
        )

        st.markdown(
            """
            <div class="executive-card" style="margin-top: 15px; border-left: 4px solid #4F46E5;">
                <div class="card-header-flex">
                    <h3 class="card-title">Análisis de Concentración del Contratista</h3>
                    <span class="card-action">Veeduría Focalizada</span>
                </div>
            """,
            unsafe_allow_html=True
        )

        cp1, cp2, cp3 = st.columns([2, 3, 5])
        with cp1:
            st.metric("Total Procesos Asignados", f"{total_contratos_prov:,}".replace(",", "."))
        with cp2:
            st.metric("Cuantía Total Adjudicada", f"COP {monto_total_prov:,.0f}")
        with cp3:
            if col_est:
                dist_estados = df_filtrado[col_est].value_counts().to_dict()
                st.markdown("**Distribución de Estados Vigentes:**")
                badges = " &nbsp;|&nbsp; ".join([f"`{k}`: **{v}**" for k, v in dist_estados.items()])
                st.markdown(badges, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Panel de Fomento Productivo y Participación PYME
    col_pyme_metric = None
    for cand_pyme in ["es_pyme", "proveedor.es_pyme", "pyme", "es pyme", "es_mipyme"]:
        if cand_pyme in df_filtrado.columns:
            col_pyme_metric = cand_pyme
            break

    col_monto_metric = None
    for cand_m in ["cuantia_final", "cuantia_inicial", "valor_del_contrato", "monto_contrato", "valor_contrato"]:
        if cand_m in df_filtrado.columns:
            col_monto_metric = cand_m
            break

    if col_pyme_metric and not df_filtrado.empty:
        total_proc = len(df_filtrado)
        serie_pyme_raw = df_filtrado[col_pyme_metric]
        if pd.api.types.is_bool_dtype(serie_pyme_raw):
            mascara_pyme = (serie_pyme_raw == True)
        else:
            mascara_pyme = serie_pyme_raw.map(
                lambda v: str(v).strip().lower() in ["si", "sí", "true", "1", "s", "verdadero", "yes"]
            )
        total_pymes_count = int(mascara_pyme.sum())
        porcentaje_pymes = (total_pymes_count / total_proc * 100.0) if total_proc > 0 else 0.0

        if col_monto_metric:
            serie_montos = pd.to_numeric(df_filtrado[col_monto_metric], errors="coerce").fillna(0.0)
            monto_total_general = serie_montos.sum()
            monto_pymes = serie_montos[mascara_pyme].sum()
            porcentaje_monto_pymes = (monto_pymes / monto_total_general * 100.0) if monto_total_general > 0 else 0.0
        else:
            monto_pymes = 0.0
            porcentaje_monto_pymes = 0.0

        st.markdown(
            """
            <div class="executive-card" style="margin-top: 15px; border-left: 4px solid #10B981;">
                <div class="card-header-flex">
                    <h3 class="card-title">Fomento Productivo y Participación PYME</h3>
                    <span class="card-action">Auditoría de Inclusión</span>
                </div>
            """,
            unsafe_allow_html=True
        )
        fp1, fp2, fp3 = st.columns([3, 4, 3])
        with fp1:
            st.metric("Contratos con PYMES", f"{total_pymes_count:,}".replace(",", "."), f"{porcentaje_pymes:.1f}% de procesos")
        with fp2:
            st.metric("Monto Asignado a PYMES", f"COP {monto_pymes:,.0f}", f"{porcentaje_monto_pymes:.1f}% del presupuesto")
        with fp3:
            distribucion_tipo = "Segmento MiPyme" if pyme_seleccion == "Solo PYMES" else ("Gran Empresa" if pyme_seleccion == "No PYMES / Gran Empresa" else "Consolidado Mixto")
            st.metric("Criterio Activo", distribucion_tipo, f"{total_pymes_count} de {total_proc} procesos")
        st.markdown("</div>", unsafe_allow_html=True)

    # 10. Detalles Técnicos NoSQL (Expander Discreto)
    with st.expander("Ver Predicado Compilado para MongoDB ($match)", expanded=False):
        if query_mongo:
            st.json(query_mongo)
        else:
            st.info("Sin restricciones activas: la consulta recupera la totalidad de documentos.")

    # Gráficas Descriptivas del subconjunto activo
    if not df_filtrado.empty:
        with st.expander("Gráficas Descriptivas del Subconjunto Filtrado", expanded=False):
            tab_g1, tab_g2, tab_g3, tab_g4, tab_g5 = st.tabs([
                "Gasto por Modalidad",
                "Serie Temporal (2021-2026)",
                "Top 10 Entidades",
                "Distribución por Estado",
                "Dispersión y Atípicos"
            ])
            with tab_g1:
                fig_mod_filtrado = AnalyticsController.generar_grafica_gasto_modalidad(df_filtrado)
                st.plotly_chart(fig_mod_filtrado, use_container_width=True, config={"displayModeBar": False})
            with tab_g2:
                fig_ts_filtrado = AnalyticsController.generar_grafica_serie_temporal(df_filtrado, granularidad="Mensual")
                st.plotly_chart(fig_ts_filtrado, use_container_width=True, config={"displayModeBar": False})
            with tab_g3:
                fig_top_filtrado = AnalyticsController.generar_grafica_top_entidades(df_filtrado, top_n=10)
                st.plotly_chart(fig_top_filtrado, use_container_width=True, config={"displayModeBar": False})
            with tab_g4:
                fig_est_filtrado = AnalyticsController.generar_grafica_dona_estados(df_filtrado)
                st.plotly_chart(fig_est_filtrado, use_container_width=True, config={"displayModeBar": False})
            with tab_g5:
                c_m, c_e = st.columns([1, 1])
                with c_m:
                    sel_box_m = st.radio(
                        "Variable de Análisis:",
                        options=["Cuantía Contractual (COP)", "Plazo de Ejecución (Días)"],
                        horizontal=True,
                        key="radio_box_metrica_consultas",
                        label_visibility="collapsed"
                    )
                with c_e:
                    sel_box_e = st.radio(
                        "Escala Eje Y:",
                        options=["Escala Logarítmica", "Escala Lineal"],
                        horizontal=True,
                        key="radio_box_escala_consultas",
                        label_visibility="collapsed"
                    )
                met_cod = "cuantia_final" if "Cuantía" in sel_box_m else "plazo_dias"
                log_val = ("Logarítmica" in sel_box_e)
                fig_box_filtrado = AnalyticsController.generar_grafica_boxplot_dispersion(
                    df_filtrado, metrica=met_cod, escala_log=log_val
                )
                st.plotly_chart(fig_box_filtrado, use_container_width=True, config={"displayModeBar": False})

    # 11. Visualización de los Contratos Filtrados
    st.markdown(
        """
        <div class="executive-card" style="margin-top: 15px;">
            <div class="card-header-flex">
                <h3 class="card-title">Contratos Filtrados</h3>
                <span class="card-action">Registros Coincidentes</span>
            </div>
        """,
        unsafe_allow_html=True
    )

    if df_filtrado.empty:
        st.warning(
            "No se encontraron contratos para la combinación de filtros seleccionada. "
            "Ajuste los parámetros territoriales, tipológicos o presupuestales."
        )
        st.download_button(
            label="Descargar Contratos Filtrados (CSV)",
            data=b"",
            file_name="SECOP_Analytics_Sin_Registros.csv",
            mime="text/csv",
            disabled=True,
            help="La descarga se encuentra deshabilitada debido a que no existen contratos coincidentes con los filtros activos."
        )
    else:
        columnas_preferidas = [
            "id_contrato", "cuantia_inicial", "cuantia_final", "tipo_contrato",
            "modalidad", "es_pyme", "codigo_unspsc", "codigo_de_categoria_principal",
            "anio_vigencia", "departamento", "municipio", "ciudad",
            "valor_adiciones", "estado", "fecha_firma", "proveedor", "nombre_entidad"
        ]
        columnas_visibles = [col for col in columnas_preferidas if col in df_filtrado.columns]
        if not columnas_visibles:
            columnas_visibles = list(df_filtrado.columns[:10])

        df_display = df_filtrado[columnas_visibles].head(200)

        st.dataframe(
            df_display,
            use_container_width=True,
            height=380
        )
        st.caption(
            f"Mostrando los primeros {len(df_display)} registros de un total de {total_filtrados:,} contratos filtrados."
            .replace(",", ".")
        )

        st.markdown("<hr style='margin: 15px 0 12px 0; border: none; border-top: 1px solid var(--border-color);'/>", unsafe_allow_html=True)
        col_exp1, col_exp2 = st.columns([1, 1])

        with col_exp1:
            tipo_exportacion = st.radio(
                "Estructura del Reporte:",
                options=["Vista Ejecutiva (Columnas Clave)", "Dataset Completo (Todas las Columnas)"],
                horizontal=True,
                key="radio_tipo_exportacion_csv",
            )

        with col_exp2:
            separador_sel = st.radio(
                "Separador de Campos:",
                options=[", (Coma estándar)", "; (Punto y coma Excel)"],
                horizontal=True,
                key="radio_separador_csv",
            )

        solo_clave = (tipo_exportacion == "Vista Ejecutiva (Columnas Clave)")
        sep_char = "," if "Coma" in separador_sel else ";"
        nombre_reporte = ExportService.generar_nombre_archivo()

        csv_bytes = ExportService.generar_csv_bytes(
            df_filtrado,
            solo_columnas_clave=solo_clave,
            separador=sep_char,
        )

        usuario_email = usuario.get("email", "auditor@secopanalytics.gov.co") if isinstance(usuario, dict) else "auditor"

        st.download_button(
            label="Descargar Contratos Filtrados (CSV)",
            data=csv_bytes,
            file_name=nombre_reporte,
            mime="text/csv",
            help="Descarga el subconjunto de contratos filtrados en formato CSV codificado en UTF-8 con BOM (utf-8-sig) para Microsoft Excel y herramientas de auditoría.",
            on_click=lambda: ExportService.registrar_auditoria_exportacion(
                usuario=usuario_email,
                total_registros=len(df_filtrado),
                query_match=query_mongo
            )
        )

    st.markdown("</div>", unsafe_allow_html=True)
