"""Contexto compartido por los controladores de una sesión."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.errors import NoPermitido
from core.observer import Observador
from models.almacenes import GestorAlmacenes
from models.carrito import CarritoCompras
from models.listas import ListaDoblementeEnlazada
from models.permisos import PERMISOS, PROVEEDOR

from .sesion import ControladorSesion


@dataclass
class ContextoSesion:
    sesion: ControladorSesion
    carrito: CarritoCompras
    lista_compras: ListaDoblementeEnlazada
    gestor_almacenes: GestorAlmacenes
    vista: Observador
    logger: logging.Logger
    ultimo_denegado: str | None = None

    def autorizar(self, permiso: str) -> bool:
        self.ultimo_denegado = None
        permitido = self.sesion.tiene_permiso(permiso)
        if not permitido and hasattr(self.vista, "notificar_denegado"):
            self.vista.notificar_denegado(permiso)
        return permitido

    def error_permiso(self, permiso: str, *, extra: str | None = None) -> NoPermitido:
        descripcion = PERMISOS.get(permiso, permiso)
        if extra:
            descripcion = f"{descripcion} ({extra})"
        return NoPermitido(descripcion, rol=self.sesion.rol)

    def autorizar_almacen(self, id_almacen: int, permiso: str) -> bool:
        """Autoriza un permiso y, para proveedores, limita el almacén asignado."""
        if not self.autorizar(permiso):
            return False
        if self.sesion.rol == PROVEEDOR:
            asignado = self.sesion.almacen_id
            if asignado is None or int(id_almacen) != int(asignado):
                self.logger.warning(
                    "Proveedor %s intentó operar sobre almacén %s (asignado: %s)",
                    self.sesion.usuario_actual,
                    id_almacen,
                    asignado,
                )
                if hasattr(self.vista, "notificar_denegado"):
                    self.vista.notificar_denegado(f"{permiso}:almacen_{id_almacen}")
                self.ultimo_denegado = (
                    f"solo puedes operar el almacén {asignado}; "
                    f"la operación apuntó al almacén {id_almacen}"
                )
                return False
        return True

    def registrar(self, etiqueta: str, mensaje: str, detalle: Any = None) -> None:
        self.logger.info("[%s] %s%s", etiqueta, mensaje, f" -> {detalle}" if detalle else "")


__all__ = ["ContextoSesion"]
