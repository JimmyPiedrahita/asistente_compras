"""Contexto compartido por los controladores de una sesión."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.observer import Observador
from models.almacenes import GestorAlmacenes
from models.carrito import CarritoCompras
from models.listas import ListaDoblementeEnlazada
from models.permisos import tiene_permiso

from .sesion import ControladorSesion


@dataclass
class ContextoSesion:
    sesion: ControladorSesion
    carrito: CarritoCompras
    lista_compras: ListaDoblementeEnlazada
    gestor_almacenes: GestorAlmacenes
    vista: Observador
    logger: logging.Logger

    def autorizar(self, permiso: str) -> bool:
        permitido = tiene_permiso(self.sesion.rol, permiso)
        if not permitido and hasattr(self.vista, "notificar_denegado"):
            self.vista.notificar_denegado(permiso)
        return permitido

    def registrar(self, etiqueta: str, mensaje: str, detalle: Any = None) -> None:
        self.logger.info("[%s] %s%s", etiqueta, mensaje, f" -> {detalle}" if detalle else "")


__all__ = ["ContextoSesion"]
