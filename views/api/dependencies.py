"""Dependencias FastAPI de sesión, roles y repositorios por rol."""

from __future__ import annotations

from fastapi import Depends, Header, Request

from controllers.administracion import ControladorAdminAlmacen, ControladorAdminApp
from controllers.autenticacion import ControladorAutenticacion
from controllers.carrito import ControladorCarrito
from controllers.catalogo import ControladorCatalogo
from controllers.compras import ControladorComprasAlmacen, ControladorComprasCliente
from controllers.sesiones import RegistroSesiones, Sesion
from core.errors import NoPermitido, SesionInvalida
from infrastructure.imagenes import ServicioImagenesProducto
from infrastructure.mongodb.contexto import ContextoAplicacion
from models.permisos import ADMINISTRADOR_ALMACEN, ADMINISTRADOR_APP, CLIENTE


def obtener_contexto(request: Request) -> ContextoAplicacion:
    return request.app.state.contexto


def obtener_registro(request: Request) -> RegistroSesiones:
    return request.app.state.sesiones


def obtener_imagenes(request: Request) -> ServicioImagenesProducto:
    return request.app.state.imagenes


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
    contexto: ContextoAplicacion = Depends(obtener_contexto),
    registro: RegistroSesiones = Depends(obtener_registro),
) -> ControladorAutenticacion:
    return ControladorAutenticacion(contexto.repo_usuarios, registro)


def obtener_catalogo(
    contexto: ContextoAplicacion = Depends(obtener_contexto),
) -> ControladorCatalogo:
    return ControladorCatalogo(contexto.repo_catalogo)


def obtener_carrito(
    contexto: ContextoAplicacion = Depends(obtener_contexto),
) -> ControladorCarrito:
    return ControladorCarrito(contexto.repo_catalogo)


def obtener_compras_cliente(
    contexto: ContextoAplicacion = Depends(obtener_contexto),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> ControladorComprasCliente:
    return ControladorComprasCliente(contexto.repo_compras, carrito)


def obtener_admin_app(
    contexto: ContextoAplicacion = Depends(obtener_contexto),
) -> ControladorAdminApp:
    return ControladorAdminApp(
        contexto.repo_almacenes,
        contexto.repo_usuarios,
        contexto.aprovisionamiento,
    )


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


def obtener_admin_almacen(
    sesion: Sesion = Depends(requerir_admin_almacen),
    contexto: ContextoAplicacion = Depends(obtener_contexto),
    imagenes: ServicioImagenesProducto = Depends(obtener_imagenes),
) -> ControladorAdminAlmacen:
    repositorio = contexto.directorio.repositorio(sesion.almacen_id or "")
    return ControladorAdminAlmacen(
        repositorio,
        contexto.validador,
        max_csv_bytes=contexto.settings.max_csv_bytes,
        imagenes=imagenes,
    )


def obtener_compras_almacen(
    sesion: Sesion = Depends(requerir_admin_almacen),
    contexto: ContextoAplicacion = Depends(obtener_contexto),
) -> ControladorComprasAlmacen:
    repositorio = contexto.directorio.repositorio(sesion.almacen_id or "")
    return ControladorComprasAlmacen(repositorio)


__all__ = [
    "obtener_admin_almacen",
    "obtener_admin_app",
    "obtener_autenticacion",
    "obtener_carrito",
    "obtener_catalogo",
    "obtener_compras_almacen",
    "obtener_compras_cliente",
    "obtener_contexto",
    "obtener_imagenes",
    "obtener_registro",
    "obtener_sesion",
    "requerir_admin_almacen",
    "requerir_admin_app",
    "requerir_cliente",
]
