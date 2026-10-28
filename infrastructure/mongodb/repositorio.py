"""Persistencia del inventario en una base MongoDB por almacén."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError, PyMongoError

from core.config import AlmacenConfig, crear_almacenes
from core.errors import Conflicto, NoEncontrado, ServicioNoDisponible
from core.logging import obtener_logger
from models.productos import FabricaProductos, Producto
from models.texto import normalizar_texto

from .cliente import ClienteMongo
from .indices import crear_indices

logger = obtener_logger("asistente_compras.mongodb")


class MongoInventarioRepository:
    """Un repositorio con una colección ``productos`` por base de almacén."""

    def __init__(
        self,
        uri: str,
        almacenes: Iterable[AlmacenConfig] | None = None,
        *,
        prefijo_almacen: str = "warehouse",
        timeout_ms: int = 5000,
        cliente: ClienteMongo | None = None,
    ) -> None:
        configuraciones = tuple(almacenes or crear_almacenes(prefijo_almacen))
        self._almacenes = {almacen.id: almacen for almacen in configuraciones}
        self._cliente = cliente or ClienteMongo(uri, timeout_ms)
        self._colecciones: dict[int, Any] = {}

        try:
            for id_almacen, configuracion in self._almacenes.items():
                coleccion = self._cliente.base(configuracion.base_datos)["productos"]
                crear_indices(coleccion)
                self._colecciones[id_almacen] = coleccion
        except PyMongoError as error:
            self._cliente.close()
            raise ServicioNoDisponible(
                "No se pudieron preparar las colecciones de MongoDB"
            ) from error

    @property
    def client(self):  # compatibilidad con código anterior
        return self._cliente.cliente

    def _coleccion(self, id_almacen: int):
        try:
            return self._colecciones[int(id_almacen)]
        except (KeyError, TypeError, ValueError) as error:
            raise NoEncontrado(f"Almacén no encontrado: {id_almacen}") from error

    @staticmethod
    def _documento(producto: Producto) -> dict[str, Any]:
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

    @staticmethod
    def _producto(documento: dict[str, Any]) -> Producto:
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

    def cargar_almacen(self, id_almacen: int) -> list[Producto]:
        try:
            documentos = (
                self._coleccion(id_almacen)
                .find({})
                .sort([("nombre_normalizado", 1), ("marca_normalizada", 1)])
            )
            productos: list[Producto] = []
            for documento in documentos:
                try:
                    productos.append(self._producto(documento))
                except (KeyError, TypeError, ValueError) as error:
                    logger.warning("Documento inválido en almacén %s: %s", id_almacen, error)
            return productos
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo leer el inventario desde MongoDB") from error

    def insertar(self, id_almacen: int, producto: Producto) -> None:
        documento = self._documento(producto)
        documento["creado_en"] = datetime.now(timezone.utc)
        try:
            self._coleccion(id_almacen).insert_one(documento)
        except DuplicateKeyError as error:
            raise Conflicto(
                f"El producto {producto.producto_id} ya existe en el almacén"
            ) from error
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo guardar el producto en MongoDB") from error

    def actualizar(self, id_almacen: int, producto: Producto) -> None:
        documento = self._documento(producto)
        documento.pop("_id", None)
        documento["actualizado_en"] = datetime.now(timezone.utc)
        try:
            resultado = self._coleccion(id_almacen).update_one(
                {"_id": producto.producto_id}, {"$set": documento}
            )
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo actualizar el producto en MongoDB") from error
        if resultado.matched_count != 1:
            raise NoEncontrado(f"Producto no encontrado: {producto.producto_id}")

    def upsert_por_nombre_marca(self, id_almacen: int, producto: Producto) -> str:
        """Inserta o actualiza por nombre+marca. Se usa en el seed idempotente."""
        coleccion = self._coleccion(id_almacen)
        try:
            existente = coleccion.find_one(
                {
                    "nombre_normalizado": normalizar_texto(producto.nombre),
                    "marca_normalizada": normalizar_texto(producto.marca),
                }
            )
            if existente is not None:
                documento = self._documento(producto)
                documento.pop("_id", None)
                documento["actualizado_en"] = datetime.now(timezone.utc)
                coleccion.update_one({"_id": existente["_id"]}, {"$set": documento})
                return "actualizado"

            documento = self._documento(producto)
            documento["creado_en"] = datetime.now(timezone.utc)
            coleccion.insert_one(documento)
            return "insertado"
        except DuplicateKeyError as error:
            raise Conflicto(
                f"El producto {producto.producto_id} ya existe en el almacén"
            ) from error
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo sincronizar el producto con MongoDB") from error

    def contar(self, id_almacen: int) -> int:
        try:
            return int(self._coleccion(id_almacen).count_documents({}))
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo contar el inventario en MongoDB") from error

    def ping(self) -> None:
        self._cliente.ping()

    def close(self) -> None:
        self._cliente.close()


__all__ = ["MongoInventarioRepository"]
