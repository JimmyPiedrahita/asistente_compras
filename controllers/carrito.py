"""Carrito, cupones y cálculo de totales."""

from __future__ import annotations

from typing import Any

from core.errors import NoEncontrado, SolicitudInvalida
from infrastructure.mongodb.repositorio import RepositorioMongo
from models.texto import normalizar_texto

from .sesiones import Sesion

MAX_CUPONES = 3


def _dinero(valor: float) -> float:
    return round(float(valor) + 1e-9, 2)


class ControladorCarrito:
    def __init__(self, repositorio: RepositorioMongo) -> None:
        self.repo = repositorio

    # Ítems -------------------------------------------------------------
    def agregar_item(
        self,
        sesion: Sesion,
        almacen_id: str,
        producto_id: str,
        cantidad: int = 1,
    ) -> dict[str, Any]:
        producto = self.repo.obtener_producto(producto_id)
        if producto is None or producto.almacen_id != str(almacen_id):
            raise NoEncontrado("Producto o almacén no encontrado")
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError) as error:
            raise SolicitudInvalida("La cantidad debe ser un número entero") from error
        if cantidad < 1:
            raise SolicitudInvalida("La cantidad debe ser mayor que cero")
        sesion.carrito.agregar(producto.almacen_id, producto.producto_id, cantidad)
        return self.resumen(sesion)

    def actualizar_cantidad(self, sesion: Sesion, item_id: str, cantidad: int) -> dict[str, Any]:
        try:
            actualizado = sesion.carrito.actualizar_cantidad(item_id, cantidad)
        except ValueError as error:
            raise SolicitudInvalida(str(error)) from error
        if not actualizado:
            raise NoEncontrado("Ítem no encontrado en el carrito")
        return self.resumen(sesion)

    def quitar_item(self, sesion: Sesion, item_id: str) -> dict[str, Any]:
        if not sesion.carrito.quitar(item_id):
            raise NoEncontrado("Ítem no encontrado en el carrito")
        return self.resumen(sesion)

    def vaciar(self, sesion: Sesion) -> dict[str, Any]:
        sesion.carrito.vaciar()
        return self.resumen(sesion)

    # Cupones -----------------------------------------------------------
    def aplicar_cupon(self, sesion: Sesion, codigo: str) -> dict[str, Any]:
        codigo = str(codigo or "").strip()
        if not codigo:
            raise SolicitudInvalida("Escribe el código de un cupón")
        cupon = self.repo.obtener_cupon_por_codigo(codigo)
        if cupon is None:
            raise SolicitudInvalida("El cupón no existe o fue eliminado")

        resumen = self.resumen(sesion)
        almacenes = {parte["almacen_id"] for parte in resumen["detalle_almacenes"]}
        if cupon.almacen_id not in almacenes:
            raise SolicitudInvalida("El carrito no contiene productos del almacén de este cupón")

        for aplicado in resumen["cupones_aplicados"]:
            if normalizar_texto(aplicado["codigo"]) == normalizar_texto(cupon.codigo):
                raise SolicitudInvalida("Este cupón ya está aplicado")
            if aplicado["almacen_id"] == cupon.almacen_id:
                raise SolicitudInvalida(
                    "Ya hay un cupón aplicado para ese almacén. "
                    "Quita el anterior antes de aplicar otro."
                )
        if len(resumen["cupones_aplicados"]) >= MAX_CUPONES:
            raise SolicitudInvalida("Solo puedes aplicar hasta tres cupones por compra")

        sesion.carrito.cupones.append(cupon.codigo)
        return self.resumen(sesion)

    def quitar_cupon(self, sesion: Sesion, codigo: str) -> dict[str, Any]:
        buscado = normalizar_texto(codigo)
        antes = len(sesion.carrito.cupones)
        sesion.carrito.cupones = [
            aplicado for aplicado in sesion.carrito.cupones if normalizar_texto(aplicado) != buscado
        ]
        if len(sesion.carrito.cupones) == antes:
            raise SolicitudInvalida("Ese cupón no está aplicado en el carrito")
        return self.resumen(sesion)

    # Resumen -----------------------------------------------------------
    def resumen(self, sesion: Sesion) -> dict[str, Any]:
        avisos: list[str] = []
        items_validos: list[dict[str, Any]] = []
        almacenes: dict[str, Any] = {}

        for item in list(sesion.carrito.items):
            producto = self.repo.obtener_producto(item.producto_id)
            if producto is None or producto.almacen_id != item.almacen_id:
                avisos.append("Un producto de tu carrito ya no está disponible y fue retirado.")
                sesion.carrito.quitar(item.item_id)
                continue
            almacen = self.repo.obtener_almacen(producto.almacen_id)
            if almacen is None:
                avisos.append("Un almacén de tu carrito ya no está disponible.")
                sesion.carrito.quitar(item.item_id)
                continue
            almacenes.setdefault(
                almacen.almacen_id,
                {"almacen_id": almacen.almacen_id, "almacen": almacen.nombre},
            )
            importe = _dinero(producto.precio * item.cantidad)
            items_validos.append(
                {
                    "item_id": item.item_id,
                    "almacen_id": almacen.almacen_id,
                    "almacen": almacen.nombre,
                    "producto_id": producto.producto_id,
                    "tipo_producto": producto.tipo_producto,
                    "nombre": producto.nombre,
                    "marca_variedad": producto.marca_variedad,
                    "presentacion": producto.presentacion,
                    "precio_unitario": producto.precio,
                    "cantidad": item.cantidad,
                    "importe": importe,
                }
            )

        # Se validan los cupones aplicados: deben existir, pertenecer a un
        # almacén presente y no repetirse por almacén.
        cupones_validos: list[dict[str, Any]] = []
        vistos: set[str] = set()
        for codigo in list(sesion.carrito.cupones):
            cupon = self.repo.obtener_cupon_por_codigo(codigo)
            if cupon is None:
                avisos.append(f"El cupón {codigo} fue eliminado y ya no se aplicará.")
                continue
            if cupon.almacen_id not in almacenes:
                avisos.append(
                    f"El cupón {cupon.codigo} no aplica porque no hay productos "
                    "de su almacén en el carrito."
                )
                continue
            if cupon.almacen_id in vistos:
                avisos.append(f"Solo se permite un cupón por almacén. Se ignoró {cupon.codigo}.")
                continue
            vistos.add(cupon.almacen_id)
            cupones_validos.append(
                {
                    "codigo": cupon.codigo,
                    "almacen_id": cupon.almacen_id,
                    "almacen": almacenes[cupon.almacen_id]["almacen"],
                    "porcentaje": cupon.porcentaje,
                }
            )

        sesion.carrito.cupones = [cupon["codigo"] for cupon in cupones_validos]

        detalle_almacenes: list[dict[str, Any]] = []
        subtotal_general = 0.0
        descuento_total = 0.0
        for almacen_id, almacen in almacenes.items():
            items_almacen = [item for item in items_validos if item["almacen_id"] == almacen_id]
            subtotal = _dinero(sum(item["importe"] for item in items_almacen))
            cupon = next(
                (c for c in cupones_validos if c["almacen_id"] == almacen_id),
                None,
            )
            descuento = _dinero(subtotal * cupon["porcentaje"] / 100) if cupon else 0.0
            total_almacen = _dinero(subtotal - descuento)
            subtotal_general += subtotal
            descuento_total += descuento
            detalle_almacenes.append(
                {
                    "almacen_id": almacen_id,
                    "almacen": almacen["almacen"],
                    "items": items_almacen,
                    "subtotal": subtotal,
                    "cupon_codigo": cupon["codigo"] if cupon else None,
                    "cupon_porcentaje": cupon["porcentaje"] if cupon else None,
                    "descuento": descuento,
                    "total": total_almacen,
                }
            )

        subtotal_general = _dinero(subtotal_general)
        descuento_total = _dinero(descuento_total)
        return {
            "items": items_validos,
            "detalle_almacenes": detalle_almacenes,
            "cupones_aplicados": cupones_validos,
            "subtotal": subtotal_general,
            "descuento_total": descuento_total,
            "total": _dinero(subtotal_general - descuento_total),
            "cantidad_items": sum(item["cantidad"] for item in items_validos),
            "avisos": avisos,
        }


__all__ = ["MAX_CUPONES", "ControladorCarrito"]
