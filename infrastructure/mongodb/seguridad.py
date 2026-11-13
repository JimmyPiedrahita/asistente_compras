"""Persistencia de roles y usuarios en la base de seguridad de MongoDB.

La colección ``roles`` se sincroniza al arrancar desde
``models.permisos.MATRIZ_PERMISOS``; la colección ``usuarios`` guarda las
identidades y el almacén asignado a cada proveedor.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from core.errors import Conflicto, NoEncontrado, ServicioNoDisponible, SolicitudInvalida
from core.logging import obtener_logger
from models.permisos import ROLES
from models.seguridad import SIN_CAMBIO, Rol, Usuario, roles_canonicos
from models.texto import normalizar_texto

from .cliente import ClienteMongo

logger = obtener_logger("asistente_compras.seguridad")


class MongoSeguridadRepository:
    """Implementación MongoDB del contrato ``SeguridadRepository``."""

    def __init__(
        self,
        uri: str,
        *,
        base_datos: str = "seguridad",
        timeout_ms: int = 5000,
        cliente: ClienteMongo | None = None,
    ) -> None:
        self._cliente = cliente or ClienteMongo(uri, timeout_ms=timeout_ms)
        self._propio = cliente is None
        self._base = self._cliente.base(base_datos)
        self._roles = self._base["roles"]
        self._usuarios = self._base["usuarios"]

    # Roles -------------------------------------------------------------
    def inicializar(self) -> None:
        try:
            self._roles.create_index("nombre", unique=True)
            self._usuarios.create_index("nombre_normalizado", unique=True)
            self._usuarios.create_index([("rol", ASCENDING), ("almacen_id", ASCENDING)])
            for rol in roles_canonicos():
                self._roles.update_one(
                    {"nombre": rol.nombre},
                    {
                        "$set": {
                            "nombre": rol.nombre,
                            "descripcion": rol.descripcion,
                            "permisos": list(rol.permisos),
                            "sistema": True,
                        }
                    },
                    upsert=True,
                )
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible(
                "No se pudo inicializar la colección de seguridad en MongoDB"
            ) from error

    def listar_roles(self) -> list[Rol]:
        try:
            documentos = list(self._roles.find({}))
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible("No se pudieron leer los roles") from error
        roles = [self._documento_a_rol(documento) for documento in documentos]
        orden = {nombre: indice for indice, nombre in enumerate(ROLES)}
        roles.sort(key=lambda rol: (orden.get(rol.nombre, len(orden)), rol.nombre))
        return roles

    def obtener_rol(self, nombre: str) -> Rol | None:
        nombre = str(nombre or "").strip().upper()
        if not nombre:
            return None
        try:
            documento = self._roles.find_one({"nombre": nombre})
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible("No se pudo leer el rol") from error
        return self._documento_a_rol(documento) if documento else None

    # Usuarios ----------------------------------------------------------
    def listar_usuarios(self) -> list[Usuario]:
        try:
            documentos = list(self._usuarios.find({}))
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible("No se pudieron leer los usuarios") from error
        usuarios = [self._documento_a_usuario(documento) for documento in documentos]
        usuarios.sort(key=lambda usuario: (normalizar_texto(usuario.nombre), usuario.usuario_id))
        return usuarios

    def obtener_usuario(self, usuario_id: str) -> Usuario | None:
        try:
            documento = self._usuarios.find_one({"_id": str(usuario_id)})
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible("No se pudo leer el usuario") from error
        return self._documento_a_usuario(documento) if documento else None

    def buscar_usuario_por_nombre(self, nombre: str) -> Usuario | None:
        buscado = normalizar_texto(nombre)
        if not buscado:
            return None
        try:
            documento = self._usuarios.find_one({"nombre_normalizado": buscado})
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible("No se pudo buscar el usuario") from error
        return self._documento_a_usuario(documento) if documento else None

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
        if self.obtener_rol(rol) is None:
            raise SolicitudInvalida(f"Rol desconocido: {rol or '(vacío)'}")
        documento = {
            "_id": uuid.uuid4().hex,
            "nombre": nombre,
            "nombre_normalizado": normalizar_texto(nombre),
            "rol": rol,
            "almacen_id": int(almacen_id) if almacen_id is not None else None,
            "activo": True,
            "creado_en": datetime.now(timezone.utc),
        }
        try:
            self._usuarios.insert_one(documento)
        except DuplicateKeyError as error:
            raise Conflicto(f"Ya existe un usuario con el nombre {nombre}") from error
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible("No se pudo crear el usuario") from error
        return self._documento_a_usuario(documento)

    def actualizar_usuario(
        self,
        usuario_id: str,
        *,
        rol: str | None = None,
        almacen_id: int | object | None = SIN_CAMBIO,
        activo: bool | None = None,
    ) -> Usuario | None:
        cambios: dict[str, Any] = {}
        if rol is not None:
            nuevo_rol = str(rol).strip().upper()
            if self.obtener_rol(nuevo_rol) is None:
                raise SolicitudInvalida(f"Rol desconocido: {nuevo_rol or '(vacío)'}")
            cambios["rol"] = nuevo_rol
        if almacen_id is not SIN_CAMBIO:
            cambios["almacen_id"] = int(almacen_id) if almacen_id is not None else None
        if activo is not None:
            cambios["activo"] = bool(activo)
        if not cambios:
            return self.obtener_usuario(usuario_id)
        try:
            documento = self._usuarios.find_one_and_update(
                {"_id": str(usuario_id)},
                {"$set": cambios},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible("No se pudo actualizar el usuario") from error
        if documento is None:
            raise NoEncontrado(f"Usuario no encontrado: {usuario_id}")
        return self._documento_a_usuario(documento)

    def close(self) -> None:
        if self._propio:
            self._cliente.close()

    # Conversión --------------------------------------------------------
    @staticmethod
    def _documento_a_rol(documento: dict[str, Any]) -> Rol:
        return Rol(
            nombre=str(documento.get("nombre", "")),
            descripcion=str(documento.get("descripcion", "")),
            permisos=tuple(str(permiso) for permiso in documento.get("permisos", [])),
            sistema=bool(documento.get("sistema", True)),
        )

    @staticmethod
    def _documento_a_usuario(documento: dict[str, Any]) -> Usuario:
        creado = documento.get("creado_en")
        if isinstance(creado, str):
            try:
                creado = datetime.fromisoformat(creado)
            except ValueError:
                creado = None
        return Usuario(
            usuario_id=str(documento.get("_id", "")),
            nombre=str(documento.get("nombre", "")),
            rol=str(documento.get("rol", "")),
            almacen_id=documento.get("almacen_id"),
            activo=bool(documento.get("activo", True)),
            creado_en=creado if isinstance(creado, datetime) else None,
        )


__all__ = ["MongoSeguridadRepository"]
