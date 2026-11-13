"""Entidad de almacén."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class Almacen:
    almacen_id: str
    nombre: str
    creado_en: datetime | None = None

    def publico(self) -> dict[str, Any]:
        return {
            "almacen_id": self.almacen_id,
            "nombre": self.nombre,
            "creado_en": (self.creado_en or datetime.now(timezone.utc)).isoformat(),
        }


__all__ = ["Almacen"]
