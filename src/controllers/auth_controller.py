"""
Controlador de Autenticación y Control de Acceso Basado en Roles (RBAC)
Historia de Usuario: HU-01 (Autenticación con MongoDB y RBAC)
Caso de Prueba de Aceptación: PA-ALFA-001
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import hashlib
import time
from datetime import datetime
from typing import Any
from src.database.connection import MongoConnectionSingleton


class AuthController:
    """
    Controlador encargado de la lógica de autenticación, validación de credenciales
    contra MongoDB y asignación de permisos según el modelo de roles RBAC.
    """

    # Mapeo de permisos autorizados por rol según la especificación de SECOP-Analytics
    ROLES_PERMISOS: dict[str, list[str]] = {
        "Admin": [
            "etl_carga",
            "gestion_usuarios",
            "consultas_bi",
            "analitica_descriptiva",
            "modelos_ml"
        ],
        "Analista_BI": [
            "consultas_bi",
            "analitica_descriptiva",
            "simulacion_ml",
            "exportar_csv"
        ],
        "Auditor_Veedor": [
            "consultas_bi",
            "analitica_descriptiva_lectura"
        ]
    }

    @classmethod
    def autenticar(cls, email: str, password_plana: str) -> tuple[bool, dict[str, Any] | None, float]:
        """
        Autentica un usuario contra la colección 'usuarios' de MongoDB.

        Args:
            email (str): Correo institucional del usuario.
            password_plana (str): Contraseña en texto plano ingresada en la vista.

        Returns:
            tuple[bool, dict | None, float]:
                - bool: True si la autenticación fue exitosa, False en caso contrario.
                - dict | None: Diccionario con los datos del usuario y sus permisos RBAC,
                  o None si falló la autenticación.
                - float: Tiempo de respuesta (latencia) de la consulta en milisegundos (ms).
        """
        if not email or not password_plana:
            return False, None, 0.0

        inicio = time.perf_counter()

        try:
            # 1. Normalización del correo y cálculo del hash SHA-256
            email_limpio = email.strip().lower()
            password_hash = hashlib.sha256(password_plana.encode("utf-8")).hexdigest()

            # 2. Consulta en la colección 'usuarios' mediante el conector Singleton
            usuarios_col = MongoConnectionSingleton.get_collection("usuarios")
            usuario = usuarios_col.find_one({"email": email_limpio, "activo": True})

            # 3. Validación de hash de contraseña
            if usuario and usuario.get("password_hash") == password_hash:
                # 4. Actualización del campo 'ultimo_acceso' con la fecha/hora actual (UTC)
                fecha_acceso = datetime.utcnow()
                try:
                    usuarios_col.update_one(
                        {"_id": usuario["_id"]},
                        {"$set": {"ultimo_acceso": fecha_acceso}}
                    )
                except Exception as err_update:
                    print(f"Advertencia al actualizar 'ultimo_acceso': {err_update}")

                # Medición de latencia de la consulta
                latencia_ms = round((time.perf_counter() - inicio) * 1000.0, 2)

                # 5. Construcción del diccionario de sesión del usuario
                usuario_dict = dict(usuario)
                if "_id" in usuario_dict:
                    usuario_dict["_id"] = str(usuario_dict["_id"])

                rol = usuario_dict.get("rol", "")
                usuario_dict["permisos"] = cls.ROLES_PERMISOS.get(rol, [])
                usuario_dict["ultimo_acceso"] = fecha_acceso

                return True, usuario_dict, latencia_ms

            # Credenciales incorrectas o usuario inactivo
            latencia_ms = round((time.perf_counter() - inicio) * 1000.0, 2)
            return False, None, latencia_ms

        except Exception as e:
            latencia_ms = round((time.perf_counter() - inicio) * 1000.0, 2) if 'inicio' in locals() else 0.0
            print(f"Error en AuthController.autenticar: {e}")
            return False, None, latencia_ms

    @classmethod
    def obtener_permisos(cls, rol: str) -> list[str]:
        """Retorna la lista de permisos asignados a un rol específico."""
        return cls.ROLES_PERMISOS.get(rol, [])
