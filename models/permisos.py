"""Roles, matriz de permisos y comprobación centralizada."""

from __future__ import annotations

from core.logging import obtener_logger

INVITADO = "INVITADO"
CLIENTE = "CLIENTE"
ADMIN = "ADMIN"

ROLES = (INVITADO, CLIENTE, ADMIN)

VER_MENU = "ver_menu"
CREAR_LISTA = "crear_lista"
AGREGAR_PRODUCTO = "agregar_producto"
ELIMINAR_PRODUCTO = "eliminar_producto"
COMPARAR = "comparar"
EXPORTAR = "exportar"
APLICAR_DESCUENTO = "aplicar_descuento"
LOGIN_ADMIN = "login_admin"
CARGAR_CSV = "cargar_csv"
EDITAR_PRECIO = "editar_precio"
GESTIONAR_ALMACENES = "gestionar_almacenes"

MATRIZ_PERMISOS: dict[str, tuple[str, ...]] = {
    INVITADO: (VER_MENU,),
    CLIENTE: (
        VER_MENU,
        CREAR_LISTA,
        AGREGAR_PRODUCTO,
        ELIMINAR_PRODUCTO,
        COMPARAR,
        EXPORTAR,
        APLICAR_DESCUENTO,
    ),
    ADMIN: (
        VER_MENU,
        CREAR_LISTA,
        AGREGAR_PRODUCTO,
        ELIMINAR_PRODUCTO,
        COMPARAR,
        EXPORTAR,
        APLICAR_DESCUENTO,
        LOGIN_ADMIN,
        CARGAR_CSV,
        EDITAR_PRECIO,
        GESTIONAR_ALMACENES,
    ),
}

logger = obtener_logger("asistente_compras.permisos")


def tiene_permiso(rol: str, permiso: str) -> bool:
    """Comprueba la matriz y registra el resultado a nivel DEBUG/WARNING."""
    permitido = rol in MATRIZ_PERMISOS and permiso in MATRIZ_PERMISOS[rol]
    if permitido:
        logger.debug("Permiso '%s' concedido para %s", permiso, rol)
    else:
        logger.warning("Permiso '%s' denegado para %s", permiso, rol)
    return permitido


def configurar_nivel_logs(nivel: int) -> None:
    logger.setLevel(nivel)


__all__ = [
    "ADMIN",
    "AGREGAR_PRODUCTO",
    "APLICAR_DESCUENTO",
    "CARGAR_CSV",
    "CLIENTE",
    "COMPARAR",
    "CREAR_LISTA",
    "EDITAR_PRECIO",
    "ELIMINAR_PRODUCTO",
    "EXPORTAR",
    "GESTIONAR_ALMACENES",
    "INVITADO",
    "LOGIN_ADMIN",
    "MATRIZ_PERMISOS",
    "ROLES",
    "VER_MENU",
    "logger",
    "tiene_permiso",
]
