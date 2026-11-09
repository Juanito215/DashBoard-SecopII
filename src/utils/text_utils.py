"""
Utilidades de procesamiento y normalización de texto para SECOP-Analytics.
Historia de Usuario: HU-14 (Filtrado por Nombre o NIT de la Entidad Compradora)
Caso de Prueba de Aceptación: PA-ALFA-003
SECOP-Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations
import re
import unicodedata


def normalizar_texto_busqueda(texto: str) -> str:
    """
    Elimina diacríticos (tildes, diéresis), espacios excedentes y convierte a minúsculas.
    Ejemplo: 'Alcaldía de Tuluá  ' -> 'alcaldia de tulua'

    Args:
        texto (str): Cadena de texto a normalizar.

    Returns:
        str: Cadena normalizada sin diacríticos, en minúsculas y con espacios simples.
    """
    if not texto:
        return ""
    texto_limpio = unicodedata.normalize("NFKD", str(texto).strip().lower())
    texto_sin_tildes = "".join([c for c in texto_limpio if not unicodedata.combining(c)])
    return re.sub(r"\s+", " ", texto_sin_tildes)
