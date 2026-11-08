"""
Script de Inicialización de Colecciones e Índices
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
import hashlib
from src.database.connection import MongoConnectionSingleton

def inicializar_base_datos():
    print(">>> Conectando con MongoDB...")
    db = MongoConnectionSingleton.get_database()
    
    # 1. Colección USUARIOS (Control de acceso RBAC para HU-01)
    usuarios = db["usuarios"]
    usuarios.create_index("email", unique=True)
    print(">>> Índice único en 'email' verificado en colección 'usuarios'.")
    
    # Usuarios semilla del sistema con contraseñas encriptadas en SHA-256
    usuarios_semilla = [
        {
            "username": "admin_samuel",
            "email": "admin@secopanalytics.gov.co",
            "password_hash": hashlib.sha256("Admin2026*".encode()).hexdigest(),
            "rol": "Admin",
            "nombre": "Samuel Escobar (Admin)",
            "activo": True
        },
        {
            "username": "analista_juandavid",
            "email": "analista@secopanalytics.gov.co",
            "password_hash": hashlib.sha256("Secop2026*".encode()).hexdigest(),
            "rol": "Analista_BI",
            "nombre": "Juan David Cuellar (Analista)",
            "activo": True
        },
        {
            "username": "auditor_joseph",
            "email": "auditor@secopanalytics.gov.co",
            "password_hash": hashlib.sha256("Auditor2026*".encode()).hexdigest(),
            "rol": "Auditor_Veedor",
            "nombre": "Joseph Herrera (Auditor)",
            "activo": True
        }
    ]
    
    for u in usuarios_semilla:
        usuarios.update_one(
            {"email": u["email"]},
            {"$set": u},
            upsert=True
        )
    
    print(f">>> {len(usuarios_semilla)} usuarios sembrados correctamente en MongoDB.")
    
    # 2. Colección FACT_CONTRATOS
    if "contratos" not in db.list_collection_names():
        db.create_collection("contratos")
        print(">>> Colección 'contratos' creada exitosamente.")
    else:
        print(">>> Colección 'contratos' ya existe.")

if __name__ == "__main__":
    inicializar_base_datos()