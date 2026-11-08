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


def test_cierre_sesion_controlador():
    """
    HU-03: Valida que el método cerrar_sesion de AuthController ejecute
    el procedimiento de terminación de sesión y retorne True.
    """
    resultado = AuthController.cerrar_sesion(email="admin@secopanalytics.gov.co")
    assert resultado is True, "El cierre de sesión en AuthController debe retornar True"

    # Cierre anónimo o sin correo también debe ser seguro
    resultado_anonimo = AuthController.cerrar_sesion()
    assert resultado_anonimo is True


def test_cierre_sesion_flujo_completo_app():
    """
    HU-03: Valida mediante Streamlit AppTest el ciclo completo de cierre de sesión:
    1. Login exitoso
    2. Existencia de sesión y datos en memoria
    3. Clic en botón 'Cerrar Sesión (HU-03)'
    4. Limpieza total de sesión (session_state) y retorno inmediato al login
    """
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    # 1. Cargar aplicación en login (resolviendo ruta absoluta a app.py en la raíz)
    ruta_app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(ruta_app).run()
    assert at.session_state.get("autenticado") is False
    assert len(at.text_input) == 2

    # 2. Iniciar sesión como Analista
    at.text_input[0].input("analista@secopanalytics.gov.co")
    at.text_input[1].input("Secop2026*")
    at.button[0].click().run()

    # Verificar sesión activa
    assert at.session_state.get("autenticado") is True
    assert at.session_state.get("usuario_datos") is not None
    assert at.session_state.get("usuario_datos")["rol"] == "Analista_BI"

    # 3. Localizar botón de cierre de sesión (HU-03)
    btn_logout = [b for b in at.button if "Cerrar Sesión" in b.label][0]
    btn_logout.click().run()

    # 4. Validar limpieza integral y bloqueo de navegación
    assert at.session_state.get("autenticado") is False
    assert at.session_state.get("usuario_datos") is None
    # Comprobar que reaparece el formulario de login y no hay excepciones
    assert len(at.exception) == 0
    assert len(at.text_input) == 2

