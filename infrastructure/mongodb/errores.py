"""Traducción de errores de PyMongo a errores de aplicación."""

from __future__ import annotations

from pymongo.errors import OperationFailure, PyMongoError

from core.errors import ErrorAplicacion, NoPermitido, ServicioNoDisponible

# Códigos de autorización de MongoDB.
_CODIGOS_AUTORIZACION = {13, 18, 8000}


def traducir_error(error: PyMongoError, mensaje: str) -> ErrorAplicacion:
    if isinstance(error, OperationFailure) and error.code in _CODIGOS_AUTORIZACION:
        return NoPermitido("la credencial de MongoDB no permite esta operación")
    return ServicioNoDisponible(mensaje)


def es_error_autorizacion(error: BaseException) -> bool:
    return isinstance(error, OperationFailure) and error.code in _CODIGOS_AUTORIZACION


__all__ = ["es_error_autorizacion", "traducir_error"]
