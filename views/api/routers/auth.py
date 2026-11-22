"""Registro, inicio y cierre de sesión."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from controllers.autenticacion import ControladorAutenticacion
from controllers.sesiones import Sesion

from ..dependencies import obtener_autenticacion, obtener_sesion
from ..schemas import LoginSolicitud, RegistroClienteSolicitud, SesionRespuesta

router = APIRouter(tags=["Autenticación"])


@router.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED,
    response_model=SesionRespuesta,
)
def registrar(
    datos: RegistroClienteSolicitud,
    auth: ControladorAutenticacion = Depends(obtener_autenticacion),
) -> dict[str, object]:
    sesion = auth.registrar_cliente(datos.model_dump())
    return sesion.publica()


@router.post("/auth/login", response_model=SesionRespuesta)
def iniciar_sesion(
    datos: LoginSolicitud,
    auth: ControladorAutenticacion = Depends(obtener_autenticacion),
) -> dict[str, object]:
    sesion = auth.iniciar_sesion(datos.email, datos.password)
    return sesion.publica()


@router.get("/auth/me", response_model=SesionRespuesta)
def estado_sesion(sesion: Sesion = Depends(obtener_sesion)) -> dict[str, object]:
    return sesion.publica()


@router.delete("/auth/session", status_code=status.HTTP_204_NO_CONTENT)
def cerrar_sesion(
    sesion: Sesion = Depends(obtener_sesion),
    auth: ControladorAutenticacion = Depends(obtener_autenticacion),
) -> None:
    auth.cerrar_sesion(sesion.token)


__all__ = ["router"]
