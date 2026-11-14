"""
Excepciones de Dominio para Ingesta y Gestión de Datasets
SECOP Analytics | Universidad del Valle - Sede Tuluá
"""
from __future__ import annotations


class SecopAnalyticsError(Exception):
    """Clase base para excepciones del dominio SECOP Analytics."""
    pass


class DatasetDuplicadoError(SecopAnalyticsError):
    """
    Excepción lanzada al intentar registrar un dataset que ya ha sido cargado en el repositorio activo,
    detectado mediante coincidencia de nombre de archivo o huella criptográfica SHA-256.
    """

    def __init__(self, mensaje: str | None = None, nombre_archivo: str = "", hash_sha256: str = "") -> None:
        self.nombre_archivo = nombre_archivo
        self.hash_sha256 = hash_sha256
        if not mensaje:
            mensaje = (
                f"El archivo '{nombre_archivo}' ya se encuentra registrado en el repositorio activo "
                f"(Huella SHA-256: {hash_sha256[:12]}...). Evite duplicar lotes para preservar la integridad analítica."
            )
        super().__init__(mensaje)


class FormatoInconsistenteError(SecopAnalyticsError):
    """
    Excepción lanzada cuando se intenta cargar un archivo con extensión o formato incompatible
    con los datasets previamente cargados en la sesión activa (por ejemplo, mezclar CSV y Parquet).
    """

    def __init__(self, mensaje: str | None = None, formato_esperado: str = "", formato_recibido: str = "") -> None:
        self.formato_esperado = formato_esperado
        self.formato_recibido = formato_recibido
        if not mensaje:
            mensaje = (
                f"Inconsistencia de formato detectada: el repositorio activo opera en formato '{formato_esperado.upper()}', "
                f"pero se intentó cargar un archivo en formato '{formato_recibido.upper()}'. "
                f"Todos los lotes deben compartir la misma estructura de almacenamiento."
            )
        super().__init__(mensaje)


class LimiteDatasetsExcedidoError(SecopAnalyticsError):
    """
    Excepción lanzada cuando se supera el límite máximo estricto de 10 datasets
    cargados simultáneamente en el repositorio activo.
    """

    def __init__(self, mensaje: str | None = None, total_actual: int = 10, limite_maximo: int = 10) -> None:
        self.total_actual = total_actual
        self.limite_maximo = limite_maximo
        if not mensaje:
            mensaje = (
                f"Límite máximo de {limite_maximo} datasets excedido. El repositorio ya contiene "
                f"{total_actual} archivos cargados. Limpie el repositorio antes de incorporar nuevos lotes."
            )
        super().__init__(mensaje)
