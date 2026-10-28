"""Serialización de objetos de dominio a JSON."""

from __future__ import annotations

from typing import Any


def producto_json(producto: Any) -> dict[str, Any]:
    resultado: dict[str, Any] = {
        "producto_id": producto.producto_id,
        "nombre": producto.nombre,
        "marca": producto.marca,
        "categoria": producto.categoria,
        "tipo": producto.tipo,
        "precio": producto.precio,
        "precio_final": producto.obtener_precio_final(),
    }
    if producto.tipo == "fisico":
        resultado["costo_envio"] = producto.costo_envio
    elif producto.tipo == "suscripcion":
        resultado["meses"] = producto.meses
    return resultado


def resultado_busqueda_json(resultado: Any) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    if isinstance(resultado, dict):
        items = (
            (almacen, producto)
            for almacen, productos in resultado.items()
            for producto in productos.mostrar()
        )
    else:
        items = ((fila["almacen"], fila["producto"]) for fila in resultado)

    for almacen, producto in items:
        filas.append(
            {
                "almacen_id": almacen.id_almacen,
                "almacen": almacen.nombre,
                "producto": producto_json(producto),
            }
        )
    return filas


def resumen_carrito_json(resumen: dict[str, Any]) -> dict[str, Any]:
    return {
        "productos": [producto_json(producto) for producto in resumen["productos"]],
        "subtotal": resumen["subtotal"],
        "total": resumen["total"],
        "descuento": resumen["descuento"],
    }


def estado_sesion_json(controlador: Any) -> dict[str, Any]:
    return {
        "usuario": controlador.obtener_usuario_actual(),
        "rol": controlador.obtener_rol(),
        "lista": controlador.obtener_compras_usuario(),
        "carrito": resumen_carrito_json(controlador.obtener_resumen_carrito()),
    }


def almacen_json(almacen: Any) -> dict[str, Any]:
    return {
        "id": almacen.id_almacen,
        "name": almacen.nombre,
        "products": len(almacen.inventario),
    }


__all__ = [
    "almacen_json",
    "estado_sesion_json",
    "producto_json",
    "resultado_busqueda_json",
    "resumen_carrito_json",
]
