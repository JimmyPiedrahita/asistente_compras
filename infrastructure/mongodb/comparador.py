"""Proyección integrada ``comparador`` mantenida con Change Streams.

Las bases ``warehouse_*`` son la fuente de verdad. Este módulo escucha sus
cambios y mantiene ``comparador.productos`` como un read model indexado que
permite responder búsquedas globales sin cargar el catálogo en memoria.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from pymongo import ReplaceOne
from pymongo.errors import OperationFailure, PyMongoError

from core.config import AlmacenConfig
from core.logging import obtener_logger
from models.productos import Producto

from .cliente import ClienteMongo
from .documentos import documento_comparador, id_comparador, producto_desde_documento
from .indices import crear_indices_comparador

logger = obtener_logger("asistente_compras.comparador")

HISTORY_LOST_CODE = 286
ESTADO_GLOBAL = "global"
TAMANO_LOTE = 500


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class SincronizadorComparador:
    """Mantiene ``comparador.productos`` sincronizado con los almacenes."""

    def __init__(
        self,
        uri: str,
        almacenes: Iterable[AlmacenConfig],
        *,
        comparador_db: str = "comparador",
        timeout_ms: int = 5000,
        cliente: ClienteMongo | None = None,
        intervalo_reintento: float = 1.0,
        intervalo_maximo: float = 30.0,
    ) -> None:
        self._almacenes = tuple(almacenes)
        if not self._almacenes:
            raise ValueError("Debe configurarse al menos un almacén")
        self._por_id = {almacen.id: almacen for almacen in self._almacenes}
        self._por_base = {almacen.base_datos: almacen for almacen in self._almacenes}
        self._cliente = cliente or ClienteMongo(uri, timeout_ms)
        self._cliente_propio = cliente is None
        self._comparador_db = comparador_db
        base = self._cliente.base(comparador_db)
        self.productos = base["productos"]
        self.estado_coleccion = base["sync_state"]
        self.intervalo_reintento = max(0.1, float(intervalo_reintento))
        self.intervalo_maximo = max(self.intervalo_reintento, float(intervalo_maximo))
        self._detenido = threading.Event()
        self._candado = threading.RLock()
        crear_indices_comparador(self.productos)

    # Estado ------------------------------------------------------------

    def estado(self) -> dict[str, Any]:
        documento = self.estado_coleccion.find_one({"_id": ESTADO_GLOBAL}) or {}
        return {
            "estado": documento.get("estado", "desconocido"),
            "documentos": int(self.productos.count_documents({})),
            "ultima_sincronizacion": documento.get("ultima_sincronizacion"),
            "ultimo_evento": documento.get("ultimo_evento"),
            "tiene_resume_token": bool(documento.get("resume_token")),
        }

    def _guardar_estado(self, cambios: Mapping[str, Any]) -> None:
        datos = dict(cambios)
        datos.setdefault("actualizado_en", _ahora())
        self.estado_coleccion.update_one({"_id": ESTADO_GLOBAL}, {"$set": datos}, upsert=True)

    def _cargar_token(self) -> Any | None:
        documento = self.estado_coleccion.find_one({"_id": ESTADO_GLOBAL}) or {}
        return documento.get("resume_token")

    def _guardar_token(self, token: Any, evento: str) -> None:
        self.estado_coleccion.update_one(
            {"_id": ESTADO_GLOBAL},
            {
                "$set": {
                    "estado": "sincronizado",
                    "resume_token": token,
                    "ultima_sincronizacion": _ahora(),
                    "ultimo_evento": evento,
                    "actualizado_en": _ahora(),
                }
            },
            upsert=True,
        )

    # Proyección --------------------------------------------------------

    @staticmethod
    def _pipeline(almacenes: Iterable[AlmacenConfig]) -> list[dict[str, Any]]:
        return [
            {
                "$match": {
                    "ns.db": {"$in": [almacen.base_datos for almacen in almacenes]},
                    "ns.coll": "productos",
                    "operationType": {"$in": ["insert", "update", "replace", "delete"]},
                }
            }
        ]

    def _aplicar_evento(self, evento: Mapping[str, Any]) -> str | None:
        ns = evento.get("ns") or {}
        almacen = self._por_base.get(ns.get("db"))
        if almacen is None:
            return None

        operacion = evento.get("operationType")
        # Se serializa con la reconciliación para que su marca final no borre
        # un documento proyectado por un evento concurrente.
        with self._candado:
            if operacion == "delete":
                producto_id = str((evento.get("documentKey") or {}).get("_id", ""))
                if not producto_id:
                    return None
                self.productos.delete_one({"_id": id_comparador(almacen.id, producto_id)})
                return f"delete {almacen.id}/{producto_id}"

            documento = evento.get("fullDocument")
            if not documento:
                return None
            try:
                producto = producto_desde_documento(documento)
            except (KeyError, TypeError, ValueError) as error:
                logger.warning("Evento inválido en %s: %s", almacen.base_datos, error)
                return None

            proyeccion = documento_comparador(almacen.id, almacen.nombre, producto)
            self.productos.replace_one({"_id": proyeccion["_id"]}, proyeccion, upsert=True)
            return f"{operacion} {almacen.id}/{producto.producto_id}"

    def _reconstruir(self) -> int:
        """Reconstruye la proyección completa usando una marca de ejecución."""
        marca = uuid.uuid4().hex
        inicio = _ahora()
        total = 0
        with self._candado:
            for almacen in self._almacenes:
                coleccion = self._cliente.base(almacen.base_datos)["productos"]
                operaciones: list[ReplaceOne] = []
                for documento in coleccion.find({}):
                    try:
                        producto = producto_desde_documento(documento)
                    except (KeyError, TypeError, ValueError) as error:
                        logger.warning(
                            "Documento inválido en %s durante reconciliación: %s",
                            almacen.base_datos,
                            error,
                        )
                        continue
                    proyeccion = documento_comparador(
                        almacen.id,
                        almacen.nombre,
                        producto,
                        marca_reconciliacion=marca,
                    )
                    operaciones.append(
                        ReplaceOne({"_id": proyeccion["_id"]}, proyeccion, upsert=True)
                    )
                    if len(operaciones) >= TAMANO_LOTE:
                        self.productos.bulk_write(operaciones, ordered=False)
                        total += len(operaciones)
                        operaciones.clear()
                if operaciones:
                    self.productos.bulk_write(operaciones, ordered=False)
                    total += len(operaciones)

            # Solo se eliminan documentos proyectados antes de esta
            # reconciliación. Un evento aplicado por otro proceso mientras
            # tanto (por ejemplo la API) tiene un `sincronizado_en` posterior
            # y no debe borrarse aunque no lleve esta marca.
            self.productos.delete_many(
                {
                    "_reconciliacion": {"$ne": marca},
                    "$or": [
                        {"sincronizado_en": {"$lt": inicio}},
                        {"sincronizado_en": {"$exists": False}},
                    ],
                }
            )
        return total

    def reconciliar(self, *, limpiar_token: bool = False) -> dict[str, Any]:
        """Reconstruye ``comparador`` desde las bases de los almacenes."""
        total = self._reconstruir()
        cambios: dict[str, Any] = {
            "estado": "reconciliado",
            "ultima_sincronizacion": _ahora(),
            "ultimo_evento": f"reconciliacion ({total} productos)",
        }
        if limpiar_token:
            self.estado_coleccion.update_one(
                {"_id": ESTADO_GLOBAL},
                {"$unset": {"resume_token": ""}, "$set": cambios},
                upsert=True,
            )
        else:
            self._guardar_estado(cambios)
        logger.info("Comparador reconstruido con %s productos", total)
        return {
            "documentos": int(self.productos.count_documents({})),
            "reconciliados": total,
        }

    # Bucle del listener ------------------------------------------------

    def verificar_replica_set(self) -> None:
        try:
            saludo = self._cliente.cliente.admin.command("hello")
        except PyMongoError as error:
            raise RuntimeError("No se pudo comprobar el estado de MongoDB") from error
        if not saludo.get("setName"):
            raise RuntimeError(
                "MongoDB debe ejecutarse como replica set para usar Change Streams. "
                "Arranca mongod con --replSet y ejecuta rs.initiate()."
            )

    def ejecutar(self) -> None:
        """Escucha cambios indefinidamente hasta llamar a ``detener``."""
        self.verificar_replica_set()
        self._detenido.clear()
        backoff = self.intervalo_reintento
        pipeline = self._pipeline(self._almacenes)
        token: Any | None = None
        reconstruido = False

        while not self._detenido.is_set():
            try:
                if not reconstruido:
                    token = self._cargar_token()
                    if token is None:
                        self.reconciliar()
                        self._guardar_estado(
                            {
                                "estado": "escuchando",
                                "ultima_sincronizacion": _ahora(),
                                "ultimo_evento": "listener iniciado",
                            }
                        )
                reconstruido = False
                opciones: dict[str, Any] = {
                    "full_document": "updateLookup",
                    "max_await_time_ms": 1000,
                }
                if token is not None:
                    opciones["resume_after"] = token

                with self._cliente.cliente.watch(pipeline, **opciones) as stream:
                    self._guardar_estado({"estado": "sincronizado"})
                    backoff = self.intervalo_reintento
                    while not self._detenido.is_set():
                        evento = stream.try_next()
                        if evento is None:
                            continue
                        detalle = self._aplicar_evento(evento)
                        if detalle is not None:
                            self._guardar_token(evento.get("_id"), detalle)
            except OperationFailure as error:
                if error.code == HISTORY_LOST_CODE:
                    logger.warning("Historial de cambios perdido; se reconstruye comparador")
                    self.reconciliar(limpiar_token=True)
                    self._guardar_estado(
                        {
                            "estado": "reconciliado",
                            "ultimo_evento": "historial perdido; reconstruido",
                        }
                    )
                    token = None
                    reconstruido = True
                    continue
                logger.exception("Error de MongoDB en el listener")
            except PyMongoError:
                logger.exception("Error de conexión en el listener")

            if self._detenido.is_set():
                break
            time.sleep(backoff)
            backoff = min(backoff * 2, self.intervalo_maximo)

    def detener(self) -> None:
        self._detenido.set()

    def close(self) -> None:
        self.detener()
        if self._cliente_propio:
            self._cliente.close()


def producto_proyectado(documento: Mapping[str, Any]) -> Producto:
    """Reconstruye el producto de un documento de ``comparador``."""
    return producto_desde_documento(dict(documento))


__all__ = [
    "ESTADO_GLOBAL",
    "HISTORY_LOST_CODE",
    "SincronizadorComparador",
    "producto_proyectado",
]
