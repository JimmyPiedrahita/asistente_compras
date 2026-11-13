"""Roles de la aplicación y sus descripciones."""

from __future__ import annotations

CLIENTE = "CLIENTE"
ADMINISTRADOR_ALMACEN = "ADMINISTRADOR_ALMACEN"
ADMINISTRADOR_APP = "ADMINISTRADOR_APP"

ROLES = (CLIENTE, ADMINISTRADOR_ALMACEN, ADMINISTRADOR_APP)

DESCRIPCION_ROLES = {
    CLIENTE: "Cliente: compra, compara y finaliza pagos.",
    ADMINISTRADOR_ALMACEN: (
        "Administrador de almacén: gestiona sus productos, cupones, compras y "
        "estadísticas. No puede comprar ni administrar la plataforma."
    ),
    ADMINISTRADOR_APP: (
        "Administrador de la aplicación: crea almacenes y sus administradores. "
        "No gestiona productos, cupones ni compras."
    ),
}

__all__ = [
    "ADMINISTRADOR_ALMACEN",
    "ADMINISTRADOR_APP",
    "CLIENTE",
    "DESCRIPCION_ROLES",
    "ROLES",
]
