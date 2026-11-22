"""Validaciones globales de catálogo usando una conexión de solo lectura."""

from __future__ import annotations

from collections.abc import Iterable

from core.errors import Conflicto
from models.productos import Producto
from models.texto import normalizar_texto

from .global_db import RepositorioValidacion


class ServicioValidacion:
    """Reglas que necesitan ver datos de todos los almacenes.

    - La presentación es la misma para todos los productos de un tipo.
    - El código de un cupón es único en toda la aplicación.
    """

    def __init__(self, repositorio: RepositorioValidacion) -> None:
        self.repo = repositorio

    def presentaciones_del_tipo(
        self,
        tipo_normalizado: str,
        *,
        locales: Iterable[str] | None = None,
        excluir_id: str | None = None,
    ) -> set[str]:
        globales = self.repo.presentaciones_del_tipo(tipo_normalizado, excluir_id=excluir_id)
        if locales:
            globales |= {str(valor) for valor in locales if str(valor).strip()}
        return globales

    def validar_presentacion(
        self,
        producto: Producto,
        *,
        locales: Iterable[str] | None = None,
        excluir_id: str | None = None,
    ) -> None:
        existentes = self.presentaciones_del_tipo(
            producto.tipo_normalizado, locales=locales, excluir_id=excluir_id
        )
        if existentes and producto.presentacion_normalizada not in existentes:
            presentacion = sorted(existentes)[0]
            raise Conflicto(
                "La presentación debe ser la misma para todos los productos del tipo "
                f"'{producto.tipo_producto}'. Presentación estándar: {presentacion}"
            )

    def validar_cupon_unico(self, codigo: str) -> None:
        if self.repo.existe_cupon(normalizar_texto(codigo)):
            raise Conflicto("Ya existe un cupón con ese código")


__all__ = ["ServicioValidacion"]
