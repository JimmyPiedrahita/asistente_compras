"""Caché de clientes MongoDB por URI y cierre ordenado."""

from __future__ import annotations

import contextlib
import threading

from pymongo.database import Database

from .cliente import ClienteMongo


class ConexionesMongo:
    """Reutiliza un ``MongoClient`` por URI.

    Un cliente por almacén es aceptable para decenas de almacenes; la creación
    es perezosa para no abrir conexiones a bases que aún no se usan.
    """

    def __init__(self, timeout_ms: int = 5000) -> None:
        self._timeout_ms = int(timeout_ms)
        self._clientes: dict[str, ClienteMongo] = {}
        self._candado = threading.RLock()

    def cliente(self, uri: str) -> ClienteMongo:
        with self._candado:
            cliente = self._clientes.get(uri)
            if cliente is None:
                cliente = ClienteMongo(uri, self._timeout_ms)
                self._clientes[uri] = cliente
            return cliente

    def base(self, uri: str, nombre: str) -> Database:
        return self.cliente(uri).base(nombre)

    def ping(self, uri: str) -> None:
        self.cliente(uri).ping()

    def cerrar(self) -> None:
        with self._candado:
            for cliente in self._clientes.values():
                with contextlib.suppress(Exception):
                    cliente.close()
            self._clientes.clear()

    def __len__(self) -> int:
        with self._candado:
            return len(self._clientes)


__all__ = ["ConexionesMongo"]
