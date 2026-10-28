"""Índices de las colecciones de productos."""

from __future__ import annotations

from pymongo.collection import Collection


def crear_indices(coleccion: Collection) -> None:
    """Crea una sola vez los índices usados por las búsquedas."""
    coleccion.create_index("nombre_normalizado")
    coleccion.create_index([("nombre_normalizado", 1), ("marca_normalizada", 1)])


__all__ = ["crear_indices"]
