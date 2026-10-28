"""Utilidades compartidas por los routers."""

from __future__ import annotations

from core.errors import Conflicto, ErrorAplicacion, NoEncontrado, NoPermitido, SolicitudInvalida
from core.results import Resultado


def verificar_resultado(
    resultado: Resultado,
    *,
    permiso: str,
    no_encontrado: str = "Recurso no encontrado",
    duplicado: str = "El recurso ya existe",
    invalido: str = "Datos inválidos",
    conflicto: str = "Conflicto con el estado actual",
) -> None:
    """Convierte un ``Resultado`` de controlador en el error HTTP adecuado."""
    if resultado == Resultado.OK:
        return
    if resultado == Resultado.DENEGADO:
        raise NoPermitido(permiso)
    if resultado == Resultado.VACIO:
        raise SolicitudInvalida("El valor no puede estar vacío")
    if resultado == Resultado.DUPLICADO:
        raise Conflicto(duplicado)
    if resultado == Resultado.NO_ENCONTRADO:
        raise NoEncontrado(no_encontrado)
    if resultado == Resultado.INVALIDO:
        raise SolicitudInvalida(invalido)
    if resultado == Resultado.CONFLICTO:
        raise Conflicto(conflicto)
    raise ErrorAplicacion("No se pudo completar la operación")


__all__ = ["verificar_resultado"]
