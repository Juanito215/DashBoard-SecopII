"""
Módulo de Vistas de SECOP-Analytics
Universidad del Valle - Sede Tuluá
"""
from src.views.auth_view import (
    render_login_view,
    render_auth_sidebar,
    render_telemetria_pa_alfa_001,
    render_welcome_header,
    render_rbac_modules_preview
)
from src.views.etl_view import (
    render_etl_view,
    render_telemetria_pa_alfa_002
)
from src.views.ingestion_view import (
    render_ingestion_view
)

__all__ = [
    "render_login_view",
    "render_auth_sidebar",
    "render_telemetria_pa_alfa_001",
    "render_welcome_header",
    "render_rbac_modules_preview",
    "render_etl_view",
    "render_telemetria_pa_alfa_002",
    "render_ingestion_view"
]
