"""Roles, catálogo de permisos y matriz canónica de autorización.

La matriz de este módulo es la fuente de verdad del *significado* de cada rol.
Al arrancar, el repositorio de seguridad la replica en MongoDB (colección
``roles``) y las sesiones consultan los permisos almacenados allí. Así la base
de datos puede auditarse y evolucionar sin repartir constantes por el código.
"""

from __future__ import annotations

from core.logging import obtener_logger

INVITADO = "INVITADO"
CLIENTE = "CLIENTE"
PROVEEDOR = "PROVEEDOR"
ADMIN = "ADMIN"

ROLES = (INVITADO, CLIENTE, PROVEEDOR, ADMIN)

# Permisos de consumo (cliente) -----------------------------------------
VER_MENU = "ver_menu"
CREAR_LISTA = "crear_lista"
AGREGAR_PRODUCTO = "agregar_producto"
ELIMINAR_PRODUCTO = "eliminar_producto"
COMPARAR = "comparar"
EXPORTAR = "exportar"
APLICAR_DESCUENTO = "aplicar_descuento"

# Permisos de inventario (proveedor y administrador) ---------------------
VER_INVENTARIO = "ver_inventario"
GESTIONAR_INVENTARIO = "gestionar_inventario"
EDITAR_PRECIO = "editar_precio"
IMPORTAR_CSV = "importar_csv"
# Alias histórico: el nombre cambió para reflejar que no es solo "cargar".
CARGAR_CSV = IMPORTAR_CSV

# Permisos de plataforma (solo administrador) ---------------------------
LOGIN_ADMIN = "login_admin"
GESTIONAR_USUARIOS = "gestionar_usuarios"
GESTIONAR_ALMACENES = "gestionar_almacenes"
GESTIONAR_COMPARADOR = "gestionar_comparador"

PERMISOS: dict[str, str] = {
    VER_MENU: "Consultar el menú, el estado de la sesión y los catálogos públicos.",
    CREAR_LISTA: "Crear y consultar su lista personal de compras.",
    AGREGAR_PRODUCTO: "Agregar productos a la lista o al carrito.",
    ELIMINAR_PRODUCTO: "Quitar productos de la lista o del carrito.",
    COMPARAR: "Buscar productos y comparar precios entre almacenes.",
    EXPORTAR: "Descargar la lista y el carrito en CSV.",
    APLICAR_DESCUENTO: "Aplicar descuentos porcentuales o fijos al carrito.",
    VER_INVENTARIO: "Consultar el inventario del almacén asignado.",
    GESTIONAR_INVENTARIO: "Crear y eliminar productos del inventario.",
    EDITAR_PRECIO: "Modificar el precio de un producto existente.",
    IMPORTAR_CSV: "Importar productos desde un archivo CSV.",
    LOGIN_ADMIN: "Iniciar sesión con la clave administrativa.",
    GESTIONAR_USUARIOS: "Listar usuarios y crear o modificar proveedores.",
    GESTIONAR_ALMACENES: "Administrar el catálogo global de almacenes.",
    GESTIONAR_COMPARADOR: "Consultar y reconciliar la proyección del comparador.",
}

DESCRIPCION_ROLES: dict[str, str] = {
    INVITADO: (
        "Visitante sin autenticación. Solo puede ver el menú y los catálogos "
        "públicos; no tiene lista, carrito ni funciones administrativas."
    ),
    CLIENTE: (
        "Comprador. Gestiona su lista personal, busca y compara precios, usa el "
        "carrito, aplica descuentos y exporta sus datos. No modifica inventarios."
    ),
    PROVEEDOR: (
        "Responsable de un único almacén. Crea, edita el precio, elimina e "
        "importa productos solo en el almacén que tiene asignado. No puede "
        "comprar ni administrar usuarios, almacenes o el comparador."
    ),
    ADMIN: (
        "Administrador de la plataforma. Supervisa todos los almacenes, gestiona "
        "usuarios y proveedores, importa inventarios globales y reconcilia el "
        "comparador. También conserva las funciones de comprador para tareas de "
        "soporte y verificación."
    ),
}

_PERMISOS_POR_ROL: dict[str, tuple[str, ...]] = {
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
    PROVEEDOR: (
        VER_MENU,
        VER_INVENTARIO,
        GESTIONAR_INVENTARIO,
        EDITAR_PRECIO,
        IMPORTAR_CSV,
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
        VER_INVENTARIO,
        GESTIONAR_INVENTARIO,
        EDITAR_PRECIO,
        IMPORTAR_CSV,
        GESTIONAR_ALMACENES,
        GESTIONAR_COMPARADOR,
        GESTIONAR_USUARIOS,
    ),
}

MATRIZ_PERMISOS: dict[str, tuple[str, ...]] = dict(_PERMISOS_POR_ROL)

logger = obtener_logger("asistente_compras.permisos")


def permisos_de(rol: str) -> tuple[str, ...]:
    """Permisos canónicos de un rol (vacío si el rol no existe)."""
    return MATRIZ_PERMISOS.get(str(rol or "").upper(), ())


def descripcion_de(rol: str) -> str:
    return DESCRIPCION_ROLES.get(str(rol or "").upper(), "")


def tiene_permiso(rol: str, permiso: str) -> bool:
    """Comprueba la matriz y registra el resultado a nivel DEBUG/WARNING."""
    rol = str(rol or "").upper()
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
    "DESCRIPCION_ROLES",
    "EDITAR_PRECIO",
    "ELIMINAR_PRODUCTO",
    "EXPORTAR",
    "GESTIONAR_ALMACENES",
    "GESTIONAR_COMPARADOR",
    "GESTIONAR_INVENTARIO",
    "GESTIONAR_USUARIOS",
    "IMPORTAR_CSV",
    "INVITADO",
    "LOGIN_ADMIN",
    "MATRIZ_PERMISOS",
    "PERMISOS",
    "PROVEEDOR",
    "ROLES",
    "VER_INVENTARIO",
    "VER_MENU",
    "configurar_nivel_logs",
    "descripcion_de",
    "logger",
    "permisos_de",
    "tiene_permiso",
]
