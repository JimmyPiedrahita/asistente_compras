"""Productos del dominio y Factory Method."""

from __future__ import annotations

import copy
import math
import uuid
from typing import Any

from .texto import normalizar_texto


def _validar_precio(precio: Any, nombre_campo: str = "precio") -> float:
    try:
        valor = float(precio)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{nombre_campo} debe ser numérico") from error
    if not math.isfinite(valor):
        raise ValueError(f"{nombre_campo} debe ser finito")
    if valor < 0:
        raise ValueError(f"{nombre_campo} no puede ser negativo")
    return valor


class Producto:
    """Clase base para todos los productos."""

    tipo = "normal"

    def __init__(
        self,
        nombre: str,
        precio: float,
        marca: str = "Generica",
        categoria: str = "General",
        producto_id: str | None = None,
    ) -> None:
        nombre_limpio = str(nombre or "").strip()
        if not nombre_limpio:
            raise ValueError("El nombre del producto no puede estar vacío")
        self.producto_id = str(producto_id or uuid.uuid4())
        self.nombre = nombre_limpio
        self.precio = _validar_precio(precio)
        self.marca = str(marca or "Generica").strip() or "Generica"
        self.categoria = str(categoria or "General").strip() or "General"

    def obtener_precio_final(self) -> float:
        return self.precio

    def clonar(self) -> Producto:
        """Copia independiente: editar el inventario no altera el carrito."""
        return copy.deepcopy(self)

    def __str__(self) -> str:
        return f"{self.nombre} ({self.marca}) - ${self.obtener_precio_final():.2f}"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(nombre={self.nombre!r}, "
            f"precio={self.precio!r}, producto_id={self.producto_id!r})"
        )


class ProductoFisico(Producto):
    """Producto físico que requiere costo de envío."""

    tipo = "fisico"

    def __init__(
        self,
        nombre: str,
        precio: float,
        costo_envio: float = 5.0,
        marca: str = "Generica",
        categoria: str = "General",
        producto_id: str | None = None,
    ) -> None:
        super().__init__(nombre, precio, marca, categoria, producto_id)
        self.costo_envio = _validar_precio(costo_envio, "costo_envio")

    def obtener_precio_final(self) -> float:
        return self.precio + self.costo_envio


class ProductoDigital(Producto):
    """Producto digital sin costo de envío."""

    tipo = "digital"

    def __init__(
        self,
        nombre: str,
        precio: float,
        marca: str = "Generica",
        categoria: str = "General",
        producto_id: str | None = None,
    ) -> None:
        super().__init__(nombre, precio, marca, categoria, producto_id)

    def obtener_precio_final(self) -> float:
        return self.precio


class ProductoSuscripcion(Producto):
    """Producto por suscripción recurrente."""

    tipo = "suscripcion"

    def __init__(
        self,
        nombre: str,
        precio_mensual: float,
        meses: int = 1,
        marca: str = "Generica",
        categoria: str = "General",
        producto_id: str | None = None,
    ) -> None:
        super().__init__(nombre, precio_mensual, marca, categoria, producto_id)
        try:
            self.meses = int(meses)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Los meses deben ser un entero") from error
        if self.meses < 1:
            raise ValueError("Los meses deben ser al menos 1")

    def obtener_precio_final(self) -> float:
        return self.precio * self.meses


class FabricaProductos:
    """La fábrica centraliza la instanciación de objetos según el tipo."""

    TIPOS = ("normal", "fisico", "digital", "suscripcion")

    @staticmethod
    def crear_producto(
        tipo: str,
        nombre: str,
        precio: float,
        marca: str = "Generica",
        categoria: str = "General",
        producto_id: str | None = None,
        **kwargs: Any,
    ) -> Producto:
        tipo_norm = normalizar_texto(tipo) or "normal"
        nombre_limpio = str(nombre or "").strip()
        if not nombre_limpio:
            raise ValueError("El nombre del producto no puede estar vacío")
        precio_validado = _validar_precio(precio)

        if tipo_norm in ("normal", "producto"):
            return Producto(nombre_limpio, precio_validado, marca, categoria, producto_id)

        if tipo_norm == "fisico":
            return ProductoFisico(
                nombre_limpio,
                precio_validado,
                kwargs.get("costo_envio", 5.0),
                marca,
                categoria,
                producto_id,
            )

        if tipo_norm == "digital":
            return ProductoDigital(nombre_limpio, precio_validado, marca, categoria, producto_id)

        if tipo_norm == "suscripcion":
            return ProductoSuscripcion(
                nombre_limpio,
                precio_validado,
                kwargs.get("meses", 1),
                marca,
                categoria,
                producto_id,
            )

        raise ValueError(f"Tipo de producto no soportado: {tipo}")


__all__ = [
    "FabricaProductos",
    "Producto",
    "ProductoDigital",
    "ProductoFisico",
    "ProductoSuscripcion",
]
