"""Endpoints de salud."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import obtener_repositorio
from ..schemas import HealthRespuesta

router = APIRouter(tags=["Salud"])


@router.get("/health", response_model=HealthRespuesta, response_model_exclude_none=True)
def health(repositorio=Depends(obtener_repositorio)) -> dict[str, str]:
    repositorio.ping()
    return {"status": "ok", "database": "mongodb"}


@router.get("/health/live", response_model=HealthRespuesta, response_model_exclude_none=True)
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", response_model=HealthRespuesta, response_model_exclude_none=True)
def health_ready(repositorio=Depends(obtener_repositorio)) -> dict[str, str]:
    repositorio.ping()
    return {"status": "ready", "database": "mongodb"}


__all__ = ["router"]
