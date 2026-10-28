"""Errores de dominio y de aplicación.

Los controladores lanzan estos errores y la capa HTTP los traduce a códigos
HTTP. Así la lógica de negocio no depende de FastAPI.
"""

from __future__ import annotations

from typing import Any


class ErrorAplicacion(Exception):
    """Error controlado que la API puede serializar."""

    status_code = 500
    codigo = "error_interno"

    def __init__(
        self,
        mensaje: str,
        *,
        detalles: Any = None,
        codigo: str | None = None,
    ) -> None:
        self.mensaje = mensaje
        self.detalles = detalles
        if codigo is not None:
            self.codigo = codigo
        super().__init__(mensaje)


class SolicitudInvalida(ErrorAplicacion):
    status_code = 400
    codigo = "solicitud_invalida"


class SesionInvalida(ErrorAplicacion):
    status_code = 401
    codigo = "sesion_invalida"

    def __init__(self) -> None:
        super().__init__("Sesión inválida o expirada")


class CredencialesInvalidas(ErrorAplicacion):
    status_code = 401
    codigo = "credenciales_invalidas"

    def __init__(self, mensaje: str = "Credenciales inválidas") -> None:
        super().__init__(mensaje)


class NoPermitido(ErrorAplicacion):
    status_code = 403
    codigo = "operacion_no_permitida"

    def __init__(self, operacion: str) -> None:
        super().__init__(f"Operación no permitida: {operacion}")


class NoEncontrado(ErrorAplicacion):
    status_code = 404
    codigo = "no_encontrado"


class Conflicto(ErrorAplicacion):
    status_code = 409
    codigo = "conflicto"


class ServicioNoDisponible(ErrorAplicacion):
    status_code = 503
    codigo = "servicio_no_disponible"


class ConfiguracionInvalida(RuntimeError):
    """Falla de arranque por variables de entorno incompletas o inválidas."""
