"""Endpoints de exportación CSV."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from controllers.compras import ControladorCompras

from ..dependencies import obtener_controlador

router = APIRouter(tags=["Exportación"])


@router.get("/sessions/{token}/export/shopping-list")
def exportar_lista(controlador: ControladorCompras = Depends(obtener_controlador)):
    contenido = controlador.exportar_lista_csv()
    return Response(
        content=contenido,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="lista_compra.csv"'},
    )


@router.get("/sessions/{token}/export/cart")
def exportar_carrito(controlador: ControladorCompras = Depends(obtener_controlador)):
    contenido = controlador.exportar_carrito_csv()
    return Response(
        content=contenido,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="carrito.csv"'},
    )


__all__ = ["router"]
