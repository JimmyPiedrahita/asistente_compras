import secrets
from dataclasses import dataclass

from controlador.controlador import ControladorCompras
from modelo.listas import CarritoCompras


class VistaApi:
    """Observador sin efectos de presentación para el controlador HTTP."""

    def actualizar(self, sujeto, mensaje: str):
        return None

    def notificar_denegado(self, permiso: str):
        return None


@dataclass
class Sesion:
    token: str
    controlador: ControladorCompras


class RegistroSesiones:
    def __init__(self, gestor_almacenes):
        self._gestor_almacenes = gestor_almacenes
        self._sesiones: dict[str, Sesion] = {}

    def crear(self) -> Sesion:
        token = secrets.token_urlsafe(32)
        controlador = ControladorCompras(
            CarritoCompras(), VistaApi(), gestor_almacenes=self._gestor_almacenes
        )
        sesion = Sesion(token, controlador)
        self._sesiones[token] = sesion
        return sesion

    def obtener(self, token: str) -> Sesion | None:
        return self._sesiones.get(token)

    def eliminar(self, token: str) -> None:
        self._sesiones.pop(token, None)
