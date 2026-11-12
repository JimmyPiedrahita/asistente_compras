"""Routers de la API HTTP."""

from . import (
    administracion,
    almacenes,
    busqueda,
    carrito,
    exportacion,
    lista_compra,
    salud,
    seguridad,
    sesiones,
)

ROUTERS = (
    salud.router,
    almacenes.router,
    seguridad.router,
    sesiones.router,
    lista_compra.router,
    busqueda.router,
    carrito.router,
    administracion.router,
    exportacion.router,
)

__all__ = ["ROUTERS"]
