"""Casos de uso de búsqueda y comparación (Strategy)."""

from __future__ import annotations

from typing import Any

from core.errors import NoPermitido, SolicitudInvalida
from models.permisos import COMPARAR

from .contexto import ContextoSesion

MODOS = ("mejor_precio", "catalogo", "global")
LIMITE_CATALOGO = 100


class ControladorBusqueda:
    def __init__(self, contexto: ContextoSesion) -> None:
        self.contexto = contexto

    def ejecutar(
        self,
        modo: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Any:
        modo_norm = str(modo or "mejor_precio").strip().casefold()
        if modo_norm not in MODOS:
            raise SolicitudInvalida("Modo inválido: use mejor_precio, catalogo o global")
        if not self.contexto.autorizar(COMPARAR):
            raise NoPermitido(COMPARAR)

        nombres = list(self.contexto.lista_compras.mostrar())
        limite = LIMITE_CATALOGO if limit is None else int(limit)
        desplazamiento = 0 if offset is None else int(offset)
        if limite < 1:
            raise SolicitudInvalida("limit debe ser mayor o igual a 1")
        if desplazamiento < 0:
            raise SolicitudInvalida("offset no puede ser negativo")

        with self.contexto.gestor_almacenes.candado:
            if modo_norm == "mejor_precio":
                return self.contexto.gestor_almacenes.buscar_mejor_precio(nombres)
            if modo_norm == "catalogo":
                return self.contexto.gestor_almacenes.buscar_catalogo(
                    nombres, limite, desplazamiento
                )
            return self.contexto.gestor_almacenes.buscar_global(nombres)

    def mejor_precio_por_almacen(self) -> Any:
        return self.ejecutar("mejor_precio")

    def catalogo_completo(self) -> Any:
        return self.ejecutar("catalogo")

    def mejor_precio_global(self) -> Any:
        return self.ejecutar("global")


__all__ = ["LIMITE_CATALOGO", "MODOS", "ControladorBusqueda"]
