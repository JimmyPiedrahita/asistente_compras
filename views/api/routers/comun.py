"""Utilidades compartidas por los routers."""

from __future__ import annotations

from core.errors import Conflicto, ErrorAplicacion, NoEncontrado, NoPermitido, SolicitudInvalida
from core.results import Resultado
from models.permisos import PERMISOS


def verificar_resultado(
    resultado: Resultado,
    *,
    permiso: str,
    controlador: object | None = None,
    no_encontrado: str = "Recurso no encontrado",
    duplicado: str = "El recurso ya existe",
    invalido: str = "Datos inválidos",
    conflicto: str = "Conflicto con el estado actual",
) -> None:
    """Convierte un ``Resultado`` de controlador en el error HTTP adecuado."""
    if resultado == Resultado.OK:
        return
    if resultado == Resultado.DENEGADO:
        rol = None
        motivo = None
        if controlador is not None:
            rol = controlador.obtener_rol()  # type: ignore[attr-defined]
            contexto = getattr(controlador, "contexto", None)
            motivo = getattr(contexto, "ultimo_denegado", None)
        raise NoPermitido(motivo or PERMISOS.get(permiso, permiso), rol=rol)
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
