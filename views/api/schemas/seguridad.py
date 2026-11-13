"""Esquemas de roles, usuarios y catálogo de permisos."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ModeloBase

RolNombre = Literal["INVITADO", "CLIENTE", "PROVEEDOR", "ADMIN"]


class PermisoRespuesta(ModeloBase):
    codigo: str
    descripcion: str


class RolRespuesta(ModeloBase):
    rol: str
    descripcion: str
    permisos: list[str]
    sistema: bool = True


class CatalogoRolesRespuesta(ModeloBase):
    roles: list[RolRespuesta]
    permisos: list[PermisoRespuesta]


class ProveedorSesion(ModeloBase):
    nombre: str = Field(min_length=1, max_length=120)


class UsuarioRespuesta(ModeloBase):
    usuario_id: str
    nombre: str
    rol: str
    almacen_id: int | None = None
    activo: bool
    creado_en: str | None = None


class ProveedorSolicitud(ModeloBase):
    nombre: str = Field(min_length=1, max_length=120)
    almacen_id: int = Field(ge=1)


class UsuarioActualizacion(ModeloBase):
    """PATCH parcial: solo se aplican los campos enviados."""

    rol: RolNombre | None = None
    almacen_id: int | None = Field(default=None, ge=1)
    activo: bool | None = None


__all__ = [
    "CatalogoRolesRespuesta",
    "PermisoRespuesta",
    "ProveedorSesion",
    "ProveedorSolicitud",
    "RolNombre",
    "RolRespuesta",
    "UsuarioActualizacion",
    "UsuarioRespuesta",
]
