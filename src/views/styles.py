"""
Estilos CSS Corporativos para SECOP-Analytics (Inspirado en Diseño Moderno de Figma)
Soporte Integral para Modo Claro, Modo Oscuro y Opciones de Accesibilidad (WCAG AAA)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations


def get_theme_css(
    tema: str = "claro",
    alto_contraste: bool = False,
    tamano_texto: str = "normal"
) -> str:
    """
    Genera la hoja de estilos CSS corporativa adaptada a:
    - Tema: 'claro' (Figma Slate) o 'oscuro' (Night Slate)
    - Modo Alto Contraste: True (WCAG AAA / bordes negros/blancos puros) o False
    - Tamaño de Tipografía: 'normal', 'grande', 'extra_grande'
    """
    es_oscuro = tema.lower() == "oscuro"

    # 1. Definición de Escalas Tipográficas
    if tamano_texto.lower() in ["extra_grande", "extra grande", "extragrande"]:
        fs_base = "1.15rem"
        fs_title = "2.1rem"
        fs_card_title = "1.35rem"
        fs_kpi = "2.15rem"
        fs_sub = "1.05rem"
        fs_small = "0.95rem"
        lh_base = "1.65"
    elif tamano_texto.lower() in ["grande"]:
        fs_base = "1.05rem"
        fs_title = "1.85rem"
        fs_card_title = "1.2rem"
        fs_kpi = "1.85rem"
        fs_sub = "0.98rem"
        fs_small = "0.88rem"
        lh_base = "1.6"
    else:  # normal
        fs_base = "0.935rem"
        fs_title = "1.65rem"
        fs_card_title = "1.05rem"
        fs_kpi = "1.65rem"
        fs_sub = "0.88rem"
        fs_small = "0.78rem"
        lh_base = "1.5"

    # 2. Definición de Paletas según Tema y Contraste
    if es_oscuro:
        if alto_contraste:
            bg_main = "#000000"
            bg_sidebar = "#000000"
            bg_card = "#05070A"
            bg_card_hover = "#111827"
            border_color = "#FFFFFF"
            border_width = "2px"
            text_primary = "#FFFFFF"
            text_secondary = "#FFFFFF"
            text_muted = "#E2E8F0"
            input_bg = "#000000"
            input_border = "#FFFFFF"
            input_text = "#FFFFFF"
            input_placeholder = "#CBD5E1"
            radio_selected_bg = "#1E1B4B"
            radio_selected_text = "#FFFFFF"
            btn_secondary_bg = "#000000"
            btn_num_bg = "#0A0A0A"
            btn_num_hover = "#1F2937"
            tag_bg = "#1E1B4B"
            tag_text = "#FFFFFF"
            tag_border = "#FFFFFF"
            dropdown_hover_bg = "#312E81"
            dropdown_hover_text = "#FFFFFF"
            card_shadow = "none"
            focus_outline = "3px solid #FFFFFF"
        else:
            bg_main = "#0F172A"
            bg_sidebar = "#090D16"
            bg_card = "#1E293B"
            bg_card_hover = "#283548"
            border_color = "#334155"
            border_width = "1px"
            text_primary = "#F8FAFC"
            text_secondary = "#E2E8F0"
            text_muted = "#94A3B8"
            input_bg = "#0B0F19"
            input_border = "#475569"
            input_text = "#F8FAFC"
            input_placeholder = "#64748B"
            radio_selected_bg = "#312E81"
            radio_selected_text = "#C7D2FE"
            btn_secondary_bg = "#1E293B"
            btn_num_bg = "#1E293B"
            btn_num_hover = "#334155"
            tag_bg = "#312E81"
            tag_text = "#E0E7FF"
            tag_border = "#4338CA"
            dropdown_hover_bg = "#312E81"
            dropdown_hover_text = "#FFFFFF"
            card_shadow = "0 4px 20px rgba(0, 0, 0, 0.4)"
            focus_outline = "2px solid #818CF8"
    else:  # Modo Claro
        if alto_contraste:
            bg_main = "#FFFFFF"
            bg_sidebar = "#FFFFFF"
            bg_card = "#FFFFFF"
            bg_card_hover = "#F8FAFC"
            border_color = "#000000"
            border_width = "2px"
            text_primary = "#000000"
            text_secondary = "#000000"
            text_muted = "#1E293B"
            input_bg = "#FFFFFF"
            input_border = "#000000"
            input_text = "#000000"
            input_placeholder = "#334155"
            radio_selected_bg = "#EEF2FF"
            radio_selected_text = "#000000"
            btn_secondary_bg = "#FFFFFF"
            btn_num_bg = "#F8FAFC"
            btn_num_hover = "#E2E8F0"
            tag_bg = "#EEF2FF"
            tag_text = "#000000"
            tag_border = "#000000"
            dropdown_hover_bg = "#EEF2FF"
            dropdown_hover_text = "#000000"
            card_shadow = "none"
            focus_outline = "3px solid #000000"
        else:
            bg_main = "#F8FAFC"
            bg_sidebar = "#FFFFFF"
            bg_card = "#FFFFFF"
            bg_card_hover = "#F1F5F9"
            border_color = "#E2E8F0"
            border_width = "1px"
            text_primary = "#0F172A"
            text_secondary = "#1E293B"
            text_muted = "#475569"
            input_bg = "#FFFFFF"
            input_border = "#CBD5E1"
            input_text = "#0F172A"
            input_placeholder = "#64748B"
            radio_selected_bg = "#EEF2FF"
            radio_selected_text = "#4F46E5"
            btn_secondary_bg = "#FFFFFF"
            btn_num_bg = "#F1F5F9"
            btn_num_hover = "#E2E8F0"
            tag_bg = "#EEF2FF"
            tag_text = "#4F46E5"
            tag_border = "#C7D2FE"
            dropdown_hover_bg = "#EEF2FF"
            dropdown_hover_text = "#4F46E5"
            card_shadow = "0 4px 16px rgba(0, 0, 0, 0.03)"
            focus_outline = "2px solid #4F46E5"

    return f"""
