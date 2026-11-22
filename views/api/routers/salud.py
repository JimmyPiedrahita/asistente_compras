"""Endpoints de salud."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from infrastructure.mongodb.contexto import ContextoAplicacion

from ..dependencies import obtener_contexto

router = APIRouter(tags=["Salud"])


def _verificar(contexto: ContextoAplicacion) -> None:
    contexto.conexiones.ping(contexto.fabrica.uri_auth())
    contexto.conexiones.ping(contexto.fabrica.uri_admin_app())


@router.get("/health")
def health(contexto: ContextoAplicacion = Depends(obtener_contexto)) -> dict[str, str]:
    _verificar(contexto)
    return {"status": "ok", "database": "ok"}


@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready(contexto: ContextoAplicacion = Depends(obtener_contexto)) -> dict[str, str]:
    _verificar(contexto)
    return {"status": "ready", "database": "ok"}


__all__ = ["router"]
