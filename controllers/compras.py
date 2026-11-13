"""Pagos, compras completadas y estadísticas del almacén."""

from __future__ import annotations

import uuid
from typing import Any

from core.errors import Conflicto, SolicitudInvalida
from infrastructure.mongodb.repositorio import RepositorioMongo
from models.texto import normalizar_texto

from .carrito import ControladorCarrito
from .sesiones import Sesion


def _dinero(valor: Any) -> float:
    return round(float(valor) + 1e-9, 2)


class ControladorCompras:
    def __init__(self, repositorio: RepositorioMongo, carrito: ControladorCarrito) -> None:
        self.repo = repositorio
        self.carrito = carrito

    def comprar(
        self,
        sesion: Sesion,
        *,
        telefono: str,
        direccion: str,
        ciudad: str,
        total_esperado: float | None,
        clave_idempotencia: str | None,
    ) -> dict[str, Any]:
        telefono = " ".join(str(telefono or "").split())
        direccion = " ".join(str(direccion or "").split())
        ciudad = " ".join(str(ciudad or "").split())
        if not telefono or not direccion or not ciudad:
            raise SolicitudInvalida("El teléfono, la dirección y la ciudad son obligatorios")

        clave = str(clave_idempotencia or "").strip() or uuid.uuid4().hex
        if clave_idempotencia:
            existente = self.repo.obtener_compra_por_clave(sesion.usuario_id, clave)
            if existente is not None:
                return self._publica(existente)

        resumen = self.carrito.resumen(sesion)
        if not resumen["items"]:
            raise SolicitudInvalida("El carrito está vacío")

        total_actual = _dinero(resumen["total"])
        if total_esperado is not None and abs(_dinero(total_esperado) - total_actual) > 0.009:
            raise Conflicto(
                "El total de la compra cambió porque un cupón ya no está disponible. "
                "Revisa el nuevo resumen y confirma otra vez.",
                detalles={"resumen": resumen},
            )

        usuario = self.repo.obtener_usuario(sesion.usuario_id)
        autorizacion = bool(usuario.autoriza_datos) if usuario else False
        if not autorizacion:
            raise SolicitudInvalida(
                "No hay autorización registrada para el tratamiento y comunicación de datos"
            )

        items = [
            {
                "almacen_id": item["almacen_id"],
                "almacen_nombre": item["almacen"],
                "producto_id": item["producto_id"],
                "tipo_producto": item["tipo_producto"],
                "nombre": item["nombre"],
                "marca_variedad": item["marca_variedad"],
                "presentacion": item["presentacion"],
                "precio_unitario": item["precio_unitario"],
                "cantidad": item["cantidad"],
                "importe": item["importe"],
            }
            for item in resumen["items"]
        ]
        por_almacen = [
            {
                "almacen_id": parte["almacen_id"],
                "almacen_nombre": parte["almacen"],
                "subtotal": parte["subtotal"],
                "cupon_codigo": parte["cupon_codigo"],
                "cupon_porcentaje": parte["cupon_porcentaje"],
                "descuento": parte["descuento"],
                "total": parte["total"],
            }
            for parte in resumen["detalle_almacenes"]
        ]

        documento = {
            "_id": uuid.uuid4().hex,
            "cliente_nombre": sesion.nombre,
            "datos_entrega": {
                "nombre": sesion.nombre,
                "telefono": telefono,
                "direccion": direccion,
                "ciudad": ciudad,
            },
            "items": items,
            "por_almacen": por_almacen,
            "subtotal": resumen["subtotal"],
            "descuento_total": resumen["descuento_total"],
            "total": total_actual,
            "autorizacion_datos": True,
            "pago": True,
        }
        clave = str(clave_idempotencia or "").strip() or uuid.uuid4().hex
        compra, creada = self.repo.crear_compra(
            documento, cliente_id=sesion.usuario_id, clave_idempotencia=clave
        )
        if creada:
            sesion.carrito.vaciar()

        return self._publica(compra)

    @staticmethod
    def _publica(compra: dict[str, Any]) -> dict[str, Any]:
        return {
            "compra_id": str(compra.get("_id")),
            "fecha": (
                compra["fecha"].isoformat()
                if hasattr(compra.get("fecha"), "isoformat")
                else str(compra.get("fecha") or "")
            ),
            "cliente_nombre": compra.get("cliente_nombre"),
            "datos_entrega": compra.get("datos_entrega", {}),
            "items": compra.get("items", []),
            "por_almacen": compra.get("por_almacen", []),
            "subtotal": compra.get("subtotal", 0),
            "descuento_total": compra.get("descuento_total", 0),
            "total": compra.get("total", 0),
            "pago": True,
        }

    # Consulta para el administrador del almacén -----------------------
    def compras_del_almacen(self, almacen_id: str) -> list[dict[str, Any]]:
        return self.repo.listar_compras_por_almacen(almacen_id)

    def estadisticas_del_almacen(self, almacen_id: str) -> dict[str, Any]:
        filas = self.repo.estadisticas_almacen(almacen_id)
        productos = self.repo.listar_todos_productos(almacen_id)
        if not productos:
            return {
                "hay_productos": False,
                "hay_ventas": False,
                "mas_vendidos": [],
                "menos_vendidos": [],
            }

        def clave_desc(fila: dict[str, Any]) -> tuple[Any, ...]:
            return (
                -int(fila["unidades_vendidas"]),
                normalizar_texto(fila["nombre"]),
                fila["producto_id"],
            )

        def clave_asc(fila: dict[str, Any]) -> tuple[Any, ...]:
            return (
                int(fila["unidades_vendidas"]),
                normalizar_texto(fila["nombre"]),
                fila["producto_id"],
            )

        return {
            "hay_productos": True,
            "hay_ventas": any(fila["unidades_vendidas"] > 0 for fila in filas),
            "mas_vendidos": sorted(filas, key=clave_desc),
            "menos_vendidos": sorted(filas, key=clave_asc),
        }


__all__ = ["ControladorCompras"]
