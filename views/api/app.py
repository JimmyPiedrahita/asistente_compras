"""Fábrica de la aplicación FastAPI y servido de la interfaz web."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from controllers.sesiones import RegistroSesiones
from core.config import Settings
from core.logging import configurar_logging, obtener_logger
from infrastructure.mongodb.contexto import ContextoAplicacion, construir_contexto

from .errors import registrar_manejadores
from .routers import ROUTERS

logger = obtener_logger("asistente_compras.api")

_RAIZ = Path(__file__).resolve().parents[2]
_DIR_FRONTEND = _RAIZ / "frontend" / "dist"


def create_app(
    settings: Settings | None = None,
    *,
    contexto: ContextoAplicacion | None = None,
) -> FastAPI:
    if settings is None:
        settings = Settings.from_env()

    configurar_logging(settings.log_level)
    contexto = contexto or construir_contexto(settings)
    sesiones = RegistroSesiones(
        ttl_seconds=settings.session_ttl_seconds,
        max_sesiones=settings.max_sessions,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "API iniciada; base global: %s (modo pruebas: %s)",
            settings.mongodb_global_db,
            settings.modo_pruebas,
        )
        try:
            yield
        finally:
            try:
                contexto.cerrar()
            except Exception:  # pragma: no cover - cierre defensivo
                logger.exception("No se pudieron cerrar las conexiones con MongoDB")

    app = FastAPI(
        title="Asistente de Compras API",
        version="5.0.0",
        description=(
            "Aplicación web de compras y comparación de productos entre almacenes. "
            "Incluye registro de clientes, búsqueda con filtros, carrito, cupones "
            "por almacén y pagos."
        ),
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Salud", "description": "Disponibilidad de la API y MongoDB."},
            {"name": "Autenticación", "description": "Registro, login y sesión."},
            {"name": "Cliente", "description": "Lista, búsqueda, carrito y compra."},
            {
                "name": "Administrador de almacén",
                "description": "Productos, CSV, cupones, compras y estadísticas.",
            },
            {
                "name": "Administrador de la aplicación",
                "description": "Almacenes y administradores de almacén.",
            },
        ],
    )
    app.state.contexto = contexto
    app.state.sesiones = sesiones
    app.state.settings = settings

    origenes = list(settings.cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes,
        allow_credentials="*" not in origenes,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def asignar_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    registrar_manejadores(app)

    for router in ROUTERS:
        app.include_router(router, prefix="/api/v1")

    _montar_frontend(app)

    return app


def _montar_frontend(app: FastAPI) -> None:
    assets = _DIR_FRONTEND / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def raiz():
        indice = _DIR_FRONTEND / "index.html"
        if indice.is_file():
            return FileResponse(indice)
        return {
            "name": "Asistente de Compras API",
            "version": app.version,
            "docs": "/docs",
            "api": "/api/v1",
        }

    @app.get("/{ruta:path}", include_in_schema=False)
    def spa(ruta: str):
        if ruta.startswith(("api/", "docs", "redoc", "openapi")):
            raise HTTPException(status_code=404, detail="No encontrado")
        indice = _DIR_FRONTEND / "index.html"
        if indice.is_file():
            return FileResponse(indice)
        raise HTTPException(status_code=404, detail="No encontrado")


__all__ = ["create_app"]
