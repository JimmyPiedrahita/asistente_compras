"""Contrato de persistencia de inventarios."""

from __future__ import annotations

from typing import Protocol

from .productos import Producto


class InventarioRepository(Protocol):
    """Interfaz que debe cumplir cualquier repositorio de inventario."""

    def cargar_almacen(self, id_almacen: int) -> list[Producto]: ...

    def insertar(self, id_almacen: int, producto: Producto) -> None: ...

    def actualizar(self, id_almacen: int, producto: Producto) -> None: ...

    def ping(self) -> None: ...

    def close(self) -> None: ...


__all__ = ["InventarioRepository"]
