"""Esquemas de autenticación."""

from __future__ import annotations

from pydantic import EmailStr, Field

from .base import ModeloBase


class LoginSolicitud(ModeloBase):
    email: EmailStr
    password: str = Field(min_length=1)


class RegistroClienteSolicitud(ModeloBase):
    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    password_confirmacion: str = Field(min_length=6, max_length=200)
    telefono: str = Field(min_length=1, max_length=30)
    direccion: str = Field(min_length=1, max_length=300)
    ciudad: str = Field(min_length=1, max_length=120)
    autoriza_datos: bool


class SesionRespuesta(ModeloBase):
    session_id: str
    usuario_id: str
    usuario: str
    email: str
    rol: str
    almacen_id: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None


__all__ = ["LoginSolicitud", "RegistroClienteSolicitud", "SesionRespuesta"]
