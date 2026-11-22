"""Routers de la API HTTP."""

from . import admin_almacen, admin_app, auth, cliente, salud

ROUTERS = (
    salud.router,
    auth.router,
    cliente.router,
    admin_almacen.router,
    admin_app.router,
)

__all__ = ["ROUTERS"]
