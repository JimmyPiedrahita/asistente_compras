"""Estrategias de búsqueda de productos (patrón Strategy)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..almacenes import Almacen, GestorAlmacenes
from ..listas import ListaSimple
from ..productos import Producto


class EstrategiaBusqueda(ABC):
    @abstractmethod
    def buscar(self, lista_compras: Any, gestor_almacenes: GestorAlmacenes) -> Any:
        raise NotImplementedError


class BusquedaMejorPrecioStrategy(EstrategiaBusqueda):
    """Mejor precio de cada producto dentro de cada almacén."""

    def buscar(
        self, lista_compras: Any, gestor_almacenes: GestorAlmacenes
    ) -> dict[Almacen, ListaSimple]:
        resultado: dict[Almacen, ListaSimple] = {}
        for almacen in gestor_almacenes.obtener_almacenes():
            for nombre in lista_compras.mostrar():
                mejor = self._mejor(almacen, nombre)
                if mejor is None:
                    continue
                if almacen not in resultado:
                    resultado[almacen] = ListaSimple()
                resultado[almacen].agregar(mejor)
        return resultado

    @staticmethod
    def _mejor(almacen: Almacen, nombre: str) -> Producto | None:
        mejor: Producto | None = None
        for producto in almacen.productos_por_nombre(nombre):
            if mejor is None or producto.obtener_precio_final() < mejor.obtener_precio_final():
                mejor = producto
        return mejor


class BusquedaCatalogoStrategy(EstrategiaBusqueda):
    """Todas las coincidencias disponibles en cada almacén."""

    def buscar(
        self, lista_compras: Any, gestor_almacenes: GestorAlmacenes
    ) -> dict[Almacen, ListaSimple]:
        resultado: dict[Almacen, ListaSimple] = {}
        for almacen in gestor_almacenes.obtener_almacenes():
            encontrados = ListaSimple()
            for nombre in lista_compras.mostrar():
                for producto in almacen.productos_por_nombre(nombre):
                    encontrados.agregar(producto)
            if not encontrados.esta_vacia():
                resultado[almacen] = encontrados
        return resultado


class MejorPrecioGlobalStrategy(EstrategiaBusqueda):
    """Compara entre todos los almacenes y devuelve la opción más barata."""

    def buscar(self, lista_compras: Any, gestor_almacenes: GestorAlmacenes) -> list[dict[str, Any]]:
        resultado: list[dict[str, Any]] = []
        for nombre in lista_compras.mostrar():
            mejor: Producto | None = None
            mejor_almacen: Almacen | None = None
            for almacen in gestor_almacenes.obtener_almacenes():
                for producto in almacen.productos_por_nombre(nombre):
                    if (
                        mejor is None
                        or producto.obtener_precio_final() < mejor.obtener_precio_final()
                    ):
                        mejor = producto
                        mejor_almacen = almacen
            if mejor is not None and mejor_almacen is not None:
                resultado.append(
                    {
                        "nombre": mejor.nombre,
                        "producto": mejor,
                        "almacen": mejor_almacen,
                        "precio": mejor.obtener_precio_final(),
                    }
                )
        return resultado


__all__ = [
    "BusquedaCatalogoStrategy",
    "BusquedaMejorPrecioStrategy",
    "EstrategiaBusqueda",
    "MejorPrecioGlobalStrategy",
]
