"""
SECOP-Analytics: Sistema de Inteligencia Empresarial y Predicción para la Contratación Estatal
Universidad del Valle – Sede Tuluá | Facultad de Ingeniería | Ingeniería de Sistemas
Asignatura: Técnicas de Pruebas de Software

Punto de Entrada Principal de la Aplicación Streamlit
- Implementación de HU-01: Autenticación con MongoDB y RBAC (PA-ALFA-001)
- Implementación de HU-02: Pipeline ETL y Carga en MongoDB (PA-ALFA-002)
"""
import streamlit as st
from src.controllers.auth_controller import AuthController
from src.views.auth_view import (
    render_login_view,
    render_auth_sidebar,
    render_welcome_header,
    render_telemetria_pa_alfa_001,
    render_rbac_modules_preview,
)
from src.views.etl_view import render_etl_view
from src.views.ingestion_view import render_ingestion_view

# 1. Configuración de página de Streamlit
st.set_page_config(
    page_title="SECOP-Analytics | Univalle",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS generales para la interfaz institucional
st.markdown(
    """
    <style>
    /* Ajustes generales de espaciado */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }
    /* Estilo de botones primarios */
    button[kind="primary"] {
        background-color: #C41230 !important;
        border-color: #C41230 !important;
        color: white !important;
        font-weight: 600;
    }
    button[kind="primary"]:hover {
        background-color: #990000 !important;
        border-color: #990000 !important;
    }
    /* Estilo para métricas */
    div[data-testid="stMetricValue"] {
        font-size: 1.55rem !important;
        font-weight: 700;
    }
    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Inicialización y Gestión del Estado de Sesión (st.session_state)
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "usuario_datos" not in st.session_state:
    st.session_state.usuario_datos = None

if "latencia_auth_ms" not in st.session_state:
    st.session_state.latencia_auth_ms = 0.0


# Callbacks para la autenticación y cierre de sesión
def procesar_login(email: str, password_plana: str) -> None:
    """Procesa el inicio de sesión invocando al AuthController."""
    exito, usuario, latencia = AuthController.autenticar(email, password_plana)
    if exito and usuario:
        st.session_state.autenticado = True
        st.session_state.usuario_datos = usuario
        st.session_state.latencia_auth_ms = latencia
        st.toast(f"✅ Autenticación exitosa ({latencia:.2f} ms)", icon="🚀")
        st.rerun()
    else:
        st.error(
            "❌ Credenciales inválidas o usuario inactivo. "
            "Por favor verifique el correo y la contraseña ingresados."
        )


def procesar_logout() -> None:
    """
    Ejecuta el cierre de sesión seguro (HU-03).
    - Registra el cierre en el controlador de auditoría.
    - Limpia íntegramente todas las claves de st.session_state (st.session_state.clear()).
    - Redirige de inmediato a la pantalla de login con st.rerun().
    """
    usuario_actual = st.session_state.get("usuario_datos", {})
    email_actual = usuario_actual.get("email") if isinstance(usuario_actual, dict) else None
    AuthController.cerrar_sesion(email=email_actual)
    st.session_state.clear()
    st.rerun()


# ==============================================================================
# 3. FLUJO NO AUTENTICADO: FORMULARIO DE INICIO DE SESIÓN
# ==============================================================================
if not st.session_state.autenticado:
    render_login_view(on_login_callback=procesar_login)
    st.stop()


# ==============================================================================
# 4. FLUJO AUTENTICADO: DASHBOARD, RBAC Y MÓDULOS DEL SISTEMA
# ==============================================================================
usuario = st.session_state.usuario_datos
latencia_ms = st.session_state.latencia_auth_ms

# Barra lateral con perfil, rol y permisos
render_auth_sidebar(usuario, on_logout_callback=procesar_logout)

# Encabezado institucional de bienvenida
render_welcome_header(usuario)

# Pestañas principales de navegación del sistema
tab_general, tab_ingesta, tab_etl = st.tabs([
    "📊 Panel General y Telemetría PA-ALFA-001 (HU-01)",
    "📥 Ingesta Masiva y Repositorio Singleton (HU-04)",
    "⚙️ Pipeline ETL y Carga NoSQL (HU-02 | PA-ALFA-002)"
])

with tab_general:
    # Panel de Telemetría para el Caso de Prueba PA-ALFA-001
    render_telemetria_pa_alfa_001(latencia_ms, usuario)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Vista previa de disponibilidad de módulos según el rol (RBAC)
    render_rbac_modules_preview(usuario.get("permisos", []))

with tab_ingesta:
    # Módulo de Ingesta Masiva y Repositorio Singleton (HU-04)
    render_ingestion_view(usuario)

with tab_etl:
    # Módulo de Gestión ETL y Carga Masiva en MongoDB (HU-02)
    render_etl_view(usuario)
