"""Conexión a MongoDB.

Se usa un único ``MongoClient`` (pool de conexiones) y una base de datos
independiente por almacén. Crear un cliente por base desperdiciaría recursos.
"""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from core.errors import ServicioNoDisponible


class ClienteMongo:
    def __init__(self, uri: str, timeout_ms: int = 5000) -> None:
        try:
            self._cliente = MongoClient(
                uri,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms,
                appname="asistente_compras",
            )
        except Exception as error:  # pragma: no cover - error de configuración
            raise ServicioNoDisponible("No se pudo crear el cliente de MongoDB") from error
        self.ping()

    def base(self, nombre: str) -> Database:
        return self._cliente[nombre]

    def ping(self) -> None:
        try:
            self._cliente.admin.command("ping")
        except PyMongoError as error:
            raise ServicioNoDisponible(
                "MongoDB no está disponible; revisa MONGODB_URI y el servicio"
            ) from error

    def close(self) -> None:
        self._cliente.close()

    @property
    def cliente(self) -> MongoClient:
        return self._cliente


__all__ = ["ClienteMongo"]
