"""Pagos, compras completadas y estadísticas del almacén."""

from __future__ import annotations

import uuid
from typing import Any

from core.errors import (
    Conflicto,
    NoEncontrado,
    ServicioNoDisponible,
    SolicitudInvalida,
)
from core.logging import obtener_logger
from infrastructure.mongodb.almacen import RepositorioAlmacen
from infrastructure.mongodb.global_db import RepositorioComprasGlobal
from infrastructure.pagos import (
    ConfiguracionPagosInvalida,
    ErrorPasarela,
    ProveedorPagos,
    cop_a_centavos,
)
from models.texto import normalizar_texto

from .carrito import ControladorCarrito
from .sesiones import Sesion

logger = obtener_logger("asistente_compras.compras")


def _dinero(valor: Any) -> float:
    return round(float(valor) + 1e-9, 2)


class ControladorComprasCliente:
    """Checkout del cliente contra ``global_asistente_compras.compras``."""

    def __init__(
        self,
        repositorio: RepositorioComprasGlobal,
        carrito: ControladorCarrito,
        pagos: ProveedorPagos | None = None,
    ) -> None:
        self.repo = repositorio
        self.carrito = carrito
        self.pagos = pagos

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

        if not sesion.autoriza_datos:
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
            "pago": False,
            "pago_detalle": {
                "estado": "PENDING",
                "proveedor": "none",
                "referencia_externa": "",
                "monto": cop_a_centavos(total_actual),
                "moneda": "COP",
                "checkout_url": None,
                "eventos": [],
            },
        }
        if self.pagos is None:
            raise ServicioNoDisponible("No hay una pasarela de pagos configurada")
        try:
            checkout = self.pagos.crear_checkout(
                referencia=documento["_id"],
                monto_cents=cop_a_centavos(total_actual),
                moneda="COP",
                correo=sesion.email,
                nombre=sesion.nombre,
            )
        except ConfiguracionPagosInvalida as error:
            raise ServicioNoDisponible(str(error)) from error
        documento["pago_detalle"].update(checkout)
        documento["pago_detalle"]["referencia_externa"] = str(
            checkout.get("referencia_externa") or documento["_id"]
        )
        documento["pago_detalle"]["estado"] = "PENDING"
        documento["pago_proveedor"] = str(checkout.get("proveedor") or "none")
        documento["pago_referencia"] = documento["pago_detalle"]["referencia_externa"]
        compra, _creada = self.repo.crear_compra(
            documento, cliente_id=sesion.usuario_id, clave_idempotencia=clave
        )

        return self._publica(compra)

    def obtener_estado(self, sesion: Sesion, compra_id: str) -> dict[str, Any]:
        compra = self._compra_del_cliente(sesion, compra_id)
        if self._esta_aprobada(compra):
            self._descontar_items(sesion, compra)
        return self._publica(compra)

    def procesar_evento(self, evento: dict[str, Any]) -> dict[str, Any] | None:
        tipo = str(evento.get("event") or "")
        if tipo and tipo != "transaction.updated":
            logger.info("Evento de pago ignorado por tipo: %s", tipo)
            return None
        if self.pagos is None or not self.pagos.verificar_evento(evento):
            raise SolicitudInvalida("Evento de pago inválido")
        data = evento.get("data")
        if not isinstance(data, dict):
            raise SolicitudInvalida("Evento de pago sin datos")
        transaccion = data.get("transaction")
        if not isinstance(transaccion, dict):
            raise SolicitudInvalida("Evento de pago sin transacción")

        referencia = str(transaccion.get("reference") or "")
        if not referencia:
            raise SolicitudInvalida("Evento de pago sin referencia")
        compra = self.repo.obtener_compra_por_referencia(referencia)
        if compra is None:
            logger.warning("Evento de pago para una compra desconocida: %s", referencia)
            return None
        event_id = str(evento.get("timestamp") or "") + ":" + str(transaccion.get("id") or "")
        actualizada = self._aplicar_transaccion(
            compra,
            transaccion,
            tipo=tipo,
            evento_id=event_id,
        )
        return self._publica(actualizada) if actualizada else None

    def sincronizar_pago(
        self,
        sesion: Sesion,
        compra_id: str,
        transaccion_id: str,
    ) -> dict[str, Any]:
        compra = self._compra_del_cliente(sesion, compra_id)
        transaccion_id = str(transaccion_id or "").strip()
        if not transaccion_id:
            raise SolicitudInvalida("Falta el identificador de la transacción")
        if self.pagos is None:
            raise ServicioNoDisponible("No hay una pasarela de pagos configurada")
        try:
            transaccion = self.pagos.consultar_transaccion(transaccion_id)
        except ErrorPasarela as error:
            raise ServicioNoDisponible(str(error)) from error
        if not isinstance(transaccion, dict):
            raise ServicioNoDisponible(
                "La pasarela no permite consultar la transacción. "
                "Usa el webhook de Wompi o configura WOMPI_PRIVATE_KEY."
            )
        referencia = str(transaccion.get("reference") or "")
        if referencia != str(compra.get("pago_referencia") or ""):
            raise SolicitudInvalida("La transacción no corresponde a la compra")
        actualizada = self._aplicar_transaccion(
            compra,
            transaccion,
            tipo="transaction.updated",
        )
        if actualizada is None:
            return self._publica(compra)
        if self._esta_aprobada(actualizada):
            self._descontar_items(sesion, actualizada)
        return self._publica(actualizada)

    def _aplicar_transaccion(
        self,
        compra: dict[str, Any],
        transaccion: dict[str, Any],
        *,
        tipo: str,
        evento_id: str | None = None,
    ) -> dict[str, Any] | None:
        transaccion_id = str(transaccion.get("id") or "")
        estado_externo = str(transaccion.get("status") or "").upper()
        estados = {
            "APPROVED": "APPROVED",
            "DECLINED": "DECLINED",
            "VOIDED": "VOIDED",
            "ERROR": "ERROR",
            "PENDING": "PENDING",
        }
        estado = estados.get(estado_externo)
        if estado is None:
            logger.warning("Estado de pago desconocido: %s", estado_externo)
            return compra

        pago = compra.get("pago_detalle") or {}
        monto_esperado = int(pago.get("monto") or 0)
        monto_recibido = int(transaccion.get("amount_in_cents") or 0)
        if monto_esperado and monto_recibido != monto_esperado:
            logger.warning(
                "Monto inconsistente para la compra %s: esperado %s, recibido %s",
                compra.get("_id"),
                monto_esperado,
                monto_recibido,
            )
            raise SolicitudInvalida("El monto del pago no coincide con la compra")
        moneda_esperada = str(pago.get("moneda") or "COP").upper()
        moneda_recibida = str(transaccion.get("currency") or moneda_esperada).upper()
        if moneda_esperada and moneda_recibida != moneda_esperada:
            raise SolicitudInvalida("La moneda del pago no coincide con la compra")

        estado_actual = str(pago.get("estado") or "")
        if not estado_actual:
            estado_actual = "APPROVED" if bool(compra.get("pago")) else "PENDING"
        if estado_actual == "APPROVED" and estado not in {"APPROVED", "VOIDED"}:
            logger.info(
                "Se ignora el estado %s para la compra %s que ya está aprobada",
                estado,
                compra.get("_id"),
            )
            return compra
        if estado_actual == "VOIDED" and estado != "VOIDED":
            return compra

        actualizada = self.repo.actualizar_pago(
            str(compra["_id"]),
            estado=estado,
            transaccion_id=transaccion_id,
            estado_externo=estado_externo,
            evento={
                "evento_id": evento_id or f"{estado_externo}:{transaccion_id}",
                "tipo": tipo or "transaction.updated",
                "estado": estado,
            },
        )
        if actualizada and estado == "APPROVED":
            logger.info("Pago aprobado para la compra %s", compra.get("_id"))
        return actualizada

    def _compra_del_cliente(self, sesion: Sesion, compra_id: str) -> dict[str, Any]:
        compra = self.repo.obtener_compra(compra_id)
        if compra is None or str(compra.get("cliente_id")) != sesion.usuario_id:
            raise NoEncontrado("Compra no encontrada")
        return compra

    @staticmethod
    def _esta_aprobada(compra: dict[str, Any]) -> bool:
        pago_detalle = compra.get("pago_detalle") or {}
        estado = str(pago_detalle.get("estado") or "")
        if not estado:
            return bool(compra.get("pago"))
        return bool(compra.get("pago")) or estado == "APPROVED"

    @staticmethod
    def _descontar_items(sesion: Sesion, compra: dict[str, Any]) -> None:
        for item in compra.get("items", []) or []:
            sesion.carrito.descontar(
                str(item.get("almacen_id") or ""),
                str(item.get("producto_id") or ""),
                int(item.get("cantidad") or 0),
            )

    @staticmethod
    def _publica(compra: dict[str, Any]) -> dict[str, Any]:
        pago_detalle = compra.get("pago_detalle") or {}
        estado = str(pago_detalle.get("estado") or "")
        if not estado:
            estado = "APPROVED" if bool(compra.get("pago")) else "PENDING"
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
            "pago": bool(compra.get("pago")) or estado == "APPROVED",
            "pago_estado": estado,
            "pago_proveedor": pago_detalle.get("proveedor") or "",
            "pago_referencia": pago_detalle.get("referencia_externa") or "",
            "checkout_url": pago_detalle.get("checkout_url"),
        }


class ControladorComprasAlmacen:
    """Compras y estadísticas de la base propia del almacén."""

    def __init__(self, repositorio: RepositorioAlmacen) -> None:
        self.repo = repositorio

    def compras_del_almacen(self) -> list[dict[str, Any]]:
        return self.repo.listar_compras_por_almacen()

    def estadisticas_del_almacen(self) -> dict[str, Any]:
        filas = self.repo.estadisticas_almacen()
        productos = self.repo.listar_todos_productos()
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


# Compatibilidad con importaciones antiguas.
ControladorCompras = ControladorComprasCliente

__all__ = [
    "ControladorCompras",
    "ControladorComprasAlmacen",
    "ControladorComprasCliente",
]
