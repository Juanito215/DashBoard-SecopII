"""
Módulo de Base de Datos y Persistencia NoSQL de SECOP-Analytics
Universidad del Valle - Sede Tuluá
"""
from src.database.connection import MongoConnectionSingleton
from src.database.data_repository import DataRepositorySingleton, get_data_repository

__all__ = [
    "MongoConnectionSingleton",
    "DataRepositorySingleton",
    "get_data_repository",
]
