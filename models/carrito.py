"""Carrito de compras observable."""

from __future__ import annotations

from typing import Any

from core.observer import SujetoObservable

from .listas import ListaDoblementeEnlazada


class CarritoCompras(SujetoObservable):
    """Carrito observable: notifica a la vista en cada cambio."""

    def __init__(self) -> None:
        super().__init__()
        self._productos = ListaDoblementeEnlazada()
        self._estrategia_descuento: Any = None

    def agregar_producto(self, producto: Any) -> None:
        self._productos.agregar_al_final(producto)
        self.notificar_observadores(f"Producto '{producto.nombre}' añadido.")

    def eliminar_producto(self, indice: int) -> bool:
        try:
            eliminado = self._productos.eliminar_en(indice)
        except IndexError:
            return False
        self.notificar_observadores(f"Producto '{eliminado.nombre}' eliminado.")
        return True

    def vaciar(self) -> None:
        self._productos.limpiar()
        self.notificar_observadores("Carrito vaciado.")

    def establecer_estrategia_descuento(self, estrategia: Any) -> None:
        self._estrategia_descuento = estrategia
        self.notificar_observadores("Estrategia de descuento actualizada.")

    def obtener_productos(self) -> list[Any]:
        return list(self._productos)

    def calcular_subtotal(self) -> float:
        return sum(producto.obtener_precio_final() for producto in self._productos)

    def calcular_total(self) -> float:
        subtotal = self.calcular_subtotal()
        if self._estrategia_descuento is None:
            return subtotal
        return self._estrategia_descuento.calcular(subtotal)

    def __len__(self) -> int:
        return len(self._productos)


__all__ = ["CarritoCompras"]
