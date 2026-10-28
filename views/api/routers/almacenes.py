"""Endpoints de almacenes e inventario."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from core.errors import NoEncontrado
from models.almacenes import GestorAlmacenes

from ..dependencies import obtener_gestor
from ..schemas import AlmacenRespuesta, ProductoRespuesta
from ..serializers import almacen_json, producto_json

router = APIRouter(tags=["Almacenes"])


@router.get("/warehouses", response_model=list[AlmacenRespuesta])
def listar_almacenes(gestor: GestorAlmacenes = Depends(obtener_gestor)):
    return [almacen_json(almacen) for almacen in gestor.obtener_almacenes()]


@router.get(
    "/warehouses/{almacen_id}/products",
    response_model=list[ProductoRespuesta],
    response_model_exclude_none=True,
)
def listar_productos(almacen_id: int, gestor: GestorAlmacenes = Depends(obtener_gestor)):
    almacen = gestor.obtener_almacen(almacen_id)
    if almacen is None:
        raise NoEncontrado(f"Almacén no encontrado: {almacen_id}")
    return [producto_json(producto) for producto in almacen.inventario.mostrar()]


__all__ = ["router"]
