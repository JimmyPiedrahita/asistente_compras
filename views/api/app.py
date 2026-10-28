"""Fábrica de la aplicación FastAPI (capa Vista)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from controllers.sesiones import RegistroSesiones
from core.config import Settings
from core.logging import configurar_logging, obtener_logger
from infrastructure.mongodb import MongoInventarioRepository
from models.almacenes import GestorAlmacenes

from .errors import registrar_manejadores
from .routers import ROUTERS

logger = obtener_logger("asistente_compras.api")

RepositoryFactory = Callable[[Settings], object]


def _crear_repositorio(settings: Settings, repository_factory: RepositoryFactory | None):
    if repository_factory is not None:
        return repository_factory(settings)
    return MongoInventarioRepository(
        settings.mongodb_uri,
        settings.almacenes,
        timeout_ms=settings.mongodb_timeout_ms,
    )


def create_app(
    settings: Settings | str | None = None,
    repository_factory: RepositoryFactory | None = None,
    *,
    mongo_uri: str | None = None,
) -> FastAPI:
    """Crea la API. MongoDB es obligatorio en ejecución real.

    ``create_app("mongodb://...")`` se mantiene por compatibilidad con la
    versión anterior; lo recomendable es pasar un ``Settings``.
    """
    if isinstance(settings, str):
        mongo_uri = settings
        settings = None
    if settings is None:
        settings = Settings.from_env(mongo_uri=mongo_uri)

    configurar_logging(settings.log_level)
    repositorio = _crear_repositorio(settings, repository_factory)
    gestor = GestorAlmacenes(repositorio, settings.almacenes)
    gestor.cargar_inventarios()
    sesiones = RegistroSesiones(
        gestor,
        admin_clave=settings.admin_clave,
        ttl_seconds=settings.session_ttl_seconds,
        max_sesiones=settings.max_sessions,
        max_csv_bytes=settings.max_csv_bytes,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "API iniciada con %s almacenes y MongoDB en %s",
            len(settings.almacenes),
            settings.mongodb_db_prefix,
        )
        try:
            yield
        finally:
            try:
                repositorio.close()  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover - cierre defensivo
                logger.exception("No se pudo cerrar la conexión con MongoDB")

    app = FastAPI(
        title="Asistente de Compras API",
        version="3.0.0",
        description=(
            "API REST MVC del asistente de compras multi-almacén. "
            "Cada almacén usa una base de datos MongoDB independiente."
        ),
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Salud", "description": "Disponibilidad de la API y MongoDB."},
            {"name": "Almacenes", "description": "Almacenes e inventarios."},
            {"name": "Sesiones", "description": "Sesiones de cliente y administrador."},
            {"name": "Lista de compras", "description": "Lista personal del cliente."},
            {"name": "Búsqueda", "description": "Comparación entre almacenes."},
            {"name": "Carrito", "description": "Carrito y descuentos."},
            {"name": "Administración", "description": "Alta, precios y CSV."},
            {"name": "Exportación", "description": "Descarga de listas y carrito en CSV."},
        ],
    )
    app.state.repositorio = repositorio
    app.state.gestor = gestor
    app.state.sesiones = sesiones

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
        app.include_router(router, prefix="/api", include_in_schema=False)

    @app.get("/", include_in_schema=False)
    def raiz() -> dict[str, str]:
        return {
            "name": "Asistente de Compras API",
            "version": app.version,
            "docs": "/docs",
            "api": "/api/v1",
        }

    return app


__all__ = ["create_app"]