<style>
/* Importación de fuentes ejecutivas */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root {{
    --bg-main: {bg_main};
    --bg-sidebar: {bg_sidebar};
    --bg-card: {bg_card};
    --bg-card-hover: {bg_card_hover};
    --border-color: {border_color};
    --border-width: {border_width};
    --text-primary: {text_primary};
    --text-secondary: {text_secondary};
    --text-muted: {text_muted};
    --input-bg: {input_bg};
    --input-border: {input_border};
    --input-text: {input_text};
    --input-placeholder: {input_placeholder};
    --radio-selected-bg: {radio_selected_bg};
    --radio-selected-text: {radio_selected_text};
    --btn-secondary-bg: {btn_secondary_bg};
    --btn-num-bg: {btn_num_bg};
    --btn-num-hover: {btn_num_hover};
    --tag-bg: {tag_bg};
    --tag-text: {tag_text};
    --tag-border: {tag_border};
    --dropdown-hover-bg: {dropdown_hover_bg};
    --dropdown-hover-text: {dropdown_hover_text};
    --card-shadow: {card_shadow};
    --focus-outline: {focus_outline};
    --font-size-base: {fs_base};
    --font-size-title: {fs_title};
    --font-size-card-title: {fs_card_title};
    --font-size-kpi: {fs_kpi};
    --font-size-sub: {fs_sub};
    --font-size-small: {fs_small};
    --line-height-base: {lh_base};
}}

/* ==========================================================================
   CONFIGURACIÓN GLOBAL DE LA APLICACIÓN Y CONTRASTE
   ========================================================================== */
html, body, [class*="css"], .stApp {{
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: var(--bg-main) !important;
    color: var(--text-primary) !important;
    font-size: var(--font-size-base) !important;
    line-height: var(--line-height-base) !important;
}}

/* Reducción de espaciados superiores */
.block-container {{
    padding-top: 1.2rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}}

/* Ocultar elementos decorativos innecesarios pero preservar barra de controles */
#MainMenu, footer {{
    visibility: hidden !important;
    height: 0px !important;
}}

header[data-testid="stHeader"] {{
    background: transparent !important;
    color: var(--text-primary) !important;
    height: 3rem !important;
    z-index: 9999 !important;
}}

