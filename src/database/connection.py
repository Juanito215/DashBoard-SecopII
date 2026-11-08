"""
Gestor de Conexión a MongoDB aplicando el Patrón Singleton
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os

class MongoConnectionSingleton:
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoConnectionSingleton, cls).__new__(cls)
            uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
            db_name = os.getenv("MONGO_DB_NAME", "secop_analytics")
            
            try:
                # Conexión con timeout de 3 segundos para detectar fallos rápido
                cls._client = MongoClient(uri, serverSelectionTimeoutMS=3000)
                # Comando ping para verificar conexión física activa
                cls._client.admin.command('ping')
                cls._db = cls._client[db_name]
                print(f" Conexión establecida exitosamente a MongoDB: {db_name}")
            except ConnectionFailure as e:
                print(f" Error de conexión a MongoDB: {e}")
                cls._client = None
                cls._db = None
                raise e
        return cls._instance

    @classmethod
    def get_database(cls):
        """Retorna la instancia activa de la base de datos."""
        if cls._instance is None or cls._db is None:
            cls()
        return cls._db

    @classmethod
    def get_collection(cls, collection_name: str):
        """Retorna una colección específica de la base de datos."""
        db = cls.get_database()
        return db[collection_name]