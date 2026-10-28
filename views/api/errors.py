"""Traducción de errores de aplicación a respuestas HTTP."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.errors import ErrorAplicacion
from core.logging import obtener_logger

logger = obtener_logger("asistente_compras.api")


def _cuerpo(error: ErrorAplicacion) -> dict[str, object]:
    cuerpo: dict[str, object] = {"error": error.mensaje, "codigo": error.codigo}
    if error.detalles is not None:
        cuerpo["detalles"] = error.detalles
    return cuerpo


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorAplicacion)
    async def manejar_error_aplicacion(request: Request, error: ErrorAplicacion) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content=_cuerpo(error))

    @app.exception_handler(RequestValidationError)
    async def manejar_error_validacion(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Solicitud inválida",
                "codigo": "validacion",
                "detalles": jsonable_encoder(error.errors()),
            },
        )

    @app.exception_handler(Exception)
    async def manejar_error_no_controlado(request: Request, error: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Error no controlado (request_id=%s): %s", request_id, error)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Error interno del servidor",
                "codigo": "error_interno",
            },
        )


__all__ = ["registrar_manejadores"]
