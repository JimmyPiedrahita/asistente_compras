"""Entidad de almacén.

Los campos ``db_name``, ``mongo_user`` y ``estado`` son metadata interna del
aprovisionamiento. Nunca se serializan en la API: ``publico()`` conserva el
contrato histórico (``almacen_id``, ``nombre`` y ``creado_en``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class Almacen:
    almacen_id: str
    nombre: str
    creado_en: datetime | None = None
    db_name: str = ""
    mongo_user: str = ""
    estado: str = "activo"

    def publico(self) -> dict[str, Any]:
        return {
            "almacen_id": self.almacen_id,
            "nombre": self.nombre,
            "creado_en": (self.creado_en or datetime.now(timezone.utc)).isoformat(),
        }

    def metadata(self) -> dict[str, Any]:
        """Documento interno para ``global_asistente_compras.almacenes``."""
        return {
            "_id": self.almacen_id,
            "nombre": self.nombre,
            "nombre_normalizado": " ".join(self.nombre.casefold().split()),
            "db_name": self.db_name,
            "mongo_user": self.mongo_user,
            "estado": self.estado,
            "creado_en": self.creado_en or datetime.now(timezone.utc),
        }


__all__ = ["Almacen"]
