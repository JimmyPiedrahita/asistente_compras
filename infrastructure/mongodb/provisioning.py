"""Aprovisionamiento de bases, roles y usuarios nativos por almacén."""

from __future__ import annotations

import uuid
from typing import Any

from pymongo.errors import OperationFailure, PyMongoError

from core.config import Settings
from core.errors import Conflicto, ServicioNoDisponible
from core.logging import obtener_logger
from models.almacenes import Almacen

from .almacen import RepositorioAlmacen
from .conexiones import ConexionesMongo
from .global_db import RepositorioAlmacenes
from .uri import FabricaURIs

logger = obtener_logger("asistente_compras.mongodb.provisioning")

_ROLE_ALMACEN = "rol_almacen"
_ROLE_CATALOGO = "rol_catalogo"
_ROLE_PROYECTOR = "rol_proyector"

# Códigos de MongoDB para "ya existe".
_YA_EXISTE = {51002, 51003, 48}


class ServicioAprovisionamiento:
    def __init__(
        self,
        settings: Settings,
        fabrica: FabricaURIs,
        conexiones: ConexionesMongo,
        repositorio: RepositorioAlmacenes,
    ) -> None:
        self.settings = settings
        self.fabrica = fabrica
        self.conexiones = conexiones
        self.repo = repositorio

    def crear_almacen(self, nombre: str) -> Almacen:
        nombre_limpio = " ".join(str(nombre or "").split())
        if not nombre_limpio:
            raise Conflicto("El nombre del almacén es obligatorio")
        if self.repo.existe_nombre(nombre_limpio):
            raise Conflicto("Ya existe un almacén con ese nombre")

        almacen_id = uuid.uuid4().hex
        db_name = self.fabrica.nombre_base_almacen(nombre_limpio, almacen_id)
        almacen = Almacen(
            almacen_id=almacen_id,
            nombre=nombre_limpio,
            db_name=db_name,
            mongo_user=self.fabrica.usuario_almacen(db_name),
            estado="creando",
        )
        self.repo.crear(almacen)
        try:
            self._provisionar(almacen)
            self._crear_indices(almacen)
            self.repo.actualizar_estado(almacen.almacen_id, "activo")
            almacen.estado = "activo"
        except Exception:
            try:
                self.repo.actualizar_estado(almacen.almacen_id, "error")
            except Exception:  # pragma: no cover - diagnóstico defensivo
                logger.exception("No se pudo marcar el almacén %s como error", almacen_id)
            raise
        logger.info(
            "Almacén aprovisionado: %s (base %s, usuario %s)",
            almacen.nombre,
            almacen.db_name,
            almacen.mongo_user,
        )
        return almacen

    # Aprovisionamiento nativo ------------------------------------------
    def _provisionar(self, almacen: Almacen) -> None:
        if self.settings.modo_pruebas:
            return
        try:
            cliente = self.conexiones.cliente(self.fabrica.uri_provisioner())
            admin = cliente.base("admin")
            base_almacen = cliente.base(almacen.db_name)
            self._crear_rol_almacen(base_almacen, almacen.db_name)
            self._crear_usuario(admin, almacen)
            self._otorgar_privilegios_servicio(admin, almacen.db_name)
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo aprovisionar el almacén en MongoDB") from error

    def asegurar_privilegios_catalogo(self, almacen: Almacen) -> None:
        """Repara los permisos del listener para almacenes existentes."""
        if self.settings.modo_pruebas:
            return
        if not almacen.db_name:
            return
        try:
            cliente = self.conexiones.cliente(self.fabrica.uri_provisioner())
            admin = cliente.base("admin")
            catalogo = [
                {
                    "resource": {"db": almacen.db_name, "collection": "productos"},
                    "actions": ["find", "changeStream"],
                },
                {
                    "resource": {"db": almacen.db_name, "collection": "cupones"},
                    "actions": ["find", "changeStream"],
                },
            ]
            try:
                admin.command("grantPrivilegesToRole", _ROLE_CATALOGO, privileges=catalogo)
            except OperationFailure as error:
                if error.code not in _YA_EXISTE:
                    raise
        except PyMongoError as error:
            raise ServicioNoDisponible(
                "No se pudieron reparar los permisos del catálogo"
            ) from error

    def asegurar_privilegios_compras(self, almacen: Almacen) -> None:
        """Repara los permisos del proyector para almacenes existentes."""
        if self.settings.modo_pruebas:
            return
        if not almacen.db_name:
            return
        try:
            cliente = self.conexiones.cliente(self.fabrica.uri_provisioner())
            admin = cliente.base("admin")
            proyector = [
                {
                    "resource": {"db": almacen.db_name, "collection": "compras_almacen"},
                    "actions": ["find", "insert", "update", "remove"],
                }
            ]
            try:
                admin.command("grantPrivilegesToRole", _ROLE_PROYECTOR, privileges=proyector)
            except OperationFailure as error:
                if error.code not in _YA_EXISTE:
                    raise
        except PyMongoError as error:
            raise ServicioNoDisponible(
                "No se pudieron reparar los permisos de compras"
            ) from error

    def _crear_rol_almacen(self, base: Any, db_name: str) -> None:
        privilegios = [
            {
                "resource": {"db": db_name, "collection": "productos"},
                "actions": ["find", "insert", "update", "remove", "createIndex"],
            },
            {
                "resource": {"db": db_name, "collection": "cupones"},
                "actions": ["find", "insert", "update", "remove", "createIndex"],
            },
            {
                "resource": {"db": db_name, "collection": "compras_almacen"},
                "actions": ["find"],
            },
        ]
        try:
            base.command("createRole", _ROLE_ALMACEN, privileges=privilegios, roles=[])
        except OperationFailure as error:
            if error.code not in _YA_EXISTE:
                raise
            base.command("updateRole", _ROLE_ALMACEN, privileges=privilegios, roles=[])

    def _crear_usuario(self, admin: Any, almacen: Almacen) -> None:
        roles = [{"role": _ROLE_ALMACEN, "db": almacen.db_name}]
        password = self.fabrica.password_almacen(almacen.almacen_id)
        try:
            admin.command("createUser", almacen.mongo_user, pwd=password, roles=roles)
        except OperationFailure as error:
            if error.code not in _YA_EXISTE:
                raise
            admin.command("updateUser", almacen.mongo_user, pwd=password, roles=roles)

    def _otorgar_privilegios_servicio(self, admin: Any, db_name: str) -> None:
        catalogo = [
            {
                "resource": {"db": db_name, "collection": "productos"},
                "actions": ["find", "changeStream"],
            },
            {
                "resource": {"db": db_name, "collection": "cupones"},
                "actions": ["find", "changeStream"],
            },
        ]
        proyector = [
            {
                "resource": {"db": db_name, "collection": "compras_almacen"},
                "actions": ["find", "insert", "update", "remove"],
            }
        ]
        for rol, privilegios in ((_ROLE_CATALOGO, catalogo), (_ROLE_PROYECTOR, proyector)):
            try:
                admin.command("grantPrivilegesToRole", rol, privileges=privilegios)
            except OperationFailure as error:
                # Si el privilegio ya existe, el aprovisionamiento es idempotente.
                if error.code in _YA_EXISTE:
                    continue
                logger.warning(
                    "No se pudieron ampliar los privilegios de %s para %s: %s",
                    rol,
                    db_name,
                    error,
                )

    def _crear_indices(self, almacen: Almacen) -> None:
        try:
            cliente = self.conexiones.cliente(self.fabrica.uri_provisioner())
            base = cliente.base(almacen.db_name)
            RepositorioAlmacen(base, almacen.almacen_id).inicializar()
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudieron crear los índices del almacén") from error


__all__ = ["ServicioAprovisionamiento"]
