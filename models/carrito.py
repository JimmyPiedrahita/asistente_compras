"""Carrito de compras por sesión."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ItemCarrito:
    item_id: str
    almacen_id: str
    producto_id: str
    cantidad: int = 1


@dataclass
class Carrito:
    items: list[ItemCarrito] = field(default_factory=list)
    cupones: list[str] = field(default_factory=list)

    def agregar(self, almacen_id: str, producto_id: str, cantidad: int = 1) -> ItemCarrito:
        cantidad = max(1, int(cantidad))
        for item in self.items:
            if item.almacen_id == str(almacen_id) and item.producto_id == str(producto_id):
                item.cantidad += cantidad
                return item
        item = ItemCarrito(
            item_id=uuid.uuid4().hex,
            almacen_id=str(almacen_id),
            producto_id=str(producto_id),
            cantidad=cantidad,
        )
        self.items.append(item)
        return item

    def quitar(self, item_id: str) -> bool:
        antes = len(self.items)
        self.items = [item for item in self.items if item.item_id != str(item_id)]
        return len(self.items) != antes

    def actualizar_cantidad(self, item_id: str, cantidad: int) -> bool:
        cantidad = int(cantidad)
        if cantidad < 1:
            raise ValueError("La cantidad debe ser mayor que cero")
        for item in self.items:
            if item.item_id == str(item_id):
                item.cantidad = cantidad
                return True
        return False

    def vaciar(self) -> None:
        self.items.clear()
        self.cupones.clear()

    def almacenes(self) -> set[str]:
        return {item.almacen_id for item in self.items}

    def __len__(self) -> int:
        return len(self.items)


__all__ = ["Carrito", "ItemCarrito"]
