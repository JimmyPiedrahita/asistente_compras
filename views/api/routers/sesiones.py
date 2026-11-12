"""Endpoints de sesiones de cliente, administrador y proveedor."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from controllers.sesiones import RegistroSesiones, Sesion
from core.errors import CredencialesInvalidas, SolicitudInvalida

from ..dependencies import obtener_registro, obtener_sesion
from ..schemas import (
    ClaveAdministrador,
    EstadoSesion,
    ProveedorSesion,
    SesionCreada,
    UsuarioSesion,
)
from ..serializers import estado_sesion_json

router = APIRouter(tags=["Sesiones"])


def _sesion_creada(nueva: Sesion) -> dict[str, object]:
    controlador = nueva.controlador
    return {
        "session_id": nueva.token,
        "usuario": controlador.obtener_usuario_actual() or "",
        "rol": controlador.obtener_rol(),
        "permisos": list(controlador.obtener_permisos()),
        "almacen_id": controlador.obtener_almacen_id(),
        "usuario_id": controlador.obtener_usuario_id(),
    }


@router.post(
    "/sessions/user",
    status_code=status.HTTP_201_CREATED,
    response_model=SesionCreada,
)
def iniciar_usuario(datos: UsuarioSesion, registro: RegistroSesiones = Depends(obtener_registro)):
    nueva = registro.crear()
    if not nueva.controlador.iniciar_sesion(datos.nombre):
        registro.eliminar(nueva.token)
        raise SolicitudInvalida(
            "No se pudo iniciar la sesión de cliente: el nombre pertenece a otro rol "
            "o el usuario está inactivo"
        )
    return _sesion_creada(nueva)


@router.post(
    "/sessions/provider",
    status_code=status.HTTP_201_CREATED,
    response_model=SesionCreada,
)
def iniciar_proveedor(
    datos: ProveedorSesion,
    registro: RegistroSesiones = Depends(obtener_registro),
):
    nueva = registro.crear()
    if not nueva.controlador.iniciar_sesion_proveedor(datos.nombre):
        registro.eliminar(nueva.token)
        raise CredencialesInvalidas(
            "Proveedor no registrado, inactivo o sin almacén asignado. "
            "Pide a un administrador que cree el proveedor."
        )
    return _sesion_creada(nueva)


@router.post(
    "/sessions/admin",
    status_code=status.HTTP_201_CREATED,
    response_model=SesionCreada,
)
def iniciar_admin(
    datos: ClaveAdministrador, registro: RegistroSesiones = Depends(obtener_registro)
):
    nueva = registro.crear()
    if not nueva.controlador.login_admin(datos.clave):
        registro.eliminar(nueva.token)
        raise CredencialesInvalidas("Clave de administrador inválida")
    return _sesion_creada(nueva)


@router.get("/sessions/{token}", response_model=EstadoSesion)
def estado_sesion(sesion: Sesion = Depends(obtener_sesion)):
    return estado_sesion_json(sesion.controlador)


@router.delete(
    "/sessions/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cerrar_sesion(
    sesion: Sesion = Depends(obtener_sesion),
    registro: RegistroSesiones = Depends(obtener_registro),
) -> None:
    registro.eliminar(sesion.token)


__all__ = ["router"]
