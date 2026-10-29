"""Casos de uso del carrito y descuentos."""

from __future__ import annotations

import math
from typing import Any

from core.results import Resultado
from models.estrategias import DescuentoFijo, DescuentoPorcentaje, SinDescuento
from models.permisos import AGREGAR_PRODUCTO, APLICAR_DESCUENTO, ELIMINAR_PRODUCTO

from .contexto import ContextoSesion


class ControladorCarrito:
    def __init__(self, contexto: ContextoSesion) -> None:
        self.contexto = contexto
        self._descuento_actual = "Sin descuento"

    def agregar_producto(self, producto: Any) -> Resultado:
        if not self.contexto.autorizar(AGREGAR_PRODUCTO):
            return Resultado.DENEGADO
        self.contexto.carrito.agregar_producto(producto.clonar())
        return Resultado.OK

    def agregar_seleccion(self, producto: Any, id_almacen: int) -> Resultado:
        if not self.contexto.autorizar(AGREGAR_PRODUCTO):
            return Resultado.DENEGADO
        candidato = self.contexto.gestor_almacenes.obtener_producto(
            id_almacen, producto.producto_id
        )
        if candidato is None:
            self.contexto.registrar(
                "CLIENTE", "Selección no válida", "El producto ya no está en el almacén"
            )
            return Resultado.NO_ENCONTRADO
        self.contexto.carrito.agregar_producto(candidato.clonar())
        return Resultado.OK

    def agregar_por_id(self, id_almacen: int, producto_id: str) -> Resultado:
        if not self.contexto.autorizar(AGREGAR_PRODUCTO):
            return Resultado.DENEGADO
        producto = self.contexto.gestor_almacenes.obtener_producto(id_almacen, producto_id)
        if producto is None:
            return Resultado.NO_ENCONTRADO
        self.contexto.carrito.agregar_producto(producto.clonar())
        return Resultado.OK

    def quitar(self, indice: int) -> Resultado:
        if not self.contexto.autorizar(ELIMINAR_PRODUCTO):
            return Resultado.DENEGADO
        if not self.contexto.carrito.eliminar_producto(indice):
            return Resultado.NO_ENCONTRADO
        return Resultado.OK

    def vaciar(self) -> Resultado:
        if not self.contexto.autorizar(ELIMINAR_PRODUCTO):
            return Resultado.DENEGADO
        self.contexto.carrito.vaciar()
        return Resultado.OK

    def establecer_descuento(self, opcion: str, valor: Any = None) -> Resultado:
        if not self.contexto.autorizar(APLICAR_DESCUENTO):
            return Resultado.DENEGADO

        opcion_norm = str(opcion or "").strip().casefold()
        try:
            if opcion_norm in ("sin", "sin descuento", "0", "1", ""):
                estrategia = SinDescuento()
                etiqueta = "Sin descuento"
            elif opcion_norm in ("porcentaje", "porcentaje (%)", "2"):
                porcentaje = float(valor)
                if not math.isfinite(porcentaje) or not 0 <= porcentaje <= 100:
                    return Resultado.INVALIDO
                estrategia = DescuentoPorcentaje(porcentaje)
                etiqueta = f"{porcentaje:g}%"
            elif opcion_norm in ("fijo", "monto fijo", "monto fijo ($)", "3"):
                monto = float(valor)
                if not math.isfinite(monto) or monto < 0:
                    return Resultado.INVALIDO
                estrategia = DescuentoFijo(monto)
                etiqueta = f"-${monto:.2f}"
            else:
                return Resultado.INVALIDO
        except (TypeError, ValueError, OverflowError):
            return Resultado.INVALIDO

        self.contexto.carrito.establecer_estrategia_descuento(estrategia)
        self._descuento_actual = etiqueta
        self.contexto.registrar("CLIENTE", "Descuento aplicado", etiqueta)
        return Resultado.OK

    def limpiar_descuento(self) -> None:
        self.contexto.carrito.establecer_estrategia_descuento(None)
        self._descuento_actual = "Sin descuento"

    def resumen(self) -> dict[str, Any]:
        return {
            "productos": self.contexto.carrito.obtener_productos(),
            "subtotal": self.contexto.carrito.calcular_subtotal(),
            "total": self.contexto.carrito.calcular_total(),
            "descuento": self._descuento_actual,
        }

    @property
    def descuento_actual(self) -> str:
        return self._descuento_actual


__all__ = ["ControladorCarrito"]
