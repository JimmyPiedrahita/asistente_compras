"""Estrategias de descuento (patrón Strategy)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EstrategiaDescuento(ABC):
    @abstractmethod
    def calcular(self, monto: float) -> float:
        raise NotImplementedError


class SinDescuento(EstrategiaDescuento):
    def calcular(self, monto: float) -> float:
        return monto


class DescuentoPorcentaje(EstrategiaDescuento):
    def __init__(self, porcentaje: float) -> None:
        self.porcentaje = float(porcentaje)
        if not 0 <= self.porcentaje <= 100:
            raise ValueError("El porcentaje debe estar entre 0 y 100")

    def calcular(self, monto: float) -> float:
        return monto * (1 - self.porcentaje / 100.0)


class DescuentoFijo(EstrategiaDescuento):
    def __init__(self, monto_descuento: float) -> None:
        self.monto_descuento = float(monto_descuento)
        if self.monto_descuento < 0:
            raise ValueError("El monto del descuento no puede ser negativo")

    def calcular(self, monto: float) -> float:
        return max(0.0, monto - self.monto_descuento)


__all__ = [
    "DescuentoFijo",
    "DescuentoPorcentaje",
    "EstrategiaDescuento",
    "SinDescuento",
]
