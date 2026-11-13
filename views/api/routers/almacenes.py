"""Endpoints de almacenes e inventario."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from core.errors import NoEncontrado
from models.almacenes import GestorAlmacenes

from ..dependencies import obtener_gestor
from ..schemas import AlmacenRespuesta, ProductoRespuesta
from ..serializers import almacen_json, producto_json

router = APIRouter(tags=["Almacenes"])


@router.get("/warehouses", response_model=list[AlmacenRespuesta])
def listar_almacenes(gestor: GestorAlmacenes = Depends(obtener_gestor)):
    return [
        almacen_json(almacen, gestor.contar_productos(almacen.id_almacen))
        for almacen in gestor.obtener_almacenes()
    ]


@router.get(
    "/warehouses/{almacen_id}/products",
    response_model=list[ProductoRespuesta],
    response_model_exclude_none=True,
)
def listar_productos(
    almacen_id: int,
    response: Response,
    limit: int = Query(100, ge=1, le=500, description="Máximo de productos a devolver"),
    offset: int = Query(0, ge=0, description="Productos a omitir"),
    gestor: GestorAlmacenes = Depends(obtener_gestor),
):
    if gestor.obtener_almacen(almacen_id) is None:
        raise NoEncontrado(f"Almacén no encontrado: {almacen_id}")
    productos, total = gestor.listar_productos(almacen_id, limit, offset)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [producto_json(producto) for producto in productos]


__all__ = ["router"]
