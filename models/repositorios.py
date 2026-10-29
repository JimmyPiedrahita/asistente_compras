"""Contrato de persistencia de inventarios y de la proyección integrada."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from .almacenes import Almacen
from .listas import ListaSimple
from .productos import Producto


class InventarioRepository(Protocol):
    """Interfaz que debe cumplir cualquier repositorio de inventario."""

    def cargar_almacen(self, id_almacen: int) -> list[Producto]: ...

    def listar_productos(
        self, id_almacen: int, limit: int = 100, offset: int = 0
    ) -> tuple[list[Producto], int]: ...

    def producto_en_indice(self, id_almacen: int, indice: int) -> Producto | None: ...

    def obtener_producto(self, id_almacen: int, producto_id: str) -> Producto | None: ...

    def existe_nombre_marca(
        self, id_almacen: int, nombre: str, marca: str | None = None
    ) -> bool: ...

    def contar(self, id_almacen: int) -> int: ...

    def insertar(self, id_almacen: int, producto: Producto) -> None: ...

    def actualizar(self, id_almacen: int, producto: Producto) -> None: ...

    def eliminar(self, id_almacen: int, producto_id: str) -> None: ...

    def buscar_mejor_precio(self, nombres: Iterable[str]) -> dict[Almacen, ListaSimple]: ...

    def buscar_catalogo(
        self, nombres: Iterable[str], limit: int = 100, offset: int = 0
    ) -> dict[Almacen, ListaSimple]: ...

    def buscar_global(self, nombres: Iterable[str]) -> list[dict[str, Any]]: ...

    def estado_comparador(self) -> dict[str, Any]: ...

    def reconciliar_comparador(self) -> dict[str, Any]: ...

    def ping(self) -> None: ...

    def close(self) -> None: ...


__all__ = ["InventarioRepository"]
