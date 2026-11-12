"""Modelo MVC: productos, almacenes, estructuras, carrito y estrategias."""

from .almacenes import Almacen, GestorAlmacenes
from .carrito import CarritoCompras
from .listas import ListaDoblementeEnlazada, ListaSimple
from .productos import (
    FabricaProductos,
    Producto,
    ProductoDigital,
    ProductoFisico,
    ProductoSuscripcion,
)
from .repositorios import InventarioRepository, SeguridadRepository
from .seguridad import Rol, SeguridadEnMemoria, Usuario
from .texto import normalizar_texto

__all__ = [
    "Almacen",
    "CarritoCompras",
    "FabricaProductos",
    "GestorAlmacenes",
    "InventarioRepository",
    "ListaDoblementeEnlazada",
    "ListaSimple",
    "Producto",
    "ProductoDigital",
    "ProductoFisico",
    "ProductoSuscripcion",
    "Rol",
    "SeguridadEnMemoria",
    "SeguridadRepository",
    "Usuario",
    "normalizar_texto",
]
