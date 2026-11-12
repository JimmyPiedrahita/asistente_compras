"""Entidades de seguridad (roles y usuarios) y repositorio en memoria.

El repositorio en memoria sirve como implementación de referencia para pruebas
y para ejecutar los controladores sin MongoDB. El repositorio real replica la
misma semántica en ``infrastructure.mongodb.seguridad``.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.errors import Conflicto, SolicitudInvalida
from models.permisos import (
    DESCRIPCION_ROLES,
    MATRIZ_PERMISOS,
    ROLES,
    permisos_de,
)
from models.texto import normalizar_texto

SIN_CAMBIO: object = object()


@dataclass(frozen=True)
class Rol:
    """Rol persistido con su descripción y permisos efectivos."""

    nombre: str
    descripcion: str
    permisos: tuple[str, ...]
    sistema: bool = True

    def json(self) -> dict[str, Any]:
        return {
            "rol": self.nombre,
            "descripcion": self.descripcion,
            "permisos": list(self.permisos),
            "sistema": self.sistema,
        }


@dataclass
class Usuario:
    """Usuario persistido. ``almacen_id`` solo aplica a proveedores."""

    usuario_id: str
    nombre: str
    rol: str
    almacen_id: int | None = None
    activo: bool = True
    creado_en: datetime | None = field(default_factory=lambda: datetime.now(timezone.utc))

    def json(self) -> dict[str, Any]:
        return {
            "usuario_id": self.usuario_id,
            "nombre": self.nombre,
            "rol": self.rol,
            "almacen_id": self.almacen_id,
            "activo": self.activo,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }


def rol_canonico(nombre: str) -> Rol | None:
    """Construye el rol desde la matriz canónica si existe."""
    nombre = str(nombre or "").strip().upper()
    if nombre not in MATRIZ_PERMISOS:
        return None
    return Rol(
        nombre=nombre,
        descripcion=DESCRIPCION_ROLES.get(nombre, ""),
        permisos=permisos_de(nombre),
        sistema=True,
    )


def roles_canonicos() -> list[Rol]:
    return [rol for nombre in ROLES if (rol := rol_canonico(nombre)) is not None]


class SeguridadEnMemoria:
    """Repositorio de seguridad en memoria, seguro para concurrencia."""

    def __init__(self) -> None:
        self._candado = threading.RLock()
        self._roles: dict[str, Rol] = {}
        self._usuarios: dict[str, Usuario] = {}
        self.inicializar()

    # Roles -------------------------------------------------------------
    def inicializar(self) -> None:
        with self._candado:
            self._roles = {rol.nombre: rol for rol in roles_canonicos()}

    def listar_roles(self) -> list[Rol]:
        with self._candado:
            return [self._roles[nombre] for nombre in ROLES if nombre in self._roles]

    def obtener_rol(self, nombre: str) -> Rol | None:
        with self._candado:
            return self._roles.get(str(nombre or "").strip().upper())

    # Usuarios ----------------------------------------------------------
    def listar_usuarios(self) -> list[Usuario]:
        with self._candado:
            return sorted(
                self._usuarios.values(),
                key=lambda usuario: (normalizar_texto(usuario.nombre), usuario.usuario_id),
            )

    def obtener_usuario(self, usuario_id: str) -> Usuario | None:
        with self._candado:
            return self._usuarios.get(str(usuario_id))

    def buscar_usuario_por_nombre(self, nombre: str) -> Usuario | None:
        buscado = normalizar_texto(nombre)
        with self._candado:
            for usuario in self._usuarios.values():
                if normalizar_texto(usuario.nombre) == buscado:
                    return usuario
        return None

    def crear_usuario(
        self,
        nombre: str,
        rol: str,
        almacen_id: int | None = None,
    ) -> Usuario:
        nombre = " ".join(str(nombre or "").split())
        if not nombre:
            raise SolicitudInvalida("El nombre del usuario no puede estar vacío")
        rol = str(rol or "").strip().upper()
        with self._candado:
            if rol not in self._roles:
                raise SolicitudInvalida(f"Rol desconocido: {rol or '(vacío)'}")
            if self.buscar_usuario_por_nombre(nombre) is not None:
                raise Conflicto(f"Ya existe un usuario con el nombre {nombre}")
            usuario = Usuario(
                usuario_id=uuid.uuid4().hex,
                nombre=nombre,
                rol=rol,
                almacen_id=int(almacen_id) if almacen_id is not None else None,
            )
            self._usuarios[usuario.usuario_id] = usuario
            return usuario

    def actualizar_usuario(
        self,
        usuario_id: str,
        *,
        rol: str | None = None,
        almacen_id: int | object | None = SIN_CAMBIO,
        activo: bool | None = None,
    ) -> Usuario | None:
        with self._candado:
            usuario = self._usuarios.get(str(usuario_id))
            if usuario is None:
                return None
            if rol is not None:
                nuevo_rol = str(rol).strip().upper()
                if nuevo_rol not in self._roles:
                    raise SolicitudInvalida(f"Rol desconocido: {nuevo_rol or '(vacío)'}")
                usuario.rol = nuevo_rol
            if almacen_id is not SIN_CAMBIO:
                usuario.almacen_id = int(almacen_id) if almacen_id is not None else None
            if activo is not None:
                usuario.activo = bool(activo)
            return usuario

    def close(self) -> None:
        return None


__all__ = [
    "SIN_CAMBIO",
    "Rol",
    "SeguridadEnMemoria",
    "Usuario",
    "rol_canonico",
    "roles_canonicos",
]
