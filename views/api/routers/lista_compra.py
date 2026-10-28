"""Endpoints de la lista de compras."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from controllers.compras import ControladorCompras
from models.permisos import CREAR_LISTA, ELIMINAR_PRODUCTO

from ..dependencies import obtener_controlador
from ..schemas import ListaProductoSolicitud, ListaRespuesta
from .comun import verificar_resultado

router = APIRouter(tags=["Lista de compras"])


@router.get("/sessions/{token}/shopping-list", response_model=ListaRespuesta)
def obtener_lista(controlador: ControladorCompras = Depends(obtener_controlador)):
    return {"lista": controlador.obtener_compras_usuario()}


@router.post("/sessions/{token}/shopping-list", response_model=ListaRespuesta)
def agregar_a_lista(
    datos: ListaProductoSolicitud,
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    resultado = controlador.agregar_producto_usuario(datos.nombre)
    verificar_resultado(
        resultado,
        permiso=CREAR_LISTA,
        duplicado="El producto ya está en la lista",
    )
    return {"lista": controlador.obtener_compras_usuario()}


@router.delete("/sessions/{token}/shopping-list/{nombre}", response_model=ListaRespuesta)
def eliminar_de_lista(nombre: str, controlador: ControladorCompras = Depends(obtener_controlador)):
    resultado = controlador.eliminar_producto_usuario(nombre)
    verificar_resultado(
        resultado,
        permiso=ELIMINAR_PRODUCTO,
        no_encontrado="Producto no encontrado en la lista",
    )
    return {"lista": controlador.obtener_compras_usuario()}


__all__ = ["router"]
