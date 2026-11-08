"""
SECOP-Analytics: Sistema de Inteligencia Empresarial y Predicción para la Contratación Estatal
Universidad del Valle – Sede Tuluá | Facultad de Ingeniería | Ingeniería de Sistemas
Asignatura: Técnicas de Pruebas de Software

Punto de Entrada Principal de la Aplicación Streamlit
Implementación de HU-01: Autenticación con MongoDB y RBAC
Validación de Caso de Prueba de Aceptación: PA-ALFA-001
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
        font-size: 1.6rem !important;
        font-weight: 700;
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
    """Ejecuta el cierre de sesión seguro (HU-03)."""
    st.session_state.autenticado = False
    st.session_state.usuario_datos = None
    st.session_state.latencia_auth_ms = 0.0
    st.rerun()


# ==============================================================================
# 3. FLUJO NO AUTENTICADO: FORMULARIO DE INICIO DE SESIÓN
# ==============================================================================
if not st.session_state.autenticado:
    render_login_view(on_login_callback=procesar_login)
    st.stop()


# ==============================================================================
# 4. FLUJO AUTENTICADO: DASHBOARD Y PANEL DE TELEMETRÍA (PA-ALFA-001)
# ==============================================================================
usuario = st.session_state.usuario_datos
latencia_ms = st.session_state.latencia_auth_ms

# Barra lateral con perfil, rol y permisos
render_auth_sidebar(usuario, on_logout_callback=procesar_logout)

# Encabezado institucional de bienvenida
render_welcome_header(usuario)

# Panel de Telemetría para el Caso de Prueba PA-ALFA-001
render_telemetria_pa_alfa_001(latencia_ms, usuario)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# Vista previa de disponibilidad de módulos según el rol (RBAC)
render_rbac_modules_preview(usuario.get("permisos", []))
