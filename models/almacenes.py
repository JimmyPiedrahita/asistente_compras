"""Almacenes, inventarios e índice auxiliar de búsqueda.

``Almacen`` conserva una lista enlazada para los casos en los que se trabaja
sin persistencia (pruebas y uso embebido). La API no carga el catálogo
completo: ``GestorAlmacenes`` delega en el repositorio cuando está disponible y
solo usa memoria como fallback para pruebas.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Iterator
from typing import Any

from core.config import AlmacenConfig
from core.errors import Conflicto

from .listas import ListaSimple
from .productos import Producto
from .texto import normalizar_texto


class Almacen:
    """Almacén con inventario opcional en una lista simplemente enlazada.

    Los diccionarios ``_por_nombre`` y ``_por_id`` son índices auxiliares para
    evitar búsquedas lineales en cada comparación.
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

    def eliminar_producto(self, producto_id: str) -> bool:
        objetivo = self._por_id.get(str(producto_id))
        if objetivo is None:
            return False
        restantes = [
            producto
            for producto in self.inventario.mostrar()
            if producto.producto_id != objetivo.producto_id
        ]
        self.inventario.limpiar()
        self._por_nombre.clear()
        self._por_id.clear()
        self._indice_tamano = 0
        for producto in restantes:
            self.inventario.agregar(producto)
            self._indexar(producto)
        return True

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
    """Coordina almacenes y delega en la persistencia cuando existe.

    Sin persistencia funciona íntegramente en memoria, lo que mantiene las
    pruebas de dominio y los usos embebidos. Con persistencia no se carga el
    catálogo: los listados y búsquedas se resuelven con consultas indexadas.
    """

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
            almacenes = (
                Almacen(1, "Almacen 1"),
                Almacen(2, "Almacen 2"),
                Almacen(3, "Almacen 3"),
            )

        for item in almacenes:
            if isinstance(item, Almacen):
                self.agregar_almacen(item)
            else:
                self.agregar_almacen(Almacen(item.id, item.nombre))

    def _delegar(self, metodo: str) -> bool:
        return self.persistencia is not None and callable(getattr(self.persistencia, metodo, None))

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
            if self._delegar("insertar"):
                self.persistencia.insertar(id_almacen, producto)  # type: ignore[attr-defined]
                return True
            if almacen.tiene_producto_id(producto.producto_id):
                raise Conflicto(f"El producto {producto.producto_id} ya existe en el almacén")
            almacen.agregar_producto(producto)
            return True

    def actualizar_producto(self, id_almacen: int, producto: Producto) -> bool:
        with self.candado:
            if self.obtener_almacen(id_almacen) is None:
                return False
            if self._delegar("actualizar"):
                self.persistencia.actualizar(id_almacen, producto)  # type: ignore[attr-defined]
            return True

    def eliminar_producto(self, id_almacen: int, producto_id: str) -> bool:
        with self.candado:
            almacen = self.obtener_almacen(id_almacen)
            if almacen is None:
                return False
            if self._delegar("eliminar"):
                self.persistencia.eliminar(id_almacen, producto_id)  # type: ignore[attr-defined]
                return True
            return almacen.eliminar_producto(producto_id)

    def obtener_producto(self, id_almacen: int, producto_id: str) -> Producto | None:
        with self.candado:
            almacen = self.obtener_almacen(id_almacen)
            if almacen is None:
                return None
            if self._delegar("obtener_producto"):
                return self.persistencia.obtener_producto(id_almacen, producto_id)  # type: ignore[attr-defined]
            return almacen.producto_por_id(producto_id)

    def producto_en_indice(self, id_almacen: int, indice: int) -> Producto | None:
        with self.candado:
            almacen = self.obtener_almacen(id_almacen)
            if almacen is None:
                return None
            if self._delegar("producto_en_indice"):
                return self.persistencia.producto_en_indice(id_almacen, indice)  # type: ignore[attr-defined]
            try:
                return almacen.inventario.obtener(indice)
            except IndexError:
                return None

    def listar_productos(
        self, id_almacen: int, limit: int = 100, offset: int = 0
    ) -> tuple[list[Producto], int]:
        with self.candado:
            almacen = self.obtener_almacen(id_almacen)
            if almacen is None:
                return [], 0
            if self._delegar("listar_productos"):
                return self.persistencia.listar_productos(  # type: ignore[attr-defined]
                    id_almacen, limit, offset
                )
            productos = list(almacen.inventario.mostrar())
            return productos[offset : offset + limit], len(productos)

    def contar_productos(self, id_almacen: int) -> int:
        with self.candado:
            almacen = self.obtener_almacen(id_almacen)
            if almacen is None:
                return 0
            if self._delegar("contar"):
                return int(self.persistencia.contar(id_almacen))  # type: ignore[attr-defined]
            return len(almacen)

    def existe_nombre_marca(self, id_almacen: int, nombre: str, marca: str | None = None) -> bool:
        with self.candado:
            almacen = self.obtener_almacen(id_almacen)
            if almacen is None:
                return False
            if self._delegar("existe_nombre_marca"):
                return bool(  # type: ignore[attr-defined]
                    self.persistencia.existe_nombre_marca(id_almacen, nombre, marca)
                )
            return almacen.existe_nombre_marca(nombre, marca)

    # Búsquedas ---------------------------------------------------------

    def buscar_mejor_precio(self, nombres: Iterable[str]) -> dict[Almacen, ListaSimple]:
        nombres = list(nombres)
        if self._delegar("buscar_mejor_precio"):
            return self.persistencia.buscar_mejor_precio(nombres)  # type: ignore[attr-defined]
        resultado: dict[Almacen, ListaSimple] = {}
        for almacen in self.almacenes:
            for nombre in nombres:
                mejor = self._mejor(almacen, nombre)
                if mejor is None:
                    continue
                resultado.setdefault(almacen, ListaSimple()).agregar(mejor)
        return resultado

    def buscar_catalogo(
        self, nombres: Iterable[str], limit: int = 100, offset: int = 0
    ) -> dict[Almacen, ListaSimple]:
        nombres = list(nombres)
        if self._delegar("buscar_catalogo"):
            return self.persistencia.buscar_catalogo(  # type: ignore[attr-defined]
                nombres, limit, offset
            )
        encontrados: list[tuple[Almacen, Producto]] = []
        for almacen in self.almacenes:
            for nombre in nombres:
                for producto in almacen.productos_por_nombre(nombre):
                    encontrados.append((almacen, producto))
        resultado: dict[Almacen, ListaSimple] = {}
        for almacen, producto in encontrados[offset : offset + limit]:
            resultado.setdefault(almacen, ListaSimple()).agregar(producto)
        return resultado

    def buscar_global(self, nombres: Iterable[str]) -> list[dict[str, Any]]:
        nombres = list(nombres)
        if self._delegar("buscar_global"):
            return self.persistencia.buscar_global(nombres)  # type: ignore[attr-defined]
        resultado: list[dict[str, Any]] = []
        for nombre in nombres:
            mejor: Producto | None = None
            mejor_almacen: Almacen | None = None
            for almacen in self.almacenes:
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

    @staticmethod
    def _mejor(almacen: Almacen, nombre: str) -> Producto | None:
        mejor: Producto | None = None
        for producto in almacen.productos_por_nombre(nombre):
            if mejor is None or producto.obtener_precio_final() < mejor.obtener_precio_final():
                mejor = producto
        return mejor

    # Administración ----------------------------------------------------

    def estado_comparador(self) -> dict[str, Any]:
        if self._delegar("estado_comparador"):
            return self.persistencia.estado_comparador()  # type: ignore[attr-defined]
        return {
            "estado": "sin_persistencia",
            "documentos": 0,
            "ultima_sincronizacion": None,
            "ultimo_evento": None,
            "tiene_resume_token": False,
        }

    def reconciliar_comparador(self) -> dict[str, Any]:
        if self._delegar("reconciliar_comparador"):
            return self.persistencia.reconciliar_comparador()  # type: ignore[attr-defined]
        return {"documentos": 0, "reconciliados": 0}

    def cargar_inventarios(self) -> None:
        """Carga completa desde la persistencia.

        Se mantiene por compatibilidad con pruebas y scripts. La API ya no la
        usa para operar: el catálogo no se guarda en memoria.
        """
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
        """Itera pares (almacén, producto) del inventario en memoria."""
        for almacen in self.almacenes:
            for producto in almacen.inventario.mostrar():
                yield almacen, producto


__all__ = ["Almacen", "GestorAlmacenes"]
