"""
Componentes de Vista para Ingesta Masiva y Repositorio Singleton
Historia de Usuario: HU-04 (Ingesta y Lectura de Datos Masivos)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
from typing import Any
import streamlit as st
from src.database.data_repository import get_data_repository


def render_ingestion_view(usuario: dict[str, Any]) -> None:
    """
    Renderiza el panel de Ingesta Masiva y estado del Repositorio Singleton (HU-04).
    Aplica control RBAC para habilitar recarga y subida de archivos exclusivamente a administradores.
    """
    st.markdown("## 📥 Ingesta Masiva y Repositorio Central Singleton (HU-04)")
    st.caption("Alimentación y gestión del repositorio analítico central en memoria RAM aplicando el Patrón Creacional Singleton.")

    rol = usuario.get("rol", "")
    permisos = usuario.get("permisos", [])
    es_admin = (rol == "Admin") or ("etl_carga" in permisos)

    # Obtención de la instancia Singleton cacheada
    repo = get_data_repository()

    # Si aún no está cargado en memoria, cargar automáticamente el dataset por defecto
    if not repo.esta_cargado():
        with st.spinner("Inicializando instancia Singleton y cargando dataset local en memoria..."):
            try:
                repo.cargar_fuente()
            except Exception as e:
                st.error(f"❌ Error al inicializar el repositorio Singleton: {e}")

    # 1. Controles Administrativos según RBAC
    if es_admin:
        st.markdown("### ⚙️ Controles de Ingesta (Rol Administrador)")
        col_up, col_btn = st.columns([2, 1])

        with col_up:
            archivo_subido = st.file_uploader(
                "Cargar archivo CSV de contratación SECOP II (2021–2026)",
                type=["csv"],
                key="uploader_hu04",
                help="Permite actualizar el repositorio central con un lote nuevo o personalizado."
            )

        with col_btn:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            btn_recargar = st.button(
                "🔄 Recargar Muestra Local (10k)",
                use_container_width=True,
                type="primary",
                help="Vuelve a cargar en memoria el archivo 'secop muestra 10k 2022.csv'."
            )

        # Procesar recarga o subida
        if archivo_subido is not None:
            if st.button("📥 Procesar Archivo Subido en Repositorio", use_container_width=True):
                with st.spinner(f"Ingestando archivo '{archivo_subido.name}' en memoria..."):
                    df_nuevo, met_nuevo = repo.cargar_fuente(archivo_subido)
                    st.success(f"✅ ¡Dataset '{archivo_subido.name}' cargado con éxito en {met_nuevo['tiempo_segundos']}s!")
                    st.rerun()

        elif btn_recargar:
            with st.spinner("Recargando dataset local de referencia en la instancia Singleton..."):
                df_rec, met_rec = repo.cargar_fuente()
                st.success(f"✅ ¡Dataset local recargado exitosamente en {met_rec['tiempo_segundos']}s!")
                st.rerun()

    else:
        st.info(
            f"ℹ️ **Modo Consulta (Solo Lectura):** Como usuario con rol **{rol}**, "
            "puede inspeccionar las métricas de rendimiento y la integridad de los datos "
            "ingestados por el Administrador en la instancia única del sistema."
        )

    # 2. Métricas Operativas de Ingesta (Criterio de Aceptación 2)
    metricas = repo.obtener_metricas()
    df_actual = repo.obtener_dataframe()

    st.markdown("<hr style='margin: 15px 0 20px 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)
    st.markdown("### 📊 Métricas Operativas de Ingesta y Rendimiento")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    with col_m1:
        st.metric(
            label="⏱️ Tiempo de Ingesta (t_carga)",
            value=f"{metricas.get('tiempo_segundos', 0.0)} s",
            delta="Lectura Vectorizada (< 3.0s)"
        )

    with col_m2:
        st.metric(
            label="📈 Total Registros Leídos",
            value=f"{metricas.get('total_registros_leidos', 0):,}",
            delta=f"{metricas.get('columnas_detectadas', 0)} Columnas"
        )

    with col_m3:
        st.metric(
            label="💾 Memoria RAM Ocupada",
            value=f"{metricas.get('tamano_memoria_mb', 0.0)} MB",
            delta="En Memoria Principal"
        )

    with col_m4:
        st.metric(
            label="🔒 Patrón Creacional",
            value=metricas.get("estado_singleton", "ACTIVA"),
            delta="Singleton @cache_resource"
        )

    # Información complementaria de origen y MongoDB
    sync_mongo = repo.sincronizar_con_mongo()
    st.markdown(
        f"""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 16px; margin: 12px 0 20px 0; font-size: 0.88rem; color: #475569;">
            📁 <strong>Fuente Activa:</strong> <code>{metricas.get('origen', 'secop muestra 10k 2022.csv')}</code> &nbsp;|&nbsp; 
            🍃 <strong>Estado en MongoDB (contratos):</strong> {sync_mongo.get('contratos_en_mongo', 0):,} documentos persistidos &nbsp;|&nbsp; 
            ⚡ <strong>Acceso Concurrente:</strong> Referencia compartida sin lecturas de disco duplicadas.
        </div>
        """,
        unsafe_allow_html=True
    )

    # 3. Visualización de Integridad de Datos
    if df_actual is not None and not df_actual.empty:
        st.markdown("### 🔍 Inspección Preliminar de Integridad (Primeras 10 Filas)")
        st.caption("Visualización tabular de las columnas originales para verificar tipos y estructura antes del procesamiento analítico.")
        st.dataframe(df_actual.head(10), use_container_width=True)
    else:
        st.warning("⚠️ No hay datos cargados actualmente en el repositorio.")
