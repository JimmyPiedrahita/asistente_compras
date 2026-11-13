"""Endpoints del cliente: lista, búsqueda, carrito y compra simulada."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from controllers.carrito import ControladorCarrito
from controllers.catalogo import ControladorCatalogo
from controllers.compras import ControladorCompras
from controllers.sesiones import Sesion

from ..dependencies import (
    obtener_carrito,
    obtener_catalogo,
    obtener_compras,
    requerir_cliente,
)
from ..schemas import (
    BusquedaRespuesta,
    BusquedaSolicitud,
    CantidadSolicitud,
    CarritoItemSolicitud,
    CheckoutSolicitud,
    CompraRespuesta,
    CuponSolicitud,
    ListaItemSolicitud,
    ListaRespuesta,
)

router = APIRouter(tags=["Cliente"])


# Lista de compras ------------------------------------------------------
@router.get("/shopping-list", response_model=ListaRespuesta)
def obtener_lista(sesion: Sesion = Depends(requerir_cliente)) -> dict:
    return {"lista": list(sesion.lista)}


@router.post("/shopping-list", response_model=ListaRespuesta)
def agregar_a_lista(
    datos: ListaItemSolicitud,
    sesion: Sesion = Depends(requerir_cliente),
    catalogo: ControladorCatalogo = Depends(obtener_catalogo),
) -> dict:
    return {"lista": catalogo.agregar_a_lista(sesion, datos.nombre)}


@router.delete("/shopping-list/{nombre}", response_model=ListaRespuesta)
def quitar_de_lista(
    nombre: str,
    sesion: Sesion = Depends(requerir_cliente),
    catalogo: ControladorCatalogo = Depends(obtener_catalogo),
) -> dict:
    return {"lista": catalogo.quitar_de_lista(sesion, nombre)}


# Búsqueda --------------------------------------------------------------
@router.post("/search", response_model=BusquedaRespuesta)
def buscar(
    datos: BusquedaSolicitud,
    sesion: Sesion = Depends(requerir_cliente),
    catalogo: ControladorCatalogo = Depends(obtener_catalogo),
) -> dict:
    return catalogo.buscar(sesion, datos.modo)


# Carrito ---------------------------------------------------------------
@router.get("/cart")
def consultar_carrito(
    sesion: Sesion = Depends(requerir_cliente),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> dict:
    return carrito.resumen(sesion)


@router.post("/cart/items")
def agregar_item(
    datos: CarritoItemSolicitud,
    sesion: Sesion = Depends(requerir_cliente),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> dict:
    return carrito.agregar_item(sesion, datos.almacen_id, datos.producto_id, datos.cantidad)


@router.patch("/cart/items/{item_id}")
def actualizar_cantidad(
    item_id: str,
    datos: CantidadSolicitud,
    sesion: Sesion = Depends(requerir_cliente),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> dict:
    return carrito.actualizar_cantidad(sesion, item_id, datos.cantidad)


@router.delete("/cart/items/{item_id}")
def quitar_item(
    item_id: str,
    sesion: Sesion = Depends(requerir_cliente),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> dict:
    return carrito.quitar_item(sesion, item_id)


@router.delete("/cart")
def vaciar_carrito(
    sesion: Sesion = Depends(requerir_cliente),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> dict:
    return carrito.vaciar(sesion)


@router.post("/cart/coupons")
def aplicar_cupon(
    datos: CuponSolicitud,
    sesion: Sesion = Depends(requerir_cliente),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> dict:
    return carrito.aplicar_cupon(sesion, datos.codigo)


@router.delete("/cart/coupons/{codigo}")
def quitar_cupon(
    codigo: str,
    sesion: Sesion = Depends(requerir_cliente),
    carrito: ControladorCarrito = Depends(obtener_carrito),
) -> dict:
    return carrito.quitar_cupon(sesion, codigo)


# Compra simulada -------------------------------------------------------
@router.post("/checkout", response_model=CompraRespuesta)
def finalizar_compra(
    datos: CheckoutSolicitud,
    sesion: Sesion = Depends(requerir_cliente),
    compras: ControladorCompras = Depends(obtener_compras),
) -> dict:
    return compras.comprar(
        sesion,
        telefono=datos.telefono,
        direccion=datos.direccion,
        ciudad=datos.ciudad,
        total_esperado=datos.total_esperado,
        clave_idempotencia=datos.clave_idempotencia,
    )


__all__ = ["router"]
