"""Caso de uso de sesión, autenticación y permisos.

La identidad y los permisos ya no viven solo en memoria: el controlador
consulta el repositorio de seguridad y conserva una copia de los permisos
efectivos para autorizar cada operación durante la sesión.
"""

from __future__ import annotations

import secrets

from core.errors import ServicioNoDisponible
from core.logging import obtener_logger
from core.observer import Observador
from models.permisos import (
    ADMIN,
    CLIENTE,
    INVITADO,
    LOGIN_ADMIN,
    PROVEEDOR,
    permisos_de,
)
from models.seguridad import SeguridadEnMemoria, Usuario

logger = obtener_logger("asistente_compras.sesion")


class ControladorSesion:
    def __init__(
        self,
        clave_admin: str,
        seguridad: object | None = None,
    ) -> None:
        self._clave_admin = str(clave_admin or "")
        self._seguridad = seguridad if seguridad is not None else SeguridadEnMemoria()
        self._usuario_actual: str | None = None
        self._usuario_id: str | None = None
        self._rol = INVITADO
        self._permisos: set[str] = set(permisos_de(INVITADO))
        self._almacen_id: int | None = None

    # Registro y login --------------------------------------------------
    def registrar_usuario(self, nombre: str) -> bool:
        """Registra un cliente si el nombre está libre.

        Se mantiene por compatibilidad con la API anterior. El login de cliente
        es idempotente: si el usuario ya existe como CLIENTE se reutiliza.
        """
        nombre = " ".join(str(nombre or "").split())
        if not nombre:
            return False
        try:
            existente = self._seguridad.buscar_usuario_por_nombre(nombre)
        except ServicioNoDisponible:
            raise
        if existente is not None:
            return False
        self._seguridad.crear_usuario(nombre, CLIENTE)
        logger.info("[SISTEMA] Usuario registrado -> %s", nombre)
        return True

    def iniciar_sesion(self, nombre: str) -> bool:
        """Inicia sesión como CLIENTE; crea la identidad si no existe."""
        nombre = " ".join(str(nombre or "").split())
        if not nombre:
            return False
        usuario = self._seguridad.buscar_usuario_por_nombre(nombre)
        if usuario is None:
            try:
                usuario = self._seguridad.crear_usuario(nombre, CLIENTE)
            except Exception:
                logger.exception("[SISTEMA] No se pudo registrar al cliente %s", nombre)
                return False
        if not usuario.activo or usuario.rol != CLIENTE:
            logger.warning(
                "[SISTEMA] Login de cliente rechazado -> %s (rol=%s, activo=%s)",
                nombre,
                usuario.rol,
                usuario.activo,
            )
            return False
        self._aplicar_identidad(usuario)
        logger.info("[SISTEMA] Inicio de sesión -> %s (CLIENTE)", nombre)
        return True

    def iniciar_sesion_proveedor(self, nombre: str) -> bool:
        """Inicia sesión como PROVEEDOR previamente creado por un ADMIN."""
        usuario = self._seguridad.buscar_usuario_por_nombre(nombre)
        if usuario is None:
            logger.warning("[PROVEEDOR] Login rechazado: usuario inexistente -> %s", nombre)
            return False
        if usuario.rol != PROVEEDOR:
            logger.warning("[PROVEEDOR] Login rechazado: rol incorrecto -> %s", usuario.rol)
            return False
        if not usuario.activo:
            logger.warning("[PROVEEDOR] Login rechazado: usuario inactivo -> %s", nombre)
            return False
        if usuario.almacen_id is None:
            logger.warning("[PROVEEDOR] Login rechazado: sin almacén asignado -> %s", nombre)
            return False
        self._aplicar_identidad(usuario)
        logger.info(
            "[PROVEEDOR] Inicio de sesión -> %s (almacén %s)",
            usuario.nombre,
            usuario.almacen_id,
        )
        return True

    def cerrar_sesion(self) -> None:
        if self._usuario_actual:
            logger.info("[SISTEMA] Cierre de sesión -> %s", self._usuario_actual)
        self._usuario_actual = None
        self._usuario_id = None
        self._rol = INVITADO
        self._permisos = set(permisos_de(INVITADO))
        self._almacen_id = None

    def login_admin(self, clave: str) -> bool:
        if not self._clave_admin:
            logger.error("ADMIN_CLAVE no está configurada")
            return False
        if not secrets.compare_digest(str(clave or ""), self._clave_admin):
            logger.warning("[ADMIN] Intento de login fallido -> DENEGADO")
            return False
        self._usuario_actual = "ADMIN"
        self._usuario_id = "ADMIN"
        self._rol = ADMIN
        self._almacen_id = None
        self._cargar_permisos(ADMIN)
        logger.info("[ADMIN] Inicio de sesión -> CONCEDIDO")
        return True

    # Permisos ----------------------------------------------------------
    def autorizar(self, permiso: str, vista: Observador) -> bool:
        permitido = self.tiene_permiso(permiso)
        if not permitido:
            vista.notificar_denegado(permiso)
        return permitido

    def tiene_permiso(self, permiso: str) -> bool:
        permitido = permiso in self._permisos
        if permitido:
            logger.debug("Permiso '%s' concedido para %s", permiso, self._rol)
        else:
            logger.warning("Permiso '%s' denegado para %s", permiso, self._rol)
        return permitido

    def _aplicar_identidad(self, usuario: Usuario) -> None:
        self._usuario_actual = usuario.nombre
        self._usuario_id = usuario.usuario_id
        self._rol = usuario.rol
        self._almacen_id = usuario.almacen_id
        self._cargar_permisos(usuario.rol)

    def _cargar_permisos(self, rol: str) -> None:
        rol_db = self._seguridad.obtener_rol(rol)
        self._permisos = set(rol_db.permisos if rol_db is not None else permisos_de(rol))

    # Propiedades -------------------------------------------------------
    @property
    def usuario_actual(self) -> str | None:
        return self._usuario_actual

    @property
    def usuario_id(self) -> str | None:
        return self._usuario_id

    @property
    def rol(self) -> str:
        return self._rol

    @property
    def permisos(self) -> tuple[str, ...]:
        return tuple(sorted(self._permisos))

    @property
    def almacen_id(self) -> int | None:
        return self._almacen_id

    @property
    def es_admin(self) -> bool:
        return self._rol == ADMIN

    @property
    def es_proveedor(self) -> bool:
        return self._rol == PROVEEDOR

    @property
    def permiso_login_admin(self) -> str:
        return LOGIN_ADMIN


__all__ = ["ControladorSesion"]
