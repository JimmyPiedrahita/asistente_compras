"""Directorio de almacenes y construcción perezosa de sus repositorios."""

from __future__ import annotations

import threading

from core.errors import NoEncontrado
from models.almacenes import Almacen

from .almacen import RepositorioAlmacen
from .conexiones import ConexionesMongo
from .global_db import RepositorioAlmacenes
from .uri import FabricaURIs


class DirectorioAlmacenes:
    """Resuelve la base y la credencial de un almacén a partir de su metadata."""

    def __init__(
        self,
        repositorio: RepositorioAlmacenes,
        fabrica: FabricaURIs,
        conexiones: ConexionesMongo,
    ) -> None:
        self._repo = repositorio
        self._fabrica = fabrica
        self._conexiones = conexiones
        self._repositorios: dict[str, RepositorioAlmacen] = {}
        self._candado = threading.RLock()

    def obtener(self, almacen_id: str) -> Almacen | None:
        return self._repo.obtener(almacen_id)

    def exigir(self, almacen_id: str) -> Almacen:
        almacen = self.obtener(almacen_id)
        if almacen is None or not almacen.db_name:
            raise NoEncontrado("Almacén no encontrado o sin base de datos asignada")
        return almacen

    def repositorio(self, almacen_id: str) -> RepositorioAlmacen:
        clave = str(almacen_id)
        with self._candado:
            existente = self._repositorios.get(clave)
            if existente is not None:
                return existente
        almacen = self.exigir(clave)
        base = self._conexiones.base(self._fabrica.uri_almacen(almacen), almacen.db_name)
        repositorio = RepositorioAlmacen(base, almacen.almacen_id)
        with self._candado:
            self._repositorios.setdefault(clave, repositorio)
            return self._repositorios[clave]

    def invalidar(self, almacen_id: str) -> None:
        with self._candado:
            self._repositorios.pop(str(almacen_id), None)


__all__ = ["DirectorioAlmacenes"]
