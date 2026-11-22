"""Utilidades transversales: configuración y errores."""

from .config import Settings
from .errors import (
    Conflicto,
    CredencialesInvalidas,
    ErrorAplicacion,
    NoEncontrado,
    NoPermitido,
    ServicioNoDisponible,
    SesionInvalida,
    SolicitudInvalida,
)

__all__ = [
    "Conflicto",
    "CredencialesInvalidas",
    "ErrorAplicacion",
    "NoEncontrado",
    "NoPermitido",
    "ServicioNoDisponible",
    "SesionInvalida",
    "Settings",
    "SolicitudInvalida",
]
