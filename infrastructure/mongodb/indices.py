"""Índices de las colecciones de productos y de la proyección integrada."""

from __future__ import annotations

from pymongo import ASCENDING
from pymongo.collection import Collection


def crear_indices(coleccion: Collection) -> None:
    """Crea una sola vez los índices usados por las búsquedas por almacén."""
    coleccion.create_index("nombre_normalizado")
    coleccion.create_index([("nombre_normalizado", ASCENDING), ("marca_normalizada", ASCENDING)])


def crear_indices_comparador(coleccion: Collection) -> None:
    """Índices para resolver búsquedas globales sin recorrer el catálogo completo."""
    coleccion.create_index([("nombre_normalizado", ASCENDING), ("precio_final", ASCENDING)])
    coleccion.create_index(
        [
            ("almacen_id", ASCENDING),
            ("nombre_normalizado", ASCENDING),
            ("precio_final", ASCENDING),
        ]
    )
    coleccion.create_index("producto_id")
    coleccion.create_index("almacen_id")
    coleccion.create_index("_reconciliacion")


__all__ = ["crear_indices", "crear_indices_comparador"]