/* Botón flotante para expandir/mostrar la barra lateral cuando está minimizada */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[data-testid="collapsedControl"],
button[data-testid="stSidebarCollapsedControl"] {{
    visibility: visible !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: fixed !important;
    top: 14px !important;
    left: 14px !important;
    z-index: 100000 !important;
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border: var(--border-width) solid var(--border-color) !important;
    border-radius: 10px !important;
    padding: 6px 10px !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12) !important;
    cursor: pointer !important;
    transition: all 0.2s ease-in-out !important;
}}

[data-testid="collapsedControl"]:hover,
[data-testid="stSidebarCollapsedControl"]:hover,
button[data-testid="collapsedControl"]:hover,
button[data-testid="stSidebarCollapsedControl"]:hover {{
    background-color: var(--bg-card-hover) !important;
    border-color: #4F46E5 !important;
    transform: scale(1.05);
}}

[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] svg,
button[data-testid="stSidebarCollapseButton"] svg {{
    stroke: var(--text-primary) !important;
    color: var(--text-primary) !important;
    fill: none !important;
    width: 20px !important;
    height: 20px !important;
}}

button[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] {{
    color: var(--text-primary) !important;
    background-color: transparent !important;
    border-radius: 8px !important;
}}

button[data-testid="stSidebarCollapseButton"]:hover {{
    background-color: var(--bg-card-hover) !important;
    color: var(--text-primary) !important;
}}

/* ==========================================================================
   BARRA LATERAL (SIDEBAR)
   ========================================================================== */
section[data-testid="stSidebar"] {{
    background-color: var(--bg-sidebar) !important;
    border-right: var(--border-width) solid var(--border-color) !important;
    box-shadow: 2px 0 12px rgba(0, 0, 0, 0.05) !important;
}}

section[data-testid="stSidebar"] > div:first-child {{
    background-color: var(--bg-sidebar) !important;
    padding-top: 1.2rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
}}

/* Logo e Identidad Institucional */
.sidebar-branding {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 4px 16px 4px;
    margin-bottom: 12px;
    border-bottom: var(--border-width) solid var(--border-color);
}}

