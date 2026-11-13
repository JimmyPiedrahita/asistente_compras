"""Endpoints de salud."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from infrastructure.mongodb.repositorio import RepositorioMongo

from ..dependencies import obtener_repositorio

router = APIRouter(tags=["Salud"])


@router.get("/health")
def health(repo: RepositorioMongo = Depends(obtener_repositorio)) -> dict[str, str]:
    repo.ping()
    return {"status": "ok", "database": "ok"}


@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready(repo: RepositorioMongo = Depends(obtener_repositorio)) -> dict[str, str]:
    repo.ping()
    return {"status": "ready", "database": "ok"}


__all__ = ["router"]
