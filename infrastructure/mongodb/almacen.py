"""Repositorio de una base de almacén: productos, cupones y compras proyectadas."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from core.errors import Conflicto, NoEncontrado
from models.cupones import Cupon, validar_porcentaje
from models.productos import Producto
from models.texto import normalizar_texto

from .errores import traducir_error


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(valor: Any) -> str | None:
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, str):
        return valor
    return None


def _producto_documento(producto: Producto) -> dict[str, Any]:
    return {
        "_id": producto.producto_id,
        "almacen_id": producto.almacen_id,
        "tipo_producto": producto.tipo_producto,
        "tipo_normalizado": producto.tipo_normalizado,
        "nombre": producto.nombre,
        "nombre_normalizado": producto.nombre_normalizado,
        "marca_variedad": producto.marca_variedad,
        "marca_normalizada": normalizar_texto(producto.marca_variedad),
        "precio": producto.precio,
        "presentacion": producto.presentacion,
        "presentacion_normalizada": producto.presentacion_normalizada,
        "creado_en": producto.creado_en or _ahora(),
        "actualizado_en": producto.actualizado_en or _ahora(),
    }


def _producto(documento: dict[str, Any]) -> Producto:
    return Producto(
        producto_id=str(documento.get("_id", "")),
        almacen_id=str(documento.get("almacen_id", "")),
        tipo_producto=str(documento.get("tipo_producto", "")),
        nombre=str(documento.get("nombre", "")),
        marca_variedad=str(documento.get("marca_variedad", "")),
        precio=documento.get("precio"),
        presentacion=str(documento.get("presentacion", "")),
        creado_en=documento.get("creado_en"),
        actualizado_en=documento.get("actualizado_en"),
    )


def _cupon(documento: dict[str, Any]) -> Cupon:
    return Cupon(
        cupon_id=str(documento.get("_id", "")),
        codigo=str(documento.get("codigo", "")),
        almacen_id=str(documento.get("almacen_id", "")),
        porcentaje=float(documento.get("porcentaje", 0)),
        creado_en=documento.get("creado_en"),
    )


class RepositorioAlmacen:
    """Opera siempre sobre la base del almacén de la sesión."""

    def __init__(self, base: Database, almacen_id: str) -> None:
        self.almacen_id = str(almacen_id)
        self.productos: Collection = base["productos"]
        self.cupones: Collection = base["cupones"]
        self.compras_almacen: Collection = base["compras_almacen"]

    def inicializar(self) -> None:
        try:
            self.productos.create_index(
                [("almacen_id", ASCENDING), ("tipo_normalizado", ASCENDING)]
            )
            self.productos.create_index([("tipo_normalizado", ASCENDING), ("precio", ASCENDING)])
            self.productos.create_index("presentacion_normalizada")
            self.cupones.create_index("codigo_normalizado", unique=True)
            self.cupones.create_index("almacen_id")
            self.compras_almacen.create_index("fecha")
            self.compras_almacen.create_index("cliente_id")
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo inicializar la base del almacén") from error

    # Productos ---------------------------------------------------------
    def insertar_producto(self, producto: Producto) -> Producto:
        documento = _producto_documento(producto)
        try:
            self.productos.insert_one(documento)
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo guardar el producto") from error
        return producto

    def insertar_productos_validados(self, productos: Iterable[Producto]) -> int:
        documentos = [_producto_documento(producto) for producto in productos]
        if not documentos:
            return 0
        try:
            self.productos.insert_many(documentos, ordered=True)
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo importar el catálogo") from error
        return len(documentos)

    def guardar_producto(self, producto: Producto) -> Producto:
        documento = _producto_documento(producto)
        documento.pop("_id", None)
        documento["creado_en"] = producto.creado_en or _ahora()
        documento["actualizado_en"] = _ahora()
        try:
            resultado = self.productos.update_one(
                {"_id": producto.producto_id, "almacen_id": self.almacen_id},
                {"$set": documento},
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo actualizar el producto") from error
        if resultado.matched_count != 1:
            raise NoEncontrado("Producto no encontrado")
        return producto

    def eliminar_producto(self, producto_id: str) -> None:
        try:
            resultado = self.productos.delete_one(
                {"_id": str(producto_id), "almacen_id": self.almacen_id}
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo eliminar el producto") from error
        if resultado.deleted_count != 1:
            raise NoEncontrado("Producto no encontrado")

    def obtener_producto(self, producto_id: str) -> Producto | None:
        try:
            documento = self.productos.find_one(
                {"_id": str(producto_id), "almacen_id": self.almacen_id}
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el producto") from error
        return _producto(documento) if documento else None

    def listar_productos(
        self,
        *,
        limite: int = 100,
        desplazamiento: int = 0,
    ) -> tuple[list[Producto], int]:
        filtro = {"almacen_id": self.almacen_id}
        try:
            total = int(self.productos.count_documents(filtro))
            documentos = (
                self.productos.find(filtro)
                .sort([("tipo_normalizado", 1), ("nombre_normalizado", 1), ("_id", 1)])
                .skip(max(0, int(desplazamiento)))
                .limit(max(1, int(limite)))
            )
            return [_producto(documento) for documento in documentos], total
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo listar el catálogo") from error

    def listar_todos_productos(self) -> list[Producto]:
        try:
            documentos = self.productos.find({"almacen_id": self.almacen_id}).sort(
                [("nombre_normalizado", 1), ("_id", 1)]
            )
            return [_producto(documento) for documento in documentos]
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo listar el catálogo") from error

    def presentaciones_del_tipo(
        self, tipo_normalizado: str, *, excluir_id: str | None = None
    ) -> set[str]:
        filtro: dict[str, Any] = {"tipo_normalizado": normalizar_texto(tipo_normalizado)}
        if excluir_id:
            filtro["_id"] = {"$ne": str(excluir_id)}
        try:
            valores = self.productos.distinct("presentacion_normalizada", filtro)
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo validar la presentación") from error
        return {str(valor) for valor in valores if str(valor).strip()}

    # Cupones -----------------------------------------------------------
    def crear_cupon(self, *, codigo: str, porcentaje: Any) -> Cupon:
        codigo_limpio = " ".join(str(codigo or "").split()).upper()
        if not codigo_limpio:
            raise Conflicto("El código del cupón es obligatorio")
        try:
            porcentaje_validado = validar_porcentaje(porcentaje)
        except ValueError as error:
            raise Conflicto(str(error)) from error
        documento = {
            "_id": uuid.uuid4().hex,
            "codigo": codigo_limpio,
            "codigo_normalizado": normalizar_texto(codigo_limpio),
            "almacen_id": self.almacen_id,
            "porcentaje": porcentaje_validado,
            "creado_en": _ahora(),
        }
        try:
            self.cupones.insert_one(documento)
        except DuplicateKeyError as error:
            raise Conflicto("Ya existe un cupón con ese código en este almacén") from error
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo crear el cupón") from error
        return _cupon(documento)

    def listar_cupones(self) -> list[Cupon]:
        try:
            documentos = self.cupones.find({"almacen_id": self.almacen_id}).sort("creado_en", -1)
            return [_cupon(documento) for documento in documentos]
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron listar los cupones") from error

    def obtener_cupon_por_codigo(self, codigo: str) -> Cupon | None:
        try:
            documento = self.cupones.find_one(
                {
                    "codigo_normalizado": normalizar_texto(codigo),
                    "almacen_id": self.almacen_id,
                }
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el cupón") from error
        return _cupon(documento) if documento else None

    def eliminar_cupon(self, cupon_id: str) -> None:
        try:
            resultado = self.cupones.delete_one(
                {"_id": str(cupon_id), "almacen_id": self.almacen_id}
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo eliminar el cupón") from error
        if resultado.deleted_count != 1:
            raise NoEncontrado("Cupón no encontrado")

    # Compras proyectadas ----------------------------------------------
    def upsert_compra(self, documento: dict[str, Any]) -> None:
        datos = dict(documento)
        datos["_id"] = f"{datos['compra_id']}:{self.almacen_id}"
        datos["almacen_id"] = self.almacen_id
        datos["sincronizado_en"] = _ahora()
        try:
            self.compras_almacen.replace_one({"_id": datos["_id"]}, datos, upsert=True)
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo proyectar la compra") from error

    def eliminar_compra(self, compra_id: str) -> None:
        try:
            self.compras_almacen.delete_one({"_id": f"{compra_id}:{self.almacen_id}"})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo eliminar la proyección") from error

    def listar_ids_compras(self) -> set[str]:
        try:
            return {
                str(documento.get("compra_id"))
                for documento in self.compras_almacen.find({}, {"compra_id": 1})
            }
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron listar las compras") from error

    def listar_compras_por_almacen(self) -> list[dict[str, Any]]:
        try:
            documentos = self.compras_almacen.find({}).sort("fecha", -1)
            return [
                {
                    "compra_id": str(documento.get("compra_id")),
                    "fecha": _iso(documento.get("fecha")),
                    "cliente_nombre": documento.get("cliente_nombre", ""),
                    "telefono": documento.get("telefono", ""),
                    "direccion": documento.get("direccion", ""),
                    "ciudad": documento.get("ciudad", ""),
                    "items": documento.get("items", []),
                    "subtotal": documento.get("subtotal", 0),
                    "cupon_codigo": documento.get("cupon_codigo"),
                    "cupon_porcentaje": documento.get("cupon_porcentaje"),
                    "descuento": documento.get("descuento", 0),
                    "total": documento.get("total", 0),
                }
                for documento in documentos
            ]
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron consultar las compras") from error

    def estadisticas_almacen(self) -> list[dict[str, Any]]:
        productos = self.listar_todos_productos()
        unidades = {producto.producto_id: 0 for producto in productos}
        try:
            for compra in self.compras_almacen.find({}, {"items": 1}):
                for item in compra.get("items", []):
                    producto_id = str(item.get("producto_id"))
                    if producto_id in unidades:
                        unidades[producto_id] += int(item.get("cantidad", 0))
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron calcular las estadísticas") from error
        return [
            {
                "producto_id": producto.producto_id,
                "nombre": producto.nombre,
                "marca_variedad": producto.marca_variedad,
                "presentacion": producto.presentacion,
                "unidades_vendidas": unidades.get(producto.producto_id, 0),
            }
            for producto in productos
        ]


__all__ = ["RepositorioAlmacen"]
