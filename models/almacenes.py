"""Almacenes, inventarios e índice auxiliar de búsqueda."""

from __future__ import annotations

import threading
from collections.abc import Iterable, Iterator

from core.config import AlmacenConfig
from core.errors import Conflicto

from .listas import ListaSimple
from .productos import Producto
from .texto import normalizar_texto


class Almacen:
    """Almacén con inventario en una lista simplemente enlazada.

    El inventario sigue siendo la estructura principal. Los diccionarios
    ``_por_nombre`` y ``_por_id`` son índices auxiliares para evitar búsquedas
    lineales en cada comparación.
    """

    def __init__(self, id_almacen: int, nombre: str) -> None:
        self.id_almacen = int(id_almacen)
        self.nombre = str(nombre).strip() or f"Almacen {id_almacen}"
        self.inventario = ListaSimple()
        self._por_nombre: dict[str, ListaSimple] = {}
        self._por_id: dict[str, Producto] = {}
        self._indice_tamano = 0

    def __repr__(self) -> str:
        return f"Almacen({self.id_almacen}, {self.nombre!r})"

    def agregar_producto(self, producto: Producto) -> None:
        if producto.producto_id in self._por_id:
            raise Conflicto(f"El producto {producto.producto_id} ya existe en {self.nombre}")
        self.inventario.agregar(producto)
        self._indexar(producto)

    # Alias de compatibilidad con el código anterior.
    agregar = agregar_producto

    def cargar(self, productos: Iterable[Producto]) -> None:
        """Reemplaza el inventario completo con los productos indicados."""
        self.inventario.limpiar()
        self._por_nombre.clear()
        self._por_id.clear()
        self._indice_tamano = 0
        for producto in productos:
            self.agregar_producto(producto)

    def productos_por_nombre(self, nombre: str) -> Iterator[Producto]:
        self._asegurar_indice()
        bucket = self._por_nombre.get(normalizar_texto(nombre))
        if bucket is None:
            return
        yield from bucket.mostrar()

    def producto_por_id(self, producto_id: str) -> Producto | None:
        self._asegurar_indice()
        return self._por_id.get(str(producto_id))

    def tiene_producto_id(self, producto_id: str) -> bool:
        return self.producto_por_id(producto_id) is not None

    def existe_nombre_marca(self, nombre: str, marca: str | None = None) -> bool:
        for producto in self.productos_por_nombre(nombre):
            if marca is None or normalizar_texto(producto.marca) == normalizar_texto(marca):
                return True
        return False

    def _indexar(self, producto: Producto) -> None:
        clave = normalizar_texto(producto.nombre)
        self._por_nombre.setdefault(clave, ListaSimple()).agregar(producto)
        self._por_id[producto.producto_id] = producto
        self._indice_tamano += 1

    def _asegurar_indice(self) -> None:
        # Si alguien agregó productos directamente a ``inventario``, se
        # reconstruye el índice para mantenerlo consistente.
        if self._indice_tamano != len(self.inventario):
            self._reconstruir_indice()

    def _reconstruir_indice(self) -> None:
        self._por_nombre.clear()
        self._por_id.clear()
        self._indice_tamano = 0
        for producto in self.inventario.mostrar():
            self._indexar(producto)

    def __len__(self) -> int:
        return len(self.inventario)

    def __iter__(self) -> Iterator[Producto]:
        return self.inventario.mostrar()


class GestorAlmacenes:
    """Gestiona la colección de almacenes y coordina la persistencia."""

    def __init__(
        self,
        persistencia: object | None = None,
        almacenes: Iterable[Almacen | AlmacenConfig] | None = None,
    ) -> None:
        self.persistencia = persistencia
        self.almacenes: list[Almacen] = []
        self._por_id: dict[int, Almacen] = {}
        self.candado = threading.RLock()

        if almacenes is None:
            almacenes = (Almacen(1, "Almacen 1"), Almacen(2, "Almacen 2"), Almacen(3, "Almacen 3"))

        for item in almacenes:
            if isinstance(item, Almacen):
                self.agregar_almacen(item)
            else:
                self.agregar_almacen(Almacen(item.id, item.nombre))

    def agregar_almacen(self, almacen: Almacen) -> None:
        with self.candado:
            existente = self._por_id.get(almacen.id_almacen)
            if existente is None:
                self.almacenes.append(almacen)
            else:
                indice = self.almacenes.index(existente)
                self.almacenes[indice] = almacen
            self._por_id[almacen.id_almacen] = almacen

    def obtener_almacenes(self) -> list[Almacen]:
        return self.almacenes

    def obtener_almacen(self, id_almacen: int) -> Almacen | None:
        try:
            return self._por_id.get(int(id_almacen))
        except (TypeError, ValueError):
            return None

    def agregar_producto(self, id_almacen: int, producto: Producto) -> bool:
        with self.candado:
            almacen = self.obtener_almacen(id_almacen)
            if almacen is None:
                return False
            if almacen.tiene_producto_id(producto.producto_id):
                raise Conflicto(f"El producto {producto.producto_id} ya existe en el almacén")
            if self.persistencia is not None:
                self.persistencia.insertar(id_almacen, producto)  # type: ignore[attr-defined]
            almacen.agregar_producto(producto)
            return True

    def cargar_inventarios(self) -> None:
        """Carga una sola vez todos los inventarios desde la persistencia."""
        if self.persistencia is None:
            return
        with self.candado:
            for almacen in self.almacenes:
                productos = self.persistencia.cargar_almacen(  # type: ignore[attr-defined]
                    almacen.id_almacen
                )
                almacen.cargar(productos)

    def recargar_almacen(self, id_almacen: int) -> bool:
        with self.candado:
            almacen = self.obtener_almacen(id_almacen)
            if almacen is None or self.persistencia is None:
                return False
            productos = self.persistencia.cargar_almacen(id_almacen)  # type: ignore[attr-defined]
            almacen.cargar(productos)
            return True

    def buscar_producto(
        self, id_almacen: int, nombre: str, marca: str | None = None
    ) -> Producto | None:
        almacen = self.obtener_almacen(id_almacen)
        if almacen is None:
            return None
        for producto in almacen.productos_por_nombre(nombre):
            if marca is None or normalizar_texto(producto.marca) == normalizar_texto(marca):
                return producto
        return None

    def productos(self) -> Iterator[tuple[Almacen, Producto]]:
        """Itera pares (almacén, producto) de todo el sistema."""
        for almacen in self.almacenes:
            for producto in almacen.inventario.mostrar():
                yield almacen, producto


__all__ = ["Almacen", "GestorAlmacenes"]
