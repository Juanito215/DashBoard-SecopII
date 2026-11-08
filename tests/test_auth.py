"""
Suite de Pruebas Automatizadas de Autenticación y Control de Acceso RBAC
Caso de Prueba de Aceptación: PA-ALFA-001 (Autenticación y Control de Acceso por Roles)
Historias de Usuario: HU-01, HU-02, HU-03
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
import pytest
from src.controllers.auth_controller import AuthController


def test_login_exitoso_admin():
    """
    PA-ALFA-001: Valida autenticación exitosa del rol 'Admin'
    Verifica credenciales, asignación de permisos RBAC y datos del usuario.
    """
    exito, usuario, latencia_ms = AuthController.autenticar(
        "admin@secopanalytics.gov.co",
        "Admin2026*"
    )
    assert exito is True, "El login de admin debería ser exitoso"
    assert usuario is not None, "El diccionario de usuario no debe ser None"
    assert usuario["rol"] == "Admin", "El rol debe ser 'Admin'"
    assert usuario["email"] == "admin@secopanalytics.gov.co"
    assert usuario["activo"] is True
    assert latencia_ms > 0, "La latencia debe ser un valor positivo"
    
    permisos_esperados = [
        "etl_carga",
        "gestion_usuarios",
        "consultas_bi",
        "analitica_descriptiva",
        "modelos_ml"
    ]
    assert usuario["permisos"] == permisos_esperados, "Los permisos del Admin no coinciden con la matriz RBAC"


def test_login_exitoso_analista():
    """
    PA-ALFA-001: Valida autenticación exitosa del rol 'Analista_BI'
    Verifica credenciales y permisos específicos del perfil de análisis.
    """
    exito, usuario, latencia_ms = AuthController.autenticar(
        "analista@secopanalytics.gov.co",
        "Secop2026*"
    )
    assert exito is True, "El login de analista debería ser exitoso"
    assert usuario is not None
    assert usuario["rol"] == "Analista_BI"
    assert usuario["email"] == "analista@secopanalytics.gov.co"
    assert latencia_ms > 0

    permisos_esperados = [
        "consultas_bi",
        "analitica_descriptiva",
        "simulacion_ml",
        "exportar_csv"
    ]
    assert usuario["permisos"] == permisos_esperados, "Los permisos del Analista_BI no coinciden"


def test_login_exitoso_auditor():
    """
    PA-ALFA-001: Valida autenticación exitosa del rol 'Auditor_Veedor'
    Verifica credenciales y permisos de solo lectura para veeduría ciudadana.
    """
    exito, usuario, latencia_ms = AuthController.autenticar(
        "auditor@secopanalytics.gov.co",
        "Auditor2026*"
    )
    assert exito is True, "El login de auditor debería ser exitoso"
    assert usuario is not None
    assert usuario["rol"] == "Auditor_Veedor"
    assert usuario["email"] == "auditor@secopanalytics.gov.co"
    assert latencia_ms > 0

    permisos_esperados = [
        "consultas_bi",
        "analitica_descriptiva_lectura"
    ]
    assert usuario["permisos"] == permisos_esperados, "Los permisos de Auditor_Veedor no coinciden"


def test_login_password_incorrecto():
    """
    PA-ALFA-001: Rechaza intento de autenticación con contraseña incorrecta.
    Debe retornar (False, None, latencia_ms).
    """
    exito, usuario, latencia_ms = AuthController.autenticar(
        "admin@secopanalytics.gov.co",
        "ClaveTotalmenteErronea2026*"
    )
    assert exito is False, "Debe rechazar una contraseña incorrecta"
    assert usuario is None, "El usuario debe ser None ante fallo de autenticación"
    assert isinstance(latencia_ms, float)
    assert latencia_ms >= 0


def test_login_usuario_inexistente():
    """
    PA-ALFA-001: Rechaza intento de inicio de sesión con correo no registrado en MongoDB.
    Debe retornar (False, None, latencia_ms).
    """
    exito, usuario, latencia_ms = AuthController.autenticar(
        "correo_inexistente_999@secopanalytics.gov.co",
        "Admin2026*"
    )
    assert exito is False, "Debe rechazar usuarios inexistentes"
    assert usuario is None
    assert isinstance(latencia_ms, float)


def test_latencia_menor_a_1500ms():
    """
    PA-ALFA-001 / Regla 4: Rendimiento y Tolerancia a Fallos.
    Verifica que la consulta y validación en MongoDB se ejecute en menos de 1.5 segundos (1500 ms).
    """
    exito, usuario, latencia_ms = AuthController.autenticar(
        "admin@secopanalytics.gov.co",
        "Admin2026*"
    )
    assert exito is True
    assert latencia_ms < 1500.0, f"La latencia ({latencia_ms} ms) debe ser menor a 1500 ms según el criterio no funcional"


def test_login_normalizacion_email():
    """
    Verifica que el controlador normalice correos con espacios y mayúsculas.
    """
    exito, usuario, _ = AuthController.autenticar(
        "  ADMIN@SECOPANALYTICS.GOV.CO  ",
        "Admin2026*"
    )
    assert exito is True
    assert usuario is not None
    assert usuario["email"] == "admin@secopanalytics.gov.co"


def test_login_credenciales_vacias():
    """
    Verifica rechazo inmediato si los campos están vacíos.
    """
    exito, usuario, _ = AuthController.autenticar("", "")
    assert exito is False
    assert usuario is None
