"""Esquemas de búsqueda, carrito y sesiones."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from .base import ModeloBase
from .productos import ProductoRespuesta

ModoBusqueda = Literal["mejor_precio", "catalogo", "global"]
TipoDescuento = Literal["sin", "porcentaje", "fijo"]

_ALIAS_DESCUENTO = {
    "": "sin",
    "0": "sin",
    "1": "sin",
    "sin descuento": "sin",
    "2": "porcentaje",
    "porcentaje (%)": "porcentaje",
    "3": "fijo",
    "monto fijo": "fijo",
    "monto fijo ($)": "fijo",
}


class ListaProductoSolicitud(ModeloBase):
    nombre: str = Field(min_length=1, max_length=200)


class ListaRespuesta(ModeloBase):
    lista: list[str]


class UsuarioSesion(ModeloBase):
    nombre: str = Field(min_length=1, max_length=120)


class ClaveAdministrador(ModeloBase):
    clave: str = Field(min_length=1)


class SesionCreada(ModeloBase):
    session_id: str
    usuario: str
    rol: str


class BusquedaSolicitud(ModeloBase):
    modo: ModoBusqueda = "mejor_precio"
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @field_validator("modo", mode="before")
    @classmethod
    def normalizar_modo(cls, valor: object) -> str:
        return str(valor or "mejor_precio").strip().casefold()


class ResultadoBusquedaItem(ModeloBase):
    almacen_id: int
    almacen: str
    producto: ProductoRespuesta


class BusquedaRespuesta(ModeloBase):
    modo: str
    resultados: list[ResultadoBusquedaItem]


class CarritoProductoSolicitud(ModeloBase):
    almacen_id: int = Field(ge=1)
    producto_id: str = Field(min_length=1)


class DescuentoSolicitud(ModeloBase):
    tipo: TipoDescuento
    valor: float | None = Field(default=None, ge=0)

    @field_validator("tipo", mode="before")
    @classmethod
    def normalizar_tipo(cls, valor: object) -> str:
        normalizado = str(valor or "").strip().casefold()
        return _ALIAS_DESCUENTO.get(normalizado, normalizado)


class ResumenCarrito(ModeloBase):
    productos: list[ProductoRespuesta]
    subtotal: float
    total: float
    descuento: str


class EstadoSesion(ModeloBase):
    usuario: str | None
    rol: str
    lista: list[str]
    carrito: ResumenCarrito


class HealthRespuesta(ModeloBase):
    status: str
    database: str | None = None


__all__ = [
    "BusquedaRespuesta",
    "BusquedaSolicitud",
    "CarritoProductoSolicitud",
    "ClaveAdministrador",
    "DescuentoSolicitud",
    "EstadoSesion",
    "HealthRespuesta",
    "ListaProductoSolicitud",
    "ListaRespuesta",
    "ModoBusqueda",
    "ResultadoBusquedaItem",
    "ResumenCarrito",
    "SesionCreada",
    "TipoDescuento",
    "UsuarioSesion",
]
