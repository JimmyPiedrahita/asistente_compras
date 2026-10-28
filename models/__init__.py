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
from .repositorios import InventarioRepository
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
    "normalizar_texto",
]
