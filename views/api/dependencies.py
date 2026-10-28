"""Dependencias FastAPI para sesiones y recursos compartidos."""

from __future__ import annotations

from fastapi import Depends, Header, Path, Request

from controllers.compras import ControladorCompras
from controllers.sesiones import RegistroSesiones, Sesion
from core.errors import SesionInvalida
from models.almacenes import GestorAlmacenes


def obtener_registro(request: Request) -> RegistroSesiones:
    return request.app.state.sesiones


def obtener_repositorio(request: Request):
    return request.app.state.repositorio


def obtener_gestor(request: Request) -> GestorAlmacenes:
    return request.app.state.gestor


def obtener_sesion(
    request: Request,
    token: str = Path(..., description="Token de sesión"),
    authorization: str | None = Header(default=None),
) -> Sesion:
    token_efectivo = token
    if authorization and authorization.lower().startswith("bearer "):
        token_efectivo = authorization[7:].strip() or token
    sesion = obtener_registro(request).obtener(token_efectivo)
    if sesion is None:
        raise SesionInvalida()
    return sesion


def obtener_controlador(
    sesion: Sesion = Depends(obtener_sesion),
) -> ControladorCompras:
    return sesion.controlador


__all__ = [
    "obtener_controlador",
    "obtener_gestor",
    "obtener_registro",
    "obtener_repositorio",
    "obtener_sesion",
]
