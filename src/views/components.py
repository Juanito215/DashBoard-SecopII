"""
Componentes Visuales Ejecutivos Reutilizables (Inspirado en Diseño Figma)
Iconos Vectoriales SVG sin Emojis y Tarjetas de Alto Nivel
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
from typing import Any
import streamlit as st


# ==============================================================================
# ICONOS VECTORIALES SVG PUROS (CERO EMOJIS)
# ==============================================================================
SVG_ICONS = {
    "dashboard": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>""",
    "explorer": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>""",
    "analytics": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>""",
    "data": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>""",
    "predictive": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>""",
    "contract": """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>""",
    "money": """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>""",
    "addition": """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>""",
    "risk": """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>""",
    "calendar": """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>"""
}


def render_sidebar_header() -> None:
    """Renderiza el isotipo y título corporativo de SECOP Analytics en la barra lateral."""
    st.markdown(
        """
        <div class="sidebar-branding">
            <div class="brand-icon">SA</div>
            <div>
                <div class="brand-title">SECOP Analytics</div>
                <div class="brand-subtitle">Plataforma BI Ejecutiva</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_user_profile_card(usuario: dict[str, Any]) -> None:
    """
    Renderiza la tarjeta limpia del perfil de usuario en el menú lateral:
    Avatar con iniciales, Nombre, Correo institucional y Rol en badge sutil (Criterio 3 / Cero emojis / Sin permisos crudos).
    """
    nombre = usuario.get("nombre", "Usuario").strip()
    rol = usuario.get("rol", "Analista")
    email = usuario.get("email", "").strip()

    # Obtención de iniciales
    partes = nombre.split()
    if len(partes) >= 2:
        iniciales = f"{partes[0][0]}{partes[1][0]}".upper()
    elif len(partes) == 1 and partes[0]:
        iniciales = partes[0][:2].upper()
    else:
        iniciales = "SA"

    # Mapeo de clase y etiqueta del rol
    if "admin" in rol.lower():
        role_class = "role-admin"
        role_label = "Administrador"
    elif "auditor" in rol.lower() or "veedor" in rol.lower():
        role_class = "role-auditor"
        role_label = "Auditor Fiscal"
    else:
        role_class = "role-analyst"
        role_label = "Analista BI"

    st.markdown(
        f"""
        <div class="user-profile-card">
            <div class="user-avatar">{iniciales}</div>
            <div class="user-info">
                <div class="user-name">{nombre}</div>
                <div class="user-email">{email}</div>
                <span class="role-badge {role_class}">{role_label}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_topbar(titulo: str, subtitulo: str, etiqueta_fecha: str = "Vigencias 2021 – 2026") -> None:
    """
    Renderiza la barra superior ejecutiva con título del módulo, subtítulo y pastilla de fecha (Figma style).
    """
    st.markdown(
        f"""
        <div class="executive-topbar">
            <div>
                <h1 class="topbar-title">{titulo}</h1>
                <div class="topbar-subtitle">{subtitulo}</div>
            </div>
            <div class="date-pill">
                <span style="display: inline-flex; align-items: center; gap: 6px;">
                    {SVG_ICONS['calendar']}
                    {etiqueta_fecha}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_kpi_card(
    titulo: str,
    valor: str,
    tendencia: str,
    icono_key: str = "contract",
    color_circulo: str = "blue"
) -> None:
    """
    Renderiza una tarjeta de métrica ejecutiva idéntica a la plantilla de Figma:
    Micro-icono circular en pastel, número grande en negrita y etiqueta secundaria limpia.
    """
    svg_icon = SVG_ICONS.get(icono_key, SVG_ICONS["contract"])
    circulo_class = f"kpi-circle-{color_circulo}"

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-icon-circle {circulo_class}">
                {svg_icon}
            </div>
            <div>
                <div class="kpi-number">{valor}</div>
                <div class="kpi-label">{titulo}</div>
                <div class="kpi-trend trend-neutral">{tendencia}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def get_status_badge_html(estado: str) -> str:
    """Genera una pastilla de estado HTML sobria y estilizada."""
    estado_limpio = str(estado).strip().title()
    estado_lower = estado_limpio.lower()

    if "celebrado" in estado_lower or "activo" in estado_lower:
        clase = "badge-celebrado"
    elif "ejecuci" in estado_lower:
        clase = "badge-ejecucion"
    elif "liquidado" in estado_lower:
        clase = "badge-liquidado"
    elif "modificado" in estado_lower:
        clase = "badge-modificado"
    else:
        clase = "badge-terminado"

    return f'<span class="badge-status {clase}">{estado_limpio}</span>'


def render_accessibility_panel() -> None:
    """
    Renderiza el panel de accesibilidad, alto contraste y selección de tema visual en el sidebar.
    Cumple con estándares WCAG AAA para legibilidad, escala tipográfica y temas de contraste.
    """
    with st.expander("Accesibilidad y Visualización", expanded=False):
        # 1. Modo Oscuro / Modo Claro
        tema_actual = st.session_state.get("tema", "claro")
        es_oscuro = st.toggle(
            "Modo Oscuro",
            value=(tema_actual == "oscuro"),
            key="toggle_modo_oscuro_panel",
            help="Alterna entre el tema visual claro ejecutivo y el modo noche de alta inmersión."
        )
        nuevo_tema = "oscuro" if es_oscuro else "claro"
        if nuevo_tema != tema_actual:
            st.session_state.tema = nuevo_tema
            st.rerun()

        # 2. Modo Alto Contraste (WCAG AAA)
        alto_contraste_actual = st.session_state.get("alto_contraste", False)
        nuevo_contraste = st.checkbox(
            "Alto Contraste (WCAG AAA)",
            value=alto_contraste_actual,
            key="checkbox_alto_contraste_panel",
            help="Maximiza la diferenciación de bordes y la relación de contraste cromático."
        )
        if nuevo_contraste != alto_contraste_actual:
            st.session_state.alto_contraste = nuevo_contraste
            st.rerun()

        # 3. Escala Tipográfica para Accesibilidad Visual
        opciones_tamano = ["Normal", "Grande", "Extra Grande"]
        tamano_actual = st.session_state.get("tamano_texto", "normal").lower()
        mapa_indices = {"normal": 0, "grande": 1, "extra_grande": 2, "extra grande": 2}
        idx_tam = mapa_indices.get(tamano_actual, 0)

        sel_tam = st.selectbox(
            "Tamaño de Letra:",
            options=opciones_tamano,
            index=idx_tam,
            key="select_tamano_letra_panel",
            help="Ajusta proporcionalmente la escala de fuentes de toda la interfaz corporativa."
        )
        mapa_valores = {"Normal": "normal", "Grande": "grande", "Extra Grande": "extra_grande"}
        nuevo_tam = mapa_valores.get(sel_tam, "normal")
        if nuevo_tam != tamano_actual:
            st.session_state.tamano_texto = nuevo_tam
            st.rerun()

