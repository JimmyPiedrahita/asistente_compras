"""Esquemas de administración."""

from __future__ import annotations

from pydantic import EmailStr, Field

from .base import ModeloBase


class AlmacenSolicitud(ModeloBase):
    nombre: str = Field(min_length=1, max_length=120)


class AlmacenRespuesta(ModeloBase):
    almacen_id: str
    nombre: str
    productos: int
    creado_en: str


class AdminAlmacenSolicitud(ModeloBase):
    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    almacen_id: str = Field(min_length=1)


class CredencialesSolicitud(ModeloBase):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=200)


class UsuarioAdminRespuesta(ModeloBase):
    usuario_id: str
    nombre: str
    email: str
    rol: str
    almacen_id: str | None = None
    almacen_nombre: str = ""
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    activo: bool
    creado_en: str | None = None


class ProductoSolicitud(ModeloBase):
    tipo_producto: str = Field(min_length=1, max_length=100)
    nombre: str = Field(min_length=1, max_length=200)
    marca_variedad: str | None = Field(default=None, max_length=120)
    precio: float = Field(gt=0)
    presentacion: str = Field(min_length=1, max_length=100)


class ProductoActualizacion(ModeloBase):
    tipo_producto: str | None = Field(default=None, min_length=1, max_length=100)
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    marca_variedad: str | None = Field(default=None, max_length=120)
    precio: float | None = Field(default=None, gt=0)
    presentacion: str | None = Field(default=None, min_length=1, max_length=100)


class CsvSolicitud(ModeloBase):
    contenido: str = Field(min_length=1)
    nombre_archivo: str | None = Field(default=None, max_length=255)


class ImportacionRespuesta(ModeloBase):
    importados: int
    errores: list[dict]


class CuponCrearSolicitud(ModeloBase):
    codigo: str = Field(min_length=1, max_length=50)
    porcentaje: float = Field(gt=0, le=100)


class CuponRespuesta(ModeloBase):
    cupon_id: str
    codigo: str
    almacen_id: str
    porcentaje: float
    creado_en: str | None = None


__all__ = [
    "AdminAlmacenSolicitud",
    "AlmacenRespuesta",
    "AlmacenSolicitud",
    "CredencialesSolicitud",
    "CsvSolicitud",
    "CuponCrearSolicitud",
    "CuponRespuesta",
    "ImportacionRespuesta",
    "ProductoActualizacion",
    "ProductoSolicitud",
    "UsuarioAdminRespuesta",
]
