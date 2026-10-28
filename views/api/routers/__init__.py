"""Routers de la API HTTP."""

from . import (
    administracion,
    almacenes,
    busqueda,
    carrito,
    exportacion,
    lista_compra,
    salud,
    sesiones,
)

ROUTERS = (
    salud.router,
    almacenes.router,
    sesiones.router,
    lista_compra.router,
    busqueda.router,
    carrito.router,
    administracion.router,
    exportacion.router,
)

__all__ = ["ROUTERS"]
