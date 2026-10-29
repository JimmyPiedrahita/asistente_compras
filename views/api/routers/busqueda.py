"""Endpoint de búsqueda y comparación."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from controllers.compras import ControladorCompras

from ..dependencies import obtener_controlador
from ..schemas import BusquedaRespuesta, BusquedaSolicitud
from ..serializers import resultado_busqueda_json

router = APIRouter(tags=["Búsqueda"])


@router.post(
    "/sessions/{token}/search",
    response_model=BusquedaRespuesta,
    response_model_exclude_none=True,
)
def buscar(
    datos: BusquedaSolicitud,
    controlador: ControladorCompras = Depends(obtener_controlador),
):
    resultado = controlador.busqueda.ejecutar(datos.modo, limit=datos.limit, offset=datos.offset)
    return {
        "modo": datos.modo,
        "resultados": resultado_busqueda_json(resultado),
    }


__all__ = ["router"]