.brand-icon {{
    width: 42px;
    height: 42px;
    border-radius: 12px;
    background: linear-gradient(135deg, #4F46E5 0%, #3B82F6 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF !important;
    font-weight: 800;
    font-size: 1.15rem;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
    flex-shrink: 0;
}}

.brand-title {{
    font-size: 1.15rem;
    font-weight: 800;
    color: var(--text-primary) !important;
    line-height: 1.2;
    letter-spacing: -0.02em;
}}

.brand-subtitle {{
    font-size: 0.72rem;
    color: var(--text-muted) !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

/* ==========================================================================
   NAVEGACIÓN VERTICAL (RADIO BUTTONS) - CONTRASTE GARANTIZADO
   ========================================================================== */
div[data-testid="stRadio"] > div[role="radiogroup"] {{
    gap: 6px !important;
}}

/* Asegurar que las etiquetas y textos NUNCA sean invisibles ni blanco sobre blanco */
div[data-testid="stRadio"] label {{
    background-color: transparent !important;
    border: var(--border-width) solid transparent !important;
    border-radius: 10px !important;
    padding: 8px 12px !important;
    transition: all 0.2s ease-in-out !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    margin-bottom: 3px !important;
}}

div[data-testid="stRadio"] label p,
div[data-testid="stRadio"] label span,
div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {{
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: var(--font-size-base) !important;
    opacity: 1 !important;
}}

div[data-testid="stRadio"] label:hover {{
    background-color: var(--bg-card-hover) !important;
}}

div[data-testid="stRadio"] label:hover p,
div[data-testid="stRadio"] label:hover span {{
    color: var(--text-primary) !important;
}}

/* Estado Seleccionado */
div[data-testid="stRadio"] label[data-checked="true"],
div[data-testid="stRadio"] label:has(input:checked) {{
    background-color: var(--radio-selected-bg) !important;
    border: var(--border-width) solid var(--border-color) !important;
}}

div[data-testid="stRadio"] label[data-checked="true"] p,
div[data-testid="stRadio"] label:has(input:checked) p,
div[data-testid="stRadio"] label:has(input:checked) span {{
    color: var(--radio-selected-text) !important;
    font-weight: 700 !important;
}}

/* Perfil de Usuario en Sidebar */
.user-profile-card {{
    background: var(--bg-card) !important;
    border: var(--border-width) solid var(--border-color) !important;
    border-radius: 14px;
    padding: 12px 14px;
    margin-top: 10px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: var(--card-shadow);
}}

.user-avatar {{
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--radio-selected-bg);
    color: var(--radio-selected-text);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.95rem;
    border: 2px solid var(--border-color);
    flex-shrink: 0;
}}

.user-info {{
    flex: 1;
    min-width: 0;
}}

.user-name {{
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary) !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.user-email {{
    font-size: 0.75rem;
    color: var(--text-muted) !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.role-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-top: 4px;
}}

.role-admin {{
    background-color: #FEF2F2;
    color: #DC2626;
    border: 1px solid #FEE2E2;
}}

.role-analyst {{
    background-color: #EEF2FF;
    color: #4F46E5;
    border: 1px solid #E0E7FF;
}}

.role-auditor {{
    background-color: #ECFDF5;
    color: #059669;
    border: 1px solid #D1FAE5;
}}

/* ==========================================================================
   TARJETAS EJECUTIVAS (CARDS)
   ========================================================================== */
.executive-card {{
    background-color: var(--bg-card) !important;
    border: var(--border-width) solid var(--border-color) !important;
    border-radius: 16px;
    padding: 22px;
    box-shadow: var(--card-shadow);
    margin-bottom: 18px;
    color: var(--text-primary) !important;
}}

.card-header-flex {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
}}

.card-title {{
    font-size: var(--font-size-card-title) !important;
    font-weight: 700;
    color: var(--text-primary) !important;
    margin: 0;
    letter-spacing: -0.01em;
}}

.card-action {{
    color: var(--text-muted) !important;
    font-size: var(--font-size-small) !important;
    font-weight: 500;
}}

/* KPI Cards Superiores */
.kpi-card {{
    background-color: var(--bg-card) !important;
    border: var(--border-width) solid var(--border-color) !important;
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: var(--card-shadow);
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 104px;
}}

.kpi-icon-circle {{
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}

.kpi-circle-blue {{
    background-color: #EFF6FF;
    color: #3B82F6;
}}

.kpi-circle-amber {{
    background-color: #FEF3C7;
    color: #D97706;
}}

.kpi-circle-orange {{
    background-color: #FFEDD5;
    color: #EA580C;
}}

.kpi-circle-purple {{
    background-color: #F3E8FF;
    color: #9333EA;
}}

.kpi-number {{
    font-size: var(--font-size-kpi) !important;
    font-weight: 800;
    color: var(--text-primary) !important;
    line-height: 1.15;
    letter-spacing: -0.02em;
}}

.kpi-label {{
    font-size: var(--font-size-small) !important;
    color: var(--text-muted) !important;
    font-weight: 600;
    margin-top: 3px;
}}

.kpi-trend {{
    font-size: 0.75rem;
    font-weight: 600;
    margin-top: 2px;
}}

.trend-positive {{
    color: #10B981 !important;
}}

.trend-neutral {{
    color: var(--text-muted) !important;
}}

/* Barra Superior Ejecutiva */
.executive-topbar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0 18px 0;
    margin-bottom: 6px;
}}

.topbar-title {{
    font-size: var(--font-size-title) !important;
    font-weight: 800;
    color: var(--text-primary) !important;
    letter-spacing: -0.025em;
    margin: 0;
}}

.topbar-subtitle {{
    font-size: var(--font-size-sub) !important;
    color: var(--text-muted) !important;
    margin-top: 2px;
}}

.date-pill {{
    background: var(--bg-card) !important;
    border: var(--border-width) solid var(--border-color) !important;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: var(--font-size-small) !important;
    font-weight: 600;
    color: var(--text-secondary) !important;
    box-shadow: var(--card-shadow);
}}

/* ==========================================================================
   INPUTS Y CONTROLES BASEWEB - ALTO CONTRASTE GARANTIZADO
   ========================================================================== */
/* Etiquetas de todos los widgets de Streamlit */
div[data-testid="stWidgetLabel"] label,
div[data-testid="stWidgetLabel"] p,
label, label p {{
    color: var(--text-primary) !important;
    font-size: var(--font-size-base) !important;
    font-weight: 600 !important;
}}

/* Contenedores de selección y entradas de texto */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
    background-color: var(--input-bg) !important;
    color: var(--input-text) !important;
    border: var(--border-width) solid var(--input-border) !important;
    border-radius: 10px !important;
    font-size: var(--font-size-base) !important;
}}

