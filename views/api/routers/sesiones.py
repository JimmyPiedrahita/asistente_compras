"""Endpoints de sesiones."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from controllers.sesiones import RegistroSesiones, Sesion
from core.errors import CredencialesInvalidas, SolicitudInvalida

from ..dependencies import obtener_registro, obtener_sesion
from ..schemas import ClaveAdministrador, EstadoSesion, SesionCreada, UsuarioSesion
from ..serializers import estado_sesion_json

router = APIRouter(tags=["Sesiones"])


@router.post(
    "/sessions/user",
    status_code=status.HTTP_201_CREATED,
    response_model=SesionCreada,
)
def iniciar_usuario(datos: UsuarioSesion, registro: RegistroSesiones = Depends(obtener_registro)):
    nueva = registro.crear()
    controlador = nueva.controlador
    if not controlador.registrar_usuario(datos.nombre) or not controlador.iniciar_sesion(
        datos.nombre
    ):
        registro.eliminar(nueva.token)
        raise SolicitudInvalida("No se pudo iniciar la sesión de usuario")
    return {
        "session_id": nueva.token,
        "usuario": datos.nombre,
        "rol": "CLIENTE",
    }


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
    return {
        "session_id": nueva.token,
        "usuario": "ADMIN",
        "rol": "ADMIN",
    }


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
