"""Esquemas de productos, almacenes y administración."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from .base import ModeloBase

TipoProducto = Literal["normal", "fisico", "digital", "suscripcion"]


class ProductoSolicitud(ModeloBase):
    nombre: str = Field(min_length=1, max_length=200)
    precio: float = Field(ge=0)
    marca: str = Field(default="Generica", max_length=120)
    categoria: str = Field(default="General", max_length=120)
    tipo: TipoProducto = "normal"
    costo_envio: float | None = Field(default=None, ge=0)
    meses: int | None = Field(default=None, ge=1)

    @field_validator("tipo", mode="before")
    @classmethod
    def normalizar_tipo(cls, valor: object) -> str:
        normalizado = str(valor or "normal").strip().casefold()
        return "normal" if normalizado == "producto" else normalizado

    @model_validator(mode="after")
    def validar_campos_por_tipo(self) -> ProductoSolicitud:
        if self.tipo != "fisico" and self.costo_envio is not None:
            raise ValueError("costo_envio solo aplica a productos físicos")
        if self.tipo != "suscripcion" and self.meses is not None:
            raise ValueError("meses solo aplica a suscripciones")
        return self


class PrecioSolicitud(ModeloBase):
    producto_id: str = Field(min_length=1)
    precio: float = Field(ge=0)


class CsvSolicitud(ModeloBase):
    contenido: str = Field(min_length=1)


class ProductoRespuesta(ModeloBase):
    producto_id: str
    nombre: str
    marca: str
    categoria: str
    tipo: str
    precio: float
    precio_final: float
    costo_envio: float | None = None
    meses: int | None = None


class AlmacenRespuesta(ModeloBase):
    id: int
    name: str
    products: int


class OkRespuesta(ModeloBase):
    ok: bool = True


class ImportacionCsvRespuesta(ModeloBase):
    importados: int
    rechazados: int
    errores: list[str]


__all__ = [
    "AlmacenRespuesta",
    "CsvSolicitud",
    "ImportacionCsvRespuesta",
    "OkRespuesta",
    "PrecioSolicitud",
    "ProductoRespuesta",
    "ProductoSolicitud",
    "TipoProducto",
]
