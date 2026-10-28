"""Endpoints del carrito y descuentos."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from controllers.compras import ControladorCompras
from models.permisos import AGREGAR_PRODUCTO, APLICAR_DESCUENTO, ELIMINAR_PRODUCTO

from ..dependencies import obtener_controlador
from ..schemas import CarritoProductoSolicitud, DescuentoSolicitud, ResumenCarrito
from ..serializers import resumen_carrito_json
from .comun import verificar_resultado

router = APIRouter(tags=["Carrito"])


def _resumen(controlador: ControladorCompras) -> dict:
    return resumen_carrito_json(controlador.obtener_resumen_carrito())


@router.get(
    "/sessions/{token}/cart",
    response_model=ResumenCarrito,
    response_model_exclude_none=True,
)
def obtener_carrito(controlador: ControladorCompras = Depends(obtener_controlador)):
    return _resumen(controlador)


@router.post(
    "/sessions/{token}/cart/items",
    response_model=ResumenCarrito,
    response_model_exclude_none=True,
)
def agregar_item(
    datos: CarritoProductoSolicitud,
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    resultado = controlador.agregar_producto_carrito_por_id(datos.almacen_id, datos.producto_id)
    verificar_resultado(
        resultado,
        permiso=AGREGAR_PRODUCTO,
        no_encontrado="Producto o almacén no encontrado",
    )
    return _resumen(controlador)


@router.delete(
    "/sessions/{token}/cart/items/{indice}",
    response_model=ResumenCarrito,
    response_model_exclude_none=True,
)
def quitar_item(indice: int, controlador: ControladorCompras = Depends(obtener_controlador)):
    resultado = controlador.quitar_producto_carrito(indice)
    verificar_resultado(
        resultado,
        permiso=ELIMINAR_PRODUCTO,
        no_encontrado="Ítem no encontrado en el carrito",
    )
    return _resumen(controlador)


@router.delete(
    "/sessions/{token}/cart",
    response_model=ResumenCarrito,
    response_model_exclude_none=True,
)
def vaciar_carrito(controlador: ControladorCompras = Depends(obtener_controlador)):
    resultado = controlador.vaciar_carrito()
    verificar_resultado(resultado, permiso=ELIMINAR_PRODUCTO)
    return _resumen(controlador)


@router.post(
    "/sessions/{token}/cart/discount",
    response_model=ResumenCarrito,
    response_model_exclude_none=True,
)
def aplicar_descuento(
    datos: DescuentoSolicitud,
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    resultado = controlador.establecer_descuento(datos.tipo, datos.valor)
    verificar_resultado(
        resultado,
        permiso=APLICAR_DESCUENTO,
        invalido="Descuento inválido",
    )
    return _resumen(controlador)


__all__ = ["router"]
