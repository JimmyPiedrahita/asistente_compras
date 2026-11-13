"""Producto del catálogo de un almacén."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .texto import normalizar_texto


def validar_precio(precio: Any, campo: str = "precio") -> float:
    try:
        valor = float(precio)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{campo} debe ser numérico") from error
    if not math.isfinite(valor):
        raise ValueError(f"{campo} debe ser finito")
    redondeado = round(valor, 2)
    if redondeado <= 0:
        raise ValueError(f"{campo} debe ser mayor que cero")
    return redondeado


@dataclass
class Producto:
    producto_id: str
    almacen_id: str
    tipo_producto: str
    nombre: str
    precio: float
    presentacion: str
    marca_variedad: str = ""
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None

    @classmethod
    def crear(
        cls,
        *,
        producto_id: str,
        almacen_id: str,
        tipo_producto: str,
        nombre: str,
        precio: Any,
        presentacion: str,
        marca_variedad: str | None = None,
    ) -> Producto:
        tipo = " ".join(str(tipo_producto or "").split())
        if not tipo:
            raise ValueError("El tipo de producto es obligatorio")
        nombre_limpio = " ".join(str(nombre or "").split())
        if not nombre_limpio:
            raise ValueError("El nombre del producto es obligatorio")
        presentacion_limpia = " ".join(str(presentacion or "").split())
        if not presentacion_limpia:
            raise ValueError("La presentación es obligatoria")
        return cls(
            producto_id=str(producto_id),
            almacen_id=str(almacen_id),
            tipo_producto=tipo,
            nombre=nombre_limpio,
            marca_variedad=" ".join(str(marca_variedad or "").split()),
            precio=validar_precio(precio),
            presentacion=presentacion_limpia,
            creado_en=datetime.now(timezone.utc),
            actualizado_en=datetime.now(timezone.utc),
        )

    @property
    def tipo_normalizado(self) -> str:
        return normalizar_texto(self.tipo_producto)

    @property
    def nombre_normalizado(self) -> str:
        return normalizar_texto(self.nombre)

    @property
    def presentacion_normalizada(self) -> str:
        return normalizar_texto(self.presentacion)

    def publico(self) -> dict[str, Any]:
        return {
            "producto_id": self.producto_id,
            "almacen_id": self.almacen_id,
            "tipo_producto": self.tipo_producto,
            "nombre": self.nombre,
            "marca_variedad": self.marca_variedad,
            "precio": self.precio,
            "presentacion": self.presentacion,
        }


__all__ = ["Producto", "validar_precio"]
