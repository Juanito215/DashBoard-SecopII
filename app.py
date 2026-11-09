"""
SECOP-Analytics: Plataforma de Inteligencia Empresarial para la Contratación Estatal
Universidad del Valle – Sede Tuluá | Facultad de Ingeniería | Ingeniería de Sistemas
Asignatura: Técnicas de Pruebas de Software

Punto de Entrada Principal de la Aplicación Streamlit (Rediseño Figma Style)
Navegación Sidebar First, Arquitectura Ejecutiva y Cero Emojis
"""
from __future__ import annotations
import streamlit as st

from src.controllers.auth_controller import AuthController
from src.views.styles import get_theme_css, CSS_CORPORATIVO
from src.views.auth_view import render_login_view
from src.views.components import render_sidebar_header, render_user_profile_card, render_accessibility_panel
from src.views.dashboard_view import render_dashboard_view
from src.views.consultas_view import render_consultas_view
from src.views.analytics_view import render_analytics_view
from src.views.predictive_view import render_predictive_view
from src.views.data_management_view import render_data_management_view


# 1. Configuración de página de Streamlit
st.set_page_config(
    page_title="SECOP Analytics | Inteligencia de Contratación",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inicialización y Gestión del Estado de Sesión (st.session_state)
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "usuario_datos" not in st.session_state:
    st.session_state.usuario_datos = None

if "latencia_auth_ms" not in st.session_state:
    st.session_state.latencia_auth_ms = 0.0

if "menu_activo" not in st.session_state:
    st.session_state.menu_activo = "Dashboard General"

if "tema" not in st.session_state:
    st.session_state.tema = "claro"

if "alto_contraste" not in st.session_state:
    st.session_state.alto_contraste = False

if "tamano_texto" not in st.session_state:
    st.session_state.tamano_texto = "normal"

# 3. Inyección Dinámica de Estilos CSS Corporativos (Modo Claro / Modo Oscuro / Accesibilidad)
css_actual = get_theme_css(
    tema=st.session_state.tema,
    alto_contraste=st.session_state.alto_contraste,
    tamano_texto=st.session_state.tamano_texto
)
st.markdown(css_actual, unsafe_allow_html=True)


# Callbacks para la autenticación y cierre de sesión
def procesar_login(email: str, password_plana: str) -> None:
    """Procesa el inicio de sesión invocando al AuthController."""
    exito, usuario, latencia = AuthController.autenticar(email, password_plana)
    if exito and usuario:
        st.session_state.autenticado = True
        st.session_state.usuario_datos = usuario
        st.session_state.latencia_auth_ms = latencia
        st.toast(f"Sesión iniciada correctamente ({latencia:.1f} ms)")
        st.rerun()
    else:
        st.error(
            "Credenciales inválidas o cuenta de usuario inactiva. "
            "Por favor verifique el correo y la contraseña ingresados."
        )


def procesar_logout() -> None:
    """
    Ejecuta el cierre de sesión seguro.
    - Registra el cierre en el controlador de auditoría.
    - Limpia íntegramente todas las claves de st.session_state.
    - Redirige de inmediato a la pantalla de login con st.rerun().
    """
    usuario_actual = st.session_state.get("usuario_datos", {})
    email_actual = usuario_actual.get("email") if isinstance(usuario_actual, dict) else None
    AuthController.cerrar_sesion(email=email_actual)
    st.session_state.clear()
    st.rerun()


# ==============================================================================
# 4. FLUJO NO AUTENTICADO: FORMULARIO DE INICIO DE SESIÓN
# ==============================================================================
if not st.session_state.autenticado:
    render_login_view(on_login_callback=procesar_login)
    st.stop()


# ==============================================================================
# 5. FLUJO AUTENTICADO: NAVEGACIÓN LATERAL (SIDEBAR FIRST) Y ENRUTAMIENTO
# ==============================================================================
usuario = st.session_state.usuario_datos

OPCIONES_MENU = [
    "Dashboard General",
    "Explorador de Contratos",
    "Analítica y Tendencias",
    "Gestión de Datos",
    "Inteligencia Predictiva"
]

with st.sidebar:
    render_sidebar_header()
    render_user_profile_card(usuario)

    st.markdown("<div style='font-size:0.75rem; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.05em; margin: 15px 0 8px 6px;'>Navegación</div>", unsafe_allow_html=True)

    try:
        idx_default = OPCIONES_MENU.index(st.session_state.menu_activo)
    except (ValueError, KeyError):
        idx_default = 0

    menu_seleccionado = st.radio(
        label="Navegación Principal",
        options=OPCIONES_MENU,
        index=idx_default,
        label_visibility="collapsed",
        key="navegacion_sidebar_radio"
    )
    st.session_state.menu_activo = menu_seleccionado

    st.markdown("<hr style='margin: 16px 0 10px 0; border: none; border-top: 1px solid var(--border-color);'/>", unsafe_allow_html=True)
    render_accessibility_panel()
    st.markdown("<hr style='margin: 10px 0 12px 0; border: none; border-top: 1px solid var(--border-color);'/>", unsafe_allow_html=True)

    if st.button("Cerrar Sesión", use_container_width=True, type="secondary"):
        procesar_logout()


# Enrutamiento dinámico según la opción seleccionada en la barra lateral
if menu_seleccionado == "Dashboard General":
    render_dashboard_view(usuario)
elif menu_seleccionado == "Explorador de Contratos":
    render_consultas_view(usuario)
elif menu_seleccionado == "Analítica y Tendencias":
    render_analytics_view(usuario)
elif menu_seleccionado == "Gestión de Datos":
    render_data_management_view(usuario)
elif menu_seleccionado == "Inteligencia Predictiva":
    render_predictive_view(usuario)
else:
    render_dashboard_view(usuario)
