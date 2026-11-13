"""Repositorio nulo para generar documentación y pruebas sin MongoDB."""

from __future__ import annotations

from typing import Any

from models.productos import Producto


class RepositorioNulo:
    """Implementa el contrato sin conectarse a ninguna base de datos."""

    def cargar_almacen(self, id_almacen: int) -> list[Producto]:
        return []

    def listar_productos(
        self, id_almacen: int, limit: int = 100, offset: int = 0
    ) -> tuple[list[Producto], int]:
        return [], 0

    def producto_en_indice(self, id_almacen: int, indice: int) -> Producto | None:
        return None

    def obtener_producto(self, id_almacen: int, producto_id: str) -> Producto | None:
        return None

    def existe_nombre_marca(self, id_almacen: int, nombre: str, marca: str | None = None) -> bool:
        return False

    def contar(self, id_almacen: int) -> int:
        return 0

    def insertar(self, id_almacen: int, producto: Producto) -> None:
        return None

    def actualizar(self, id_almacen: int, producto: Producto) -> None:
        return None

    def eliminar(self, id_almacen: int, producto_id: str) -> None:
        return None

    def upsert_por_nombre_marca(self, id_almacen: int, producto: Producto) -> str:
        return "insertado"

    def buscar_mejor_precio(self, nombres) -> dict:
        return {}

    def buscar_catalogo(self, nombres, limit: int = 100, offset: int = 0) -> dict:
        return {}

    def buscar_global(self, nombres) -> list[dict[str, Any]]:
        return []

    def estado_comparador(self) -> dict[str, Any]:
        return {
            "estado": "sin_persistencia",
            "documentos": 0,
            "ultima_sincronizacion": None,
            "ultimo_evento": None,
            "tiene_resume_token": False,
        }

    def reconciliar_comparador(self) -> dict[str, Any]:
        return {"documentos": 0, "reconciliados": 0}

    def ping(self) -> None:
        return None

    def close(self) -> None:
        return None


__all__ = ["RepositorioNulo"]