div[data-baseweb="input"] input {{
    color: var(--input-text) !important;
    background-color: transparent !important;
}}

/* Botones de número +/- */
div[data-testid="stNumberInput"] button {{
    background-color: var(--btn-num-bg) !important;
    color: var(--text-primary) !important;
    border: var(--border-width) solid var(--input-border) !important;
}}

div[data-testid="stNumberInput"] button:hover {{
    background-color: var(--btn-num-hover) !important;
    color: var(--text-primary) !important;
}}

/* Placeholders visibles */
div[data-baseweb="select"] [data-baseweb="placeholder"],
::placeholder {{
    color: var(--input-placeholder) !important;
    opacity: 1 !important;
}}

/* Etiquetas / Tags de Multiselect */
div[data-baseweb="tag"] {{
    background-color: var(--tag-bg) !important;
    color: var(--tag-text) !important;
    border: var(--border-width) solid var(--tag-border) !important;
    border-radius: 6px !important;
}}

div[data-baseweb="tag"] span {{
    color: var(--tag-text) !important;
    font-weight: 600 !important;
}}

/* Menú desplegable Popover */
div[data-baseweb="popover"],
div[data-baseweb="menu"],
ul[role="listbox"] {{
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border: var(--border-width) solid var(--border-color) !important;
    border-radius: 10px !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15) !important;
}}

li[role="option"] {{
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    font-size: var(--font-size-base) !important;
}}

li[role="option"]:hover,
li[role="option"][aria-selected="true"] {{
    background-color: var(--dropdown-hover-bg) !important;
    color: var(--dropdown-hover-text) !important;
}}

/* Párrafos, títulos y leyendas de Streamlit */
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] span,
div[data-testid="stMarkdownContainer"] li {{
    color: var(--text-primary) !important;
}}

div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4,
div[data-testid="stMarkdownContainer"] h5 {{
    color: var(--text-primary) !important;
}}

div[data-testid="stCaptionContainer"] p,
.stCaption {{
    color: var(--text-muted) !important;
    font-size: var(--font-size-small) !important;
    font-weight: 500 !important;
}}

/* Métricas integradas */
div[data-testid="stMetricValue"] {{
    color: var(--text-primary) !important;
    font-weight: 800 !important;
}}

div[data-testid="stMetricLabel"] {{
    color: var(--text-muted) !important;
    font-weight: 600 !important;
}}

/* Tablas estilizadas */
div[data-testid="stDataFrame"] {{
    border-radius: 12px !important;
    overflow: hidden !important;
    border: var(--border-width) solid var(--border-color) !important;
}}

/* Botones Principales y Secundarios */
button[kind="primary"] {{
    background-color: #4F46E5 !important;
    border: var(--border-width) solid #4F46E5 !important;
    border-radius: 10px !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: var(--font-size-base) !important;
    padding: 0.5rem 1.2rem !important;
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25) !important;
    transition: all 0.2s ease !important;
}}

button[kind="primary"]:hover {{
    background-color: #4338CA !important;
    border-color: #4338CA !important;
    transform: translateY(-1px);
}}

button[kind="secondary"] {{
    background-color: var(--btn-secondary-bg) !important;
    border: var(--border-width) solid var(--border-color) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: var(--font-size-base) !important;
    transition: all 0.2s ease !important;
}}

button[kind="secondary"]:hover {{
    background-color: var(--bg-card-hover) !important;
    color: var(--text-primary) !important;
    border-color: var(--input-border) !important;
}}

/* Accesibilidad: Anillos de enfoque */
button:focus-visible,
input:focus-visible,
[role="radiogroup"] label:focus-visible {{
    outline: var(--focus-outline) !important;
    outline-offset: 2px !important;
}}
</style>
"""


# Constante para compatibilidad retroactiva directa
CSS_CORPORATIVO = get_theme_css("claro", alto_contraste=False, tamano_texto="normal")
