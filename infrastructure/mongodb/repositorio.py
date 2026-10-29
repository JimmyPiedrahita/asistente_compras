"""Persistencia del inventario en una base MongoDB por almacén.

Las escrituras van únicamente a ``warehouse_*``. La base ``comparador`` es un
read model mantenido por ``SincronizadorComparador`` mediante Change Streams y
se usa para búsquedas globales indexadas.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError, PyMongoError

from core.config import AlmacenConfig, crear_almacenes
from core.errors import Conflicto, NoEncontrado, ServicioNoDisponible
from core.logging import obtener_logger
from models.almacenes import Almacen
from models.listas import ListaSimple
from models.productos import Producto
from models.texto import normalizar_texto

from .cliente import ClienteMongo
from .comparador import SincronizadorComparador
from .documentos import documento_producto, producto_desde_documento
from .indices import crear_indices, crear_indices_comparador

logger = obtener_logger("asistente_compras.mongodb")


def _normalizar_nombres(nombres: Iterable[str]) -> list[str]:
    return sorted({normalizar_texto(nombre) for nombre in nombres if normalizar_texto(nombre)})


class MongoInventarioRepository:
    """Repositorio de almacenes y consultas sobre la proyección integrada."""

    def __init__(
        self,
        uri: str,
        almacenes: Iterable[AlmacenConfig] | None = None,
        *,
        prefijo_almacen: str = "warehouse",
        comparador_db: str = "comparador",
        timeout_ms: int = 5000,
        cliente: ClienteMongo | None = None,
    ) -> None:
        configuraciones = tuple(almacenes or crear_almacenes(prefijo_almacen))
        self._almacenes = {almacen.id: almacen for almacen in configuraciones}
        self._modelos = {
            almacen.id: Almacen(almacen.id, almacen.nombre) for almacen in configuraciones
        }
        self._cliente = cliente or ClienteMongo(uri, timeout_ms)
        self._colecciones: dict[int, Any] = {}

        try:
            for id_almacen, configuracion in self._almacenes.items():
                coleccion = self._cliente.base(configuracion.base_datos)["productos"]
                crear_indices(coleccion)
                self._colecciones[id_almacen] = coleccion

            base_comparador = self._cliente.base(comparador_db)
            self._comparador = base_comparador["productos"]
            crear_indices_comparador(self._comparador)
        except PyMongoError as error:
            self._cliente.close()
            raise ServicioNoDisponible(
                "No se pudieron preparar las colecciones de MongoDB"
            ) from error

        self.comparador_db = comparador_db
        self._sincronizador = SincronizadorComparador(
            uri,
            configuraciones,
            comparador_db=comparador_db,
            timeout_ms=timeout_ms,
            cliente=self._cliente,
        )

    @property
    def client(self):  # compatibilidad con código anterior
        return self._cliente.cliente

    def _coleccion(self, id_almacen: int):
        try:
            return self._colecciones[int(id_almacen)]
        except (KeyError, TypeError, ValueError) as error:
            raise NoEncontrado(f"Almacén no encontrado: {id_almacen}") from error

    def _modelo(self, id_almacen: int) -> Almacen | None:
        try:
            return self._modelos[int(id_almacen)]
        except (KeyError, TypeError, ValueError):
            return None

    # Lectura por almacén ------------------------------------------------

    @staticmethod
    def _documento(producto: Producto) -> dict[str, Any]:
        return documento_producto(producto)

    @staticmethod
    def _producto(documento: dict[str, Any]) -> Producto:
        return producto_desde_documento(documento)

    def cargar_almacen(self, id_almacen: int) -> list[Producto]:
        """Compatibilidad: carga completa de un almacén.

        La API no usa este método para operar; existe para scripts y pruebas.
        """
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

    def listar_productos(
        self, id_almacen: int, limit: int = 100, offset: int = 0
    ) -> tuple[list[Producto], int]:
        """Devuelve una página del inventario y el total de documentos."""
        limite = max(1, int(limit))
        desplazamiento = max(0, int(offset))
        coleccion = self._coleccion(id_almacen)
        try:
            total = int(coleccion.count_documents({}))
            documentos = (
                coleccion.find({})
                .sort([("nombre_normalizado", 1), ("marca_normalizada", 1), ("_id", 1)])
                .skip(desplazamiento)
                .limit(limite)
            )
            productos: list[Producto] = []
            for documento in documentos:
                try:
                    productos.append(self._producto(documento))
                except (KeyError, TypeError, ValueError) as error:
                    logger.warning("Documento inválido en almacén %s: %s", id_almacen, error)
            return productos, total
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo listar el inventario") from error

    def producto_en_indice(self, id_almacen: int, indice: int) -> Producto | None:
        try:
            posicion = int(indice)
        except (TypeError, ValueError):
            return None
        if posicion < 0:
            return None
        productos, _ = self.listar_productos(id_almacen, limit=1, offset=posicion)
        return productos[0] if productos else None

    def obtener_producto(self, id_almacen: int, producto_id: str) -> Producto | None:
        try:
            documento = self._coleccion(id_almacen).find_one({"_id": str(producto_id)})
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo consultar el producto") from error
        if documento is None:
            return None
        try:
            return self._producto(documento)
        except (KeyError, TypeError, ValueError):
            return None

    def existe_nombre_marca(self, id_almacen: int, nombre: str, marca: str | None = None) -> bool:
        filtro: dict[str, Any] = {"nombre_normalizado": normalizar_texto(nombre)}
        if marca is not None:
            filtro["marca_normalizada"] = normalizar_texto(marca)
        try:
            return self._coleccion(id_almacen).find_one(filtro, {"_id": 1}) is not None
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo consultar el inventario") from error

    # Escritura ----------------------------------------------------------

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

    def eliminar(self, id_almacen: int, producto_id: str) -> None:
        try:
            resultado = self._coleccion(id_almacen).delete_one({"_id": str(producto_id)})
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo eliminar el producto") from error
        if resultado.deleted_count != 1:
            raise NoEncontrado(f"Producto no encontrado: {producto_id}")

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

    # Consultas sobre comparador ----------------------------------------

    def _fila(self, documento: dict[str, Any]) -> tuple[Almacen, Producto] | None:
        almacen = self._modelo(int(documento.get("almacen_id", 0)))
        if almacen is None:
            return None
        try:
            producto = self._producto(documento)
        except (KeyError, TypeError, ValueError) as error:
            logger.warning("Documento inválido en comparador: %s", error)
            return None
        return almacen, producto

    def _agrupar(self, documentos: Iterable[dict[str, Any]]) -> dict[Almacen, ListaSimple]:
        resultado: dict[Almacen, ListaSimple] = {}
        for documento in documentos:
            fila = self._fila(documento)
            if fila is None:
                continue
            almacen, producto = fila
            resultado.setdefault(almacen, ListaSimple()).agregar(producto)
        return resultado

    def buscar_mejor_precio(self, nombres: Iterable[str]) -> dict[Almacen, ListaSimple]:
        """El producto más barato de cada nombre dentro de cada almacén."""
        normalizados = _normalizar_nombres(nombres)
        if not normalizados:
            return {}
        pipeline = [
            {"$match": {"nombre_normalizado": {"$in": normalizados}}},
            {
                "$sort": {
                    "almacen_id": 1,
                    "nombre_normalizado": 1,
                    "precio_final": 1,
                    "_id": 1,
                }
            },
            {
                "$group": {
                    "_id": {
                        "almacen_id": "$almacen_id",
                        "nombre_normalizado": "$nombre_normalizado",
                    },
                    "documento": {"$first": "$$ROOT"},
                }
            },
            {"$sort": {"_id.almacen_id": 1, "_id.nombre_normalizado": 1}},
        ]
        try:
            documentos = list(self._comparador.aggregate(pipeline))
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo consultar comparador") from error
        return self._agrupar(documento["documento"] for documento in documentos)

    def buscar_catalogo(
        self, nombres: Iterable[str], limit: int = 100, offset: int = 0
    ) -> dict[Almacen, ListaSimple]:
        """Todas las coincidencias, paginadas, agrupadas por almacén."""
        normalizados = _normalizar_nombres(nombres)
        if not normalizados:
            return {}
        limite = max(1, int(limit))
        desplazamiento = max(0, int(offset))
        try:
            documentos = (
                self._comparador.find({"nombre_normalizado": {"$in": normalizados}})
                .sort(
                    [
                        ("almacen_id", 1),
                        ("nombre_normalizado", 1),
                        ("precio_final", 1),
                        ("_id", 1),
                    ]
                )
                .skip(desplazamiento)
                .limit(limite)
            )
            return self._agrupar(documentos)
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo consultar comparador") from error

    def buscar_global(self, nombres: Iterable[str]) -> list[dict[str, Any]]:
        """El producto más barato de cada nombre entre todos los almacenes."""
        normalizados = _normalizar_nombres(nombres)
        if not normalizados:
            return []
        pipeline = [
            {"$match": {"nombre_normalizado": {"$in": normalizados}}},
            {
                "$sort": {
                    "nombre_normalizado": 1,
                    "precio_final": 1,
                    "_id": 1,
                }
            },
            {
                "$group": {
                    "_id": "$nombre_normalizado",
                    "documento": {"$first": "$$ROOT"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        try:
            documentos = list(self._comparador.aggregate(pipeline))
        except PyMongoError as error:
            raise ServicioNoDisponible("No se pudo consultar comparador") from error

        resultado: list[dict[str, Any]] = []
        for item in documentos:
            fila = self._fila(item["documento"])
            if fila is None:
                continue
            almacen, producto = fila
            resultado.append(
                {
                    "nombre": producto.nombre,
                    "producto": producto,
                    "almacen": almacen,
                    "precio": producto.obtener_precio_final(),
                }
            )
        return resultado

    def estado_comparador(self) -> dict[str, Any]:
        return self._sincronizador.estado()

    def reconciliar_comparador(self) -> dict[str, Any]:
        return self._sincronizador.reconciliar()

    # Ciclo de vida ------------------------------------------------------

    def ping(self) -> None:
        self._cliente.ping()

    def close(self) -> None:
        self._sincronizador.close()
        self._cliente.close()


__all__ = ["MongoInventarioRepository"]
