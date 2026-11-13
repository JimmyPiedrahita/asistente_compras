"""Conversión entre entidades de dominio y documentos de MongoDB.

Se comparte entre el repositorio de almacenes y el proyector de ``comparador``
para que ambos guarden exactamente los mismos campos.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models.productos import FabricaProductos, Producto
from models.texto import normalizar_texto


def documento_producto(producto: Producto) -> dict[str, Any]:
    """Documento que se guarda en la base de cada almacén."""
    documento: dict[str, Any] = {
        "_id": producto.producto_id,
        "nombre": producto.nombre,
        "nombre_normalizado": normalizar_texto(producto.nombre),
        "marca": producto.marca,
        "marca_normalizada": normalizar_texto(producto.marca),
        "categoria": producto.categoria,
        "tipo": producto.tipo,
        "precio": producto.precio,
    }
    if producto.tipo == "fisico":
        documento["costo_envio"] = producto.costo_envio
    elif producto.tipo == "suscripcion":
        documento["meses"] = producto.meses
    return documento


def producto_desde_documento(documento: dict[str, Any]) -> Producto:
    """Reconstruye la entidad de dominio a partir de un documento."""
    extra: dict[str, Any] = {}
    if documento.get("tipo") == "fisico":
        extra["costo_envio"] = documento.get("costo_envio", 5.0)
    elif documento.get("tipo") == "suscripcion":
        extra["meses"] = documento.get("meses", 1)

    producto_id = str(documento.get("producto_id") or documento["_id"])
    return FabricaProductos.crear_producto(
        documento.get("tipo", "normal"),
        documento["nombre"],
        documento["precio"],
        marca=documento.get("marca", "Generica"),
        categoria=documento.get("categoria", "General"),
        producto_id=producto_id,
        **extra,
    )


def id_comparador(id_almacen: int, producto_id: str) -> str:
    """``_id`` compuesto que permite convivir al mismo producto en varios almacenes."""
    return f"{int(id_almacen)}_{producto_id}"


def documento_comparador(
    id_almacen: int,
    almacen_nombre: str,
    producto: Producto,
    *,
    sincronizado_en: datetime | None = None,
    marca_reconciliacion: str | None = None,
) -> dict[str, Any]:
    """Documento de la proyección integrada ``comparador.productos``."""
    documento = documento_producto(producto)
    documento.pop("_id", None)
    documento["_id"] = id_comparador(id_almacen, producto.producto_id)
    documento["producto_id"] = producto.producto_id
    documento["almacen_id"] = int(id_almacen)
    documento["almacen_nombre"] = str(almacen_nombre)
    documento["precio_final"] = producto.obtener_precio_final()
    documento["sincronizado_en"] = sincronizado_en or datetime.now(timezone.utc)
    if marca_reconciliacion is not None:
        documento["_reconciliacion"] = marca_reconciliacion
    return documento


__all__ = [
    "documento_comparador",
    "documento_producto",
    "id_comparador",
    "producto_desde_documento",
]
