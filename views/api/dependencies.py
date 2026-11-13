"""Dependencias FastAPI de sesión, roles y repositorio."""

from __future__ import annotations

from fastapi import Depends, Header, Request

from controllers.administracion import ControladorAdministracion
from controllers.autenticacion import ControladorAutenticacion
from controllers.carrito import ControladorCarrito
from controllers.catalogo import ControladorCatalogo
from controllers.compras import ControladorCompras
from controllers.sesiones import RegistroSesiones, Sesion
from core.errors import NoPermitido, SesionInvalida
from infrastructure.mongodb.repositorio import RepositorioMongo
from models.permisos import ADMINISTRADOR_ALMACEN, ADMINISTRADOR_APP, CLIENTE


def obtener_repositorio(request: Request) -> RepositorioMongo:
    return request.app.state.repositorio


def obtener_registro(request: Request) -> RegistroSesiones:
    return request.app.state.sesiones


def obtener_sesion(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Sesion:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise SesionInvalida()
    token = authorization[7:].strip()
    if not token:
        raise SesionInvalida()
    sesion = obtener_registro(request).obtener(token)
    if sesion is None:
        raise SesionInvalida()
    return sesion


def obtener_autenticacion(
    repo: RepositorioMongo = Depends(obtener_repositorio),
    registro: RegistroSesiones = Depends(obtener_registro),
) -> ControladorAutenticacion:
    return ControladorAutenticacion(repo, registro)


def obtener_catalogo(
    repo: RepositorioMongo = Depends(obtener_repositorio),
) -> ControladorCatalogo:
    return ControladorCatalogo(repo)


def obtener_carrito(
    repo: RepositorioMongo = Depends(obtener_repositorio),
) -> ControladorCarrito:
    return ControladorCarrito(repo)


def obtener_compras(
    repo: RepositorioMongo = Depends(obtener_repositorio),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> ControladorCompras:
    return ControladorCompras(repo, carrito)


def obtener_administracion(
    request: Request,
    repo: RepositorioMongo = Depends(obtener_repositorio),
) -> ControladorAdministracion:
    return ControladorAdministracion(repo, max_csv_bytes=request.app.state.settings.max_csv_bytes)


def _exigir_rol(sesion: Sesion, rol: str) -> Sesion:
    if sesion.rol != rol:
        raise NoPermitido("esta función no corresponde a tu rol", rol=sesion.rol)
    return sesion


def requerir_cliente(sesion: Sesion = Depends(obtener_sesion)) -> Sesion:
    return _exigir_rol(sesion, CLIENTE)


def requerir_admin_almacen(sesion: Sesion = Depends(obtener_sesion)) -> Sesion:
    return _exigir_rol(sesion, ADMINISTRADOR_ALMACEN)


def requerir_admin_app(sesion: Sesion = Depends(obtener_sesion)) -> Sesion:
    return _exigir_rol(sesion, ADMINISTRADOR_APP)


__all__ = [
    "obtener_administracion",
    "obtener_autenticacion",
    "obtener_carrito",
    "obtener_catalogo",
    "obtener_compras",
    "obtener_registro",
    "obtener_repositorio",
    "obtener_sesion",
    "requerir_admin_almacen",
    "requerir_admin_app",
    "requerir_cliente",
]
