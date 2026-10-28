"""Caso de uso de sesión, autenticación y permisos."""

from __future__ import annotations

import secrets

from core.logging import obtener_logger
from core.observer import Observador
from models.permisos import ADMIN, CLIENTE, INVITADO, LOGIN_ADMIN, tiene_permiso

logger = obtener_logger("asistente_compras.sesion")


class ControladorSesion:
    def __init__(self, clave_admin: str) -> None:
        self._clave_admin = str(clave_admin or "")
        self._usuarios: list[str] = []
        self._usuario_actual: str | None = None
        self._rol = INVITADO

    def registrar_usuario(self, nombre: str) -> bool:
        nombre = (nombre or "").strip()
        if not nombre or nombre in self._usuarios:
            return False
        self._usuarios.append(nombre)
        logger.info("[SISTEMA] Usuario registrado -> %s", nombre)
        return True

    def iniciar_sesion(self, nombre: str) -> bool:
        nombre = (nombre or "").strip()
        if nombre not in self._usuarios:
            logger.warning("[SISTEMA] Inicio de sesión fallido -> %s", nombre or "(vacío)")
            return False
        self._usuario_actual = nombre
        self._rol = CLIENTE
        logger.info("[SISTEMA] Inicio de sesión -> %s (CLIENTE)", nombre)
        return True

    def cerrar_sesion(self) -> None:
        if self._usuario_actual:
            logger.info("[SISTEMA] Cierre de sesión -> %s", self._usuario_actual)
        self._usuario_actual = None
        self._rol = INVITADO

    def login_admin(self, clave: str) -> bool:
        if not self._clave_admin:
            logger.error("ADMIN_CLAVE no está configurada")
            return False
        if not secrets.compare_digest(str(clave or ""), self._clave_admin):
            logger.warning("[ADMIN] Intento de login fallido -> DENEGADO")
            return False
        self._usuario_actual = "ADMIN"
        self._rol = ADMIN
        logger.info("[ADMIN] Inicio de sesión -> CONCEDIDO")
        return True

    def autorizar(self, permiso: str, vista: Observador) -> bool:
        permitido = tiene_permiso(self._rol, permiso)
        if not permitido:
            vista.notificar_denegado(permiso)
        return permitido

    def tiene_permiso(self, permiso: str) -> bool:
        return tiene_permiso(self._rol, permiso)

    @property
    def usuario_actual(self) -> str | None:
        return self._usuario_actual

    @property
    def rol(self) -> str:
        return self._rol

    @property
    def permiso_login_admin(self) -> str:
        return LOGIN_ADMIN


__all__ = ["ControladorSesion"]
