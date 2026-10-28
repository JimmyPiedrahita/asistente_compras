"""Modelos base de los esquemas HTTP."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ModeloBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ErrorRespuesta(ModeloBase):
    error: str
    codigo: str | None = None
    detalles: Any | None = None


__all__ = ["ErrorRespuesta", "ModeloBase"]
