"""Estrategias del dominio."""

from .busqueda import (
    BusquedaCatalogoStrategy,
    BusquedaMejorPrecioStrategy,
    EstrategiaBusqueda,
    MejorPrecioGlobalStrategy,
)
from .descuento import (
    DescuentoFijo,
    DescuentoPorcentaje,
    EstrategiaDescuento,
    SinDescuento,
)

__all__ = [
    "BusquedaCatalogoStrategy",
    "BusquedaMejorPrecioStrategy",
    "DescuentoFijo",
    "DescuentoPorcentaje",
    "EstrategiaBusqueda",
    "EstrategiaDescuento",
    "MejorPrecioGlobalStrategy",
    "SinDescuento",
]
