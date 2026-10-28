import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.almacenes import Almacen, GestorAlmacenes
from models.persistencia_mongodb import MongoInventarioRepository

from .errores import ApiError
from .rutas import crear_router
from .sesiones import RegistroSesiones


def create_app(
    mongo_uri: str | None = None,
    repository_factory=MongoInventarioRepository,
) -> FastAPI:
    """Crea la API. MongoDB es obligatorio para la ejecución real."""
    uri = mongo_uri or os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI es obligatorio para iniciar la API")
    persistencia = repository_factory(uri)
    gestor = GestorAlmacenes(persistencia)
    for id_almacen in range(1, 4):
        gestor.agregar_almacen(
            Almacen(id_almacen=id_almacen, nombre=f"Almacen {id_almacen}")
        )
    sesiones = RegistroSesiones(gestor)

    app = FastAPI(
        title="Asistente de Compras API",
        version="2.0.0",
        description="API REST del asistente de compras multi-almacén.",
    )
    origenes = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origen.strip() for origen in origenes if origen.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def manejar_error(request: Request, error: ApiError):
        return JSONResponse(
            status_code=error.status_code,
            content={"error": error.detail},
        )

    router = crear_router(sesiones, persistencia)
    app.include_router(router, prefix="/api", include_in_schema=False)
    app.include_router(router, prefix="/api/v1", include_in_schema=True)
    return app
