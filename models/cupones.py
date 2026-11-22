"""Cupones de descuento por almacén."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .texto import normalizar_texto


def validar_porcentaje(porcentaje: Any) -> float:
    try:
        valor = float(porcentaje)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("El porcentaje debe ser numérico") from error
    if valor <= 0 or valor > 100:
        raise ValueError("El porcentaje debe ser mayor que 0 y menor o igual a 100")
    redondeado = round(valor, 2)
    if redondeado <= 0:
        raise ValueError("El porcentaje debe ser mayor que 0 y menor o igual a 100")
    return redondeado


@dataclass
class Cupon:
    cupon_id: str
    codigo: str
    almacen_id: str
    porcentaje: float
    creado_en: datetime | None = None

    @property
    def codigo_normalizado(self) -> str:
        return normalizar_texto(self.codigo)

    def publico(self) -> dict[str, Any]:
        return {
            "cupon_id": self.cupon_id,
            "codigo": self.codigo,
            "almacen_id": self.almacen_id,
            "porcentaje": self.porcentaje,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }


__all__ = ["Cupon", "validar_porcentaje"]
