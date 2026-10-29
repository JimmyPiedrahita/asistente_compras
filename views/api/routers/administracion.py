"""Endpoints administrativos de inventario y CSV."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from controllers.compras import ControladorCompras
from models.permisos import EDITAR_PRECIO, GESTIONAR_ALMACENES

from ..dependencies import obtener_controlador
from ..schemas import (
    ComparadorEstadoRespuesta,
    CsvSolicitud,
    ImportacionCsvRespuesta,
    OkRespuesta,
    PrecioSolicitud,
    ProductoSolicitud,
)
from ..serializers import comparador_estado_json
from .comun import verificar_resultado

router = APIRouter(tags=["Administración"])


@router.post(
    "/sessions/{token}/admin/warehouses/{almacen_id}/products",
    response_model=OkRespuesta,
)
def agregar_producto(
    almacen_id: int,
    datos: ProductoSolicitud,
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    extra: dict[str, object] = {}
    if datos.costo_envio is not None:
        extra["costo_envio"] = datos.costo_envio
    if datos.meses is not None:
        extra["meses"] = datos.meses
    resultado = controlador.agregar_producto_almacen(
        almacen_id,
        datos.nombre,
        datos.precio,
        datos.marca,
        datos.categoria,
        datos.tipo,
        **extra,
    )
    verificar_resultado(
        resultado,
        permiso=GESTIONAR_ALMACENES,
        no_encontrado="Almacén no encontrado",
        conflicto="El producto ya existe en el almacén",
        invalido="Datos del producto inválidos",
    )
    return {"ok": True}


@router.patch(
    "/sessions/{token}/admin/warehouses/{almacen_id}/products",
    response_model=OkRespuesta,
)
def editar_precio(
    almacen_id: int,
    datos: PrecioSolicitud,
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    resultado = controlador.editar_precio_por_id(almacen_id, datos.producto_id, datos.precio)
    verificar_resultado(
        resultado,
        permiso=EDITAR_PRECIO,
        no_encontrado="Producto o almacén no encontrado",
        invalido="Precio inválido",
    )
    return {"ok": True}


@router.delete(
    "/sessions/{token}/admin/warehouses/{almacen_id}/products/{producto_id}",
    response_model=OkRespuesta,
)
def eliminar_producto(
    almacen_id: int,
    producto_id: str,
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    resultado = controlador.eliminar_producto_almacen(almacen_id, producto_id)
    verificar_resultado(
        resultado,
        permiso=GESTIONAR_ALMACENES,
        no_encontrado="Producto o almacén no encontrado",
    )
    return {"ok": True}


@router.post(
    "/sessions/{token}/admin/csv",
    response_model=ImportacionCsvRespuesta,
)
def cargar_csv(
    datos: CsvSolicitud,
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    return controlador.cargar_csv_contenido(datos.contenido)


@router.get(
    "/sessions/{token}/admin/comparador/status",
    response_model=ComparadorEstadoRespuesta,
)
def estado_comparador(
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    return comparador_estado_json(controlador.estado_comparador())


@router.post(
    "/sessions/{token}/admin/comparador/reconciliar",
    response_model=OkRespuesta,
)
def reconciliar_comparador(
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    resultado = controlador.recargar_inventarios()
    verificar_resultado(resultado, permiso=GESTIONAR_ALMACENES)
    return {"ok": True}


@router.post(
    "/sessions/{token}/admin/reload",
    response_model=OkRespuesta,
)
def recargar_inventarios(
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    resultado = controlador.recargar_inventarios()
    verificar_resultado(resultado, permiso=GESTIONAR_ALMACENES)
    return {"ok": True}


__all__ = ["router"]
