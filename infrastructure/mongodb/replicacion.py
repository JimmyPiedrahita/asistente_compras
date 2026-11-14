"""Replicación con Change Streams: catálogo global y compras por almacén.

El proceso ``listener`` ejecuta ``SincronizadorCatalogo`` y ``ProyectorCompras``.
La API nunca depende de que el listener esté vivo para atender peticiones; la
consistencia es eventual y se puede reparar con los scripts de reconciliación.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from pymongo.errors import OperationFailure, PyMongoError

from core.config import Settings
from core.logging import obtener_logger

from .almacen import RepositorioAlmacen
from .conexiones import ConexionesMongo
from .global_db import (
    RepositorioAlmacenes,
    RepositorioComprasGlobal,
    RepositorioEstadoCompras,
    RepositorioReplicaCatalogo,
)
from .uri import FabricaURIs

logger = obtener_logger("asistente_compras.mongodb.replicacion")

HISTORY_LOST_CODE = 286


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class SincronizadorCatalogo:
    """Mantiene ``productos_global`` y ``cupones_global`` al día."""

    def __init__(
        self,
        settings: Settings,
        fabrica: FabricaURIs,
        conexiones: ConexionesMongo,
        repo_almacenes: RepositorioAlmacenes,
        repo_replica: RepositorioReplicaCatalogo,
    ) -> None:
        self.settings = settings
        self.fabrica = fabrica
        self.conexiones = conexiones
        self.repo_almacenes = repo_almacenes
        self.repo_replica = repo_replica
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None
        self._trabajadores: dict[str, threading.Thread] = {}
        self._candado = threading.RLock()

    def iniciar(self) -> None:
        with self._candado:
            if self._hilo is not None and self._hilo.is_alive():
                return
            self._detener.clear()
            self._hilo = threading.Thread(
                target=self._bucle_gerente, name="catalogo-gerente", daemon=True
            )
            self._hilo.start()
        logger.info("Sincronizador de catálogo iniciado")

    def detener(self) -> None:
        self._detener.set()
        with self._candado:
            hilos = list(self._trabajadores.values())
            if self._hilo is not None:
                hilos.append(self._hilo)
            self._trabajadores.clear()
        for hilo in hilos:
            hilo.join(timeout=5)
        logger.info("Sincronizador de catálogo detenido")

    def _bucle_gerente(self) -> None:
        while not self._detener.is_set():
            try:
                for almacen in self.repo_almacenes.listar():
                    if almacen.estado != "activo" or not almacen.db_name:
                        continue
                    with self._candado:
                        if almacen.almacen_id in self._trabajadores:
                            continue
                        hilo = threading.Thread(
                            target=self._trabajador,
                            args=(almacen,),
                            name=f"catalogo-{almacen.almacen_id[:8]}",
                            daemon=True,
                        )
                        self._trabajadores[almacen.almacen_id] = hilo
                        hilo.start()
            except Exception:  # pragma: no cover - diagnóstico
                logger.exception("No se pudo refrescar la lista de almacenes")
            self._detener.wait(self.settings.listener_refresh_seconds)

    def _trabajador(self, almacen: Any) -> None:
        primera_vez = True
        while not self._detener.is_set():
            try:
                self._escuchar(almacen, reconciliar=primera_vez)
                primera_vez = False
            except OperationFailure as error:
                if error.code == HISTORY_LOST_CODE:
                    logger.warning(
                        "Historial perdido para %s; se reconstruye la réplica",
                        almacen.almacen_id,
                    )
                    self.reconciliar_almacen(almacen)
                    continue
                logger.exception("Error de replicación para %s", almacen.almacen_id)
                self._detener.wait(2)
            except PyMongoError:
                logger.exception("MongoDB no disponible para %s", almacen.almacen_id)
                self._detener.wait(2)
            except Exception:  # pragma: no cover - diagnóstico
                logger.exception("Error inesperado replicando %s", almacen.almacen_id)
                self._detener.wait(2)

    def _escuchar(self, almacen: Any, *, reconciliar: bool = False) -> None:
        cliente = self.conexiones.cliente(self.fabrica.uri_catalogo())
        base = cliente.base(almacen.db_name)
        tokens = self.repo_replica.leer_tokens(almacen.almacen_id)
        base_opciones: dict[str, Any] = {
            "full_document": "updateLookup",
            "max_await_time_ms": 1000,
        }

        def opciones(coleccion: str) -> dict[str, Any]:
            actuales = dict(base_opciones)
            if tokens.get(coleccion):
                actuales["resume_after"] = tokens[coleccion]
            return actuales

        with (
            base["productos"].watch(**opciones("productos")) as stream_productos,
            base["cupones"].watch(**opciones("cupones")) as stream_cupones,
        ):
            # Un almacén creado después de arrancar el listener ya puede tener
            # catálogo. Se abre el stream primero y luego se reconcilia para no
            # perder los cambios que ocurran durante la reconstrucción.
            if reconciliar:
                self.reconciliar_almacen(almacen)
            self.repo_replica.marcar_estado(almacen.almacen_id, "activo")
            while not self._detener.is_set():
                for coleccion, stream in (
                    ("productos", stream_productos),
                    ("cupones", stream_cupones),
                ):
                    try:
                        cambio = stream.try_next()
                    except StopIteration:
                        return
                    while cambio is not None and not self._detener.is_set():
                        self._procesar(almacen, base, cambio)
                        self.repo_replica.guardar_token(
                            almacen.almacen_id, coleccion, cambio["_id"]
                        )
                        try:
                            cambio = stream.try_next()
                        except StopIteration:
                            return

    def _procesar(self, almacen: Any, base: Any, cambio: dict[str, Any]) -> None:
        coleccion = cambio["ns"]["coll"]
        operacion = cambio["operationType"]
        documento_id = cambio["documentKey"]["_id"]
        if coleccion == "productos":
            if operacion == "delete":
                self.repo_replica.eliminar_producto(almacen.almacen_id, documento_id)
                return
            documento = base["productos"].find_one({"_id": documento_id})
            if documento is None:
                self.repo_replica.eliminar_producto(almacen.almacen_id, documento_id)
            else:
                self.repo_replica.upsert_producto(almacen, documento)
            return
        if coleccion == "cupones":
            if operacion == "delete":
                self.repo_replica.eliminar_cupon(almacen.almacen_id, documento_id)
                return
            documento = base["cupones"].find_one({"_id": documento_id})
            if documento is None:
                self.repo_replica.eliminar_cupon(almacen.almacen_id, documento_id)
            else:
                self.repo_replica.upsert_cupon(almacen, documento)

    def reconciliar_almacen(self, almacen: Any) -> None:
        cliente = self.conexiones.cliente(self.fabrica.uri_catalogo())
        base = cliente.base(almacen.db_name)
        productos = list(base["productos"].find({}))
        ids_productos: set[str] = set()
        for documento in productos:
            self.repo_replica.upsert_producto(almacen, documento)
            ids_productos.add(str(documento.get("_id")))
        self.repo_replica.eliminar_productos_obsoletos(almacen.almacen_id, ids_productos)

        cupones = list(base["cupones"].find({}))
        ids_cupones: set[str] = set()
        for documento in cupones:
            self.repo_replica.upsert_cupon(almacen, documento)
            ids_cupones.add(str(documento.get("_id")))
        self.repo_replica.eliminar_cupones_obsoletos(almacen.almacen_id, ids_cupones)
        self.repo_replica.reiniciar_tokens(almacen.almacen_id)
        logger.info(
            "Catálogo reconciliado para %s: %s productos, %s cupones",
            almacen.almacen_id,
            len(productos),
            len(cupones),
        )

    def reconciliar_todo(self) -> None:
        for almacen in self.repo_almacenes.listar():
            if almacen.estado == "activo" and almacen.db_name:
                self.reconciliar_almacen(almacen)


class ProyectorCompras:
    """Proyecta la parte de cada almacén de una compra global."""

    def __init__(
        self,
        settings: Settings,
        fabrica: FabricaURIs,
        conexiones: ConexionesMongo,
        repo_almacenes: RepositorioAlmacenes,
        repo_compras: RepositorioComprasGlobal,
        repo_estado: RepositorioEstadoCompras,
    ) -> None:
        self.settings = settings
        self.fabrica = fabrica
        self.conexiones = conexiones
        self.repo_almacenes = repo_almacenes
        self.repo_compras = repo_compras
        self.repo_estado = repo_estado
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._hilo is not None and self._hilo.is_alive():
            return
        self._detener.clear()
        self._hilo = threading.Thread(target=self._bucle, name="proyector-compras", daemon=True)
        self._hilo.start()
        logger.info("Proyector de compras iniciado")

    def detener(self) -> None:
        self._detener.set()
        if self._hilo is not None:
            self._hilo.join(timeout=5)
        logger.info("Proyector de compras detenido")

    def _bucle(self) -> None:
        while not self._detener.is_set():
            try:
                self._escuchar()
            except OperationFailure as error:
                if error.code == HISTORY_LOST_CODE:
                    logger.warning("Historial perdido; se reconstruyen las compras")
                    self.reconciliar_todo()
                    self.repo_estado.guardar_token(None, estado="reconciliado")
                    continue
                logger.exception("Error del proyector de compras")
                self._detener.wait(2)
            except PyMongoError:
                logger.exception("MongoDB no disponible para el proyector")
                self._detener.wait(2)
            except Exception:  # pragma: no cover - diagnóstico
                logger.exception("Error inesperado en el proyector")
                self._detener.wait(2)

    def _escuchar(self) -> None:
        cliente = self.conexiones.cliente(self.fabrica.uri_compras())
        base = cliente.base(self.settings.mongodb_global_db)
        token = self.repo_estado.leer_token()
        opciones: dict[str, Any] = {
            "full_document": "updateLookup",
            "max_await_time_ms": 1000,
        }
        if token:
            opciones["resume_after"] = token
        with base["compras"].watch(**opciones) as stream:
            self.repo_estado.marcar_estado("activo")
            for cambio in stream:
                if self._detener.is_set():
                    return
                if cambio["operationType"] == "delete":
                    self._eliminar(str(cambio["documentKey"]["_id"]))
                else:
                    self._proyectar(cambio.get("fullDocument"))
                self.repo_estado.guardar_token(cambio["_id"])

    def _repositorio_almacen(self, almacen: Any) -> RepositorioAlmacen:
        base = self.conexiones.base(self.fabrica.uri_compras(), almacen.db_name)
        return RepositorioAlmacen(base, almacen.almacen_id)

    def _proyectar(self, compra: dict[str, Any] | None) -> None:
        if not compra:
            return
        compra_id = str(compra.get("_id"))
        entrega = compra.get("datos_entrega", {}) or {}
        for parte in compra.get("por_almacen", []) or []:
            almacen_id = str(parte.get("almacen_id"))
            almacen = self.repo_almacenes.obtener(almacen_id)
            if almacen is None or not almacen.db_name:
                continue
            items = [
                {
                    "producto_id": item.get("producto_id"),
                    "nombre": item.get("nombre"),
                    "marca_variedad": item.get("marca_variedad", ""),
                    "presentacion": item.get("presentacion"),
                    "precio_unitario": item.get("precio_unitario"),
                    "cantidad": item.get("cantidad"),
                    "importe": item.get("importe"),
                }
                for item in compra.get("items", []) or []
                if str(item.get("almacen_id")) == almacen_id
            ]
            documento = {
                "compra_id": compra_id,
                "cliente_id": compra.get("cliente_id"),
                "cliente_nombre": compra.get("cliente_nombre", ""),
                "fecha": compra.get("fecha"),
                "telefono": entrega.get("telefono", ""),
                "direccion": entrega.get("direccion", ""),
                "ciudad": entrega.get("ciudad", ""),
                "datos_entrega": entrega,
                "items": items,
                "subtotal": parte.get("subtotal", 0),
                "cupon_codigo": parte.get("cupon_codigo"),
                "cupon_porcentaje": parte.get("cupon_porcentaje"),
                "descuento": parte.get("descuento", 0),
                "total": parte.get("total", 0),
            }
            self._repositorio_almacen(almacen).upsert_compra(documento)

    def _eliminar(self, compra_id: str) -> None:
        for almacen in self.repo_almacenes.listar():
            if almacen.db_name:
                self._repositorio_almacen(almacen).eliminar_compra(compra_id)

    def reconciliar_todo(self) -> None:
        compras = self.repo_compras.listar_compras()
        ids: set[str] = set()
        for compra in compras:
            self._proyectar(compra)
            ids.add(str(compra.get("_id")))
        for almacen in self.repo_almacenes.listar():
            if not almacen.db_name:
                continue
            repositorio = self._repositorio_almacen(almacen)
            for compra_id in repositorio.listar_ids_compras() - ids:
                repositorio.eliminar_compra(compra_id)
        self.repo_estado.guardar_token(None, estado="reconciliado")
        logger.info("Compras reconciliadas: %s compras globales", len(compras))


__all__ = ["ProyectorCompras", "SincronizadorCatalogo"]
