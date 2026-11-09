"""
Componentes de Vista para Autenticación y Perfil Institucional
Diseño Ejecutivo y Limpio (Figma Style) sin Emojis ni Jerga Académica
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
from typing import Any
import streamlit as st
from src.views.components import render_sidebar_header, render_user_profile_card


def render_login_view(on_login_callback) -> None:
    """
    Renderiza la vista centrada, corporativa y limpia para el inicio de sesión.
    """
    col_left, col_center, col_right = st.columns([1, 1.8, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 25px; padding: 30px 20px; background: var(--bg-card); border-radius: 18px; border: var(--border-width) solid var(--border-color); box-shadow: var(--card-shadow);">
                <div style="width: 52px; height: 52px; margin: 0 auto 12px auto; border-radius: 14px; background: linear-gradient(135deg, #4F46E5 0%, #3B82F6 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 800; font-size: 1.35rem; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);">
                    SA
                </div>
                <h1 style="color: var(--text-primary); margin: 0 0 4px 0; font-size: 1.75rem; font-weight: 800; letter-spacing: -0.02em;">SECOP Analytics</h1>
                <p style="color: var(--text-muted); font-size: 0.95rem; margin: 0 0 10px 0; font-weight: 500;">
                    Plataforma Corporativa de Inteligencia de Contratación Estatal
                </p>
                <span style="display: inline-block; background-color: var(--bg-main); border: var(--border-width) solid var(--border-color); padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; color: var(--text-secondary); font-weight: 600;">
                    Universidad del Valle – Sede Tuluá
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("form_inicio_sesion", clear_on_submit=False):
            st.markdown(
                """
                <div style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">
                    Inicio de Sesión
                </div>
                <div style="font-size: 0.84rem; color: var(--text-muted); margin-bottom: 14px;">
                    Ingrese sus credenciales autorizadas para acceder a la plataforma.
                </div>
                """,
                unsafe_allow_html=True
            )

            email_input = st.text_input(
                "Correo Institucional",
                placeholder="ejemplo@secopanalytics.gov.co",
                help="Correo institucional registrado en el sistema."
            )

            password_input = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••••••",
                help="Su contraseña es validada mediante cifrado seguro."
            )

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            boton_submit = st.form_submit_button(
                "Acceder a la Plataforma",
                use_container_width=True,
                type="primary"
            )

            if boton_submit:
                if not email_input or not password_input:
                    st.warning("Por favor ingrese tanto el correo institucional como la contraseña.")
                else:
                    on_login_callback(email_input, password_input)

        # Acceso rápido de credenciales de demostración
        with st.expander("Perfiles de Demostración y Prueba", expanded=False):
            st.markdown(
                """
                | Perfil | Correo Institucional | Contraseña | Alcance de Acceso |
                | :--- | :--- | :--- | :--- |
                | **Administrador** | `admin@secopanalytics.gov.co` | `Admin2026*` | Acceso Total, Sincronización ETL, Modelos |
                | **Analista BI** | `analista@secopanalytics.gov.co` | `Secop2026*` | Consultas, Tendencias, Simulación |
                | **Auditor Fiscal** | `auditor@secopanalytics.gov.co` | `Auditor2026*` | Auditoría, Explorador, Veeduría Ciudadana |
                """
            )


def render_auth_sidebar(usuario: dict[str, Any], on_logout_callback) -> None:
    """
    Renderiza la barra lateral con branding, perfil limpio del usuario y botón de cierre de sesión.
    (Reglas 2 y 3: Cero emojis, sin volcado de permisos crudos).
    """
    with st.sidebar:
        render_sidebar_header()
        render_user_profile_card(usuario)

        st.markdown("<hr style='margin: 15px 0 10px 0; border: none; border-top: 1px solid #F1F5F9;'/>", unsafe_allow_html=True)

        if st.button("Cerrar Sesión", use_container_width=True, type="secondary"):
            on_logout_callback()


def render_welcome_header(usuario: dict[str, Any]) -> None:
    """Función de compatibilidad retroactiva."""
    pass


def render_telemetria_pa_alfa_001(latencia_ms: float, usuario: dict[str, Any]) -> None:
    """Función de compatibilidad retroactiva."""
    pass


def render_rbac_modules_preview(permisos: list[str]) -> None:
    """Función de compatibilidad retroactiva."""
    pass
