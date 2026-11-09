"""
Módulo de Vistas Ejecutivas de SECOP-Analytics (Figma Style)
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from src.views.auth_view import (
    render_login_view,
    render_auth_sidebar,
    render_telemetria_pa_alfa_001,
    render_welcome_header,
    render_rbac_modules_preview
)
from src.views.dashboard_view import render_dashboard_view
from src.views.consultas_view import render_consultas_view
from src.views.analytics_view import render_analytics_view
from src.views.predictive_view import render_predictive_view
from src.views.data_management_view import render_data_management_view
from src.views.etl_view import (
    render_etl_view,
    render_telemetria_pa_alfa_002,
    render_auditoria_calidad_hu05,
    render_transformacion_formatos_hu06,
    render_feature_engineering_hu07
)
from src.views.ingestion_view import render_ingestion_view

__all__ = [
    "render_login_view",
    "render_auth_sidebar",
    "render_dashboard_view",
    "render_consultas_view",
    "render_analytics_view",
    "render_predictive_view",
    "render_data_management_view",
    "render_etl_view",
    "render_ingestion_view",
    "render_telemetria_pa_alfa_001",
    "render_welcome_header",
    "render_rbac_modules_preview",
    "render_telemetria_pa_alfa_002",
    "render_auditoria_calidad_hu05",
    "render_transformacion_formatos_hu06",
    "render_feature_engineering_hu07"
]
