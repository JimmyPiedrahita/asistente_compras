"""Utilidades transversales: configuración, errores, logging y Observer."""

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
from .observer import ObservadorNulo, SujetoObservable
from .results import Resultado

__all__ = [
    "Conflicto",
    "CredencialesInvalidas",
    "ErrorAplicacion",
    "NoEncontrado",
    "NoPermitido",
    "ObservadorNulo",
    "Resultado",
    "ServicioNoDisponible",
    "SesionInvalida",
    "Settings",
    "SolicitudInvalida",
    "SujetoObservable",
]
