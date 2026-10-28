"""Repositorio nulo para generar documentación y pruebas sin MongoDB."""

from __future__ import annotations

from models.productos import Producto


class RepositorioNulo:
    def cargar_almacen(self, id_almacen: int) -> list[Producto]:
        return []

    def insertar(self, id_almacen: int, producto: Producto) -> None:
        return None

    def actualizar(self, id_almacen: int, producto: Producto) -> None:
        return None

    def ping(self) -> None:
        return None

    def close(self) -> None:
        return None


__all__ = ["RepositorioNulo"]
