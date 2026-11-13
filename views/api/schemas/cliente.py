"""Esquemas del flujo del cliente."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ModeloBase

ModoBusqueda = Literal["catalogo", "mejor_precio", "global"]


class ListaItemSolicitud(ModeloBase):
    nombre: str = Field(min_length=1, max_length=200)


class ListaRespuesta(ModeloBase):
    lista: list[str]


class BusquedaSolicitud(ModeloBase):
    modo: ModoBusqueda = "catalogo"


class ProductoPublico(ModeloBase):
    producto_id: str
    almacen_id: str
    tipo_producto: str
    nombre: str
    marca_variedad: str = ""
    precio: float
    presentacion: str


class ResultadoBusqueda(ModeloBase):
    almacen_id: str
    almacen: str
    producto: ProductoPublico


class GrupoBusqueda(ModeloBase):
    producto_buscado: str
    tipo_producto: str
    resultados: list[ResultadoBusqueda]
    sin_resultados: bool


class BusquedaRespuesta(ModeloBase):
    modo: str
    hay_productos: bool
    grupos: list[GrupoBusqueda]
    total_resultados: int


class CarritoItemSolicitud(ModeloBase):
    almacen_id: str = Field(min_length=1)
    producto_id: str = Field(min_length=1)
    cantidad: int = Field(default=1, ge=1)


class CantidadSolicitud(ModeloBase):
    cantidad: int = Field(ge=1)


class CuponSolicitud(ModeloBase):
    codigo: str = Field(min_length=1, max_length=50)


class CheckoutSolicitud(ModeloBase):
    telefono: str = Field(min_length=1, max_length=30)
    direccion: str = Field(min_length=1, max_length=300)
    ciudad: str = Field(min_length=1, max_length=120)
    total_esperado: float | None = None
    clave_idempotencia: str | None = Field(default=None, max_length=100)


class CompraRespuesta(ModeloBase):
    compra_id: str
    fecha: str
    cliente_nombre: str
    datos_entrega: dict
    items: list[dict]
    por_almacen: list[dict]
    subtotal: float
    descuento_total: float
    total: float
    pago_simulado: bool


__all__ = [
    "BusquedaRespuesta",
    "BusquedaSolicitud",
    "CantidadSolicitud",
    "CarritoItemSolicitud",
    "CheckoutSolicitud",
    "CompraRespuesta",
    "CuponSolicitud",
    "GrupoBusqueda",
    "ListaItemSolicitud",
    "ListaRespuesta",
    "ModoBusqueda",
    "ProductoPublico",
    "ResultadoBusqueda",
]
