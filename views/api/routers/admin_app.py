"""Endpoints del administrador de la aplicación."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from controllers.administracion import ControladorAdminApp
from controllers.sesiones import Sesion

from ..dependencies import obtener_admin_app, requerir_admin_app
from ..schemas import (
    AdminAlmacenSolicitud,
    AlmacenRespuesta,
    AlmacenSolicitud,
    CredencialesSolicitud,
    UsuarioAdminRespuesta,
)

router = APIRouter(tags=["Administrador de la aplicación"])


# Almacenes -------------------------------------------------------------
@router.get("/admin-app/almacenes", response_model=list[AlmacenRespuesta])
def listar_almacenes(
    sesion: Sesion = Depends(requerir_admin_app),
    admin: ControladorAdminApp = Depends(obtener_admin_app),
) -> list[dict]:
    return admin.listar_almacenes()


@router.post(
    "/admin-app/almacenes",
    status_code=status.HTTP_201_CREATED,
    response_model=AlmacenRespuesta,
)
def crear_almacen(
    datos: AlmacenSolicitud,
    sesion: Sesion = Depends(requerir_admin_app),
    admin: ControladorAdminApp = Depends(obtener_admin_app),
) -> dict:
    return admin.crear_almacen(datos.nombre)


# Administradores de almacén -------------------------------------------
@router.get("/admin-app/administradores", response_model=list[UsuarioAdminRespuesta])
def listar_administradores(
    sesion: Sesion = Depends(requerir_admin_app),
    admin: ControladorAdminApp = Depends(obtener_admin_app),
) -> list[dict]:
    return admin.listar_admins_almacen()


@router.post(
    "/admin-app/administradores",
    status_code=status.HTTP_201_CREATED,
    response_model=UsuarioAdminRespuesta,
)
def crear_administrador(
    datos: AdminAlmacenSolicitud,
    sesion: Sesion = Depends(requerir_admin_app),
    admin: ControladorAdminApp = Depends(obtener_admin_app),
) -> dict:
    return admin.crear_admin_almacen(
        nombre=datos.nombre,
        email=datos.email,
        password=datos.password,
        almacen_id=datos.almacen_id,
    )


@router.patch(
    "/admin-app/administradores/{usuario_id}/credenciales",
    response_model=UsuarioAdminRespuesta,
)
def actualizar_credenciales(
    usuario_id: str,
    datos: CredencialesSolicitud,
    sesion: Sesion = Depends(requerir_admin_app),
    admin: ControladorAdminApp = Depends(obtener_admin_app),
) -> dict:
    return admin.actualizar_credenciales(usuario_id, email=datos.email, password=datos.password)


__all__ = ["router"]
