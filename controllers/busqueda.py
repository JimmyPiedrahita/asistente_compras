"""Casos de uso de búsqueda y comparación (Strategy)."""

from __future__ import annotations

from typing import Any

from core.errors import NoPermitido, SolicitudInvalida
from models.estrategias import (
    BusquedaCatalogoStrategy,
    BusquedaMejorPrecioStrategy,
    MejorPrecioGlobalStrategy,
)
from models.permisos import COMPARAR

from .contexto import ContextoSesion

MODOS = ("mejor_precio", "catalogo", "global")


class ControladorBusqueda:
    def __init__(self, contexto: ContextoSesion) -> None:
        self.contexto = contexto
        self.mejor_precio = BusquedaMejorPrecioStrategy()
        self.catalogo = BusquedaCatalogoStrategy()
        self.global_ = MejorPrecioGlobalStrategy()

    def ejecutar(self, modo: str) -> Any:
        modo_norm = str(modo or "mejor_precio").strip().casefold()
        if modo_norm not in MODOS:
            raise SolicitudInvalida("Modo inválido: use mejor_precio, catalogo o global")
        if not self.contexto.autorizar(COMPARAR):
            raise NoPermitido(COMPARAR)

        with self.contexto.gestor_almacenes.candado:
            if modo_norm == "mejor_precio":
                return self.mejor_precio.buscar(
                    self.contexto.lista_compras,
                    self.contexto.gestor_almacenes,
                )
            if modo_norm == "catalogo":
                return self.catalogo.buscar(
                    self.contexto.lista_compras,
                    self.contexto.gestor_almacenes,
                )
            return self.global_.buscar(
                self.contexto.lista_compras,
                self.contexto.gestor_almacenes,
            )

    def mejor_precio_por_almacen(self) -> Any:
        return self.ejecutar("mejor_precio")

    def catalogo_completo(self) -> Any:
        return self.ejecutar("catalogo")

    def mejor_precio_global(self) -> Any:
        return self.ejecutar("global")


__all__ = ["MODOS", "ControladorBusqueda"]
