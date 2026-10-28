"""Listener global que replica inventarios dedicados hacia comparador."""

import logging
import os
import time


LOGGER = logging.getLogger(__name__)
ALMACENES = ("almacen_1", "almacen_2", "almacen_3")
HISTORY_LOST_CODE = 286


class MongoChangeStreamReplicator:
    def __init__(self, uri: str, base_comparador: str = "comparador"):
        try:
            from pymongo import MongoClient
        except ImportError as error:
            raise RuntimeError(
                "MongoDB requiere instalar pymongo (pip install -r requirements.txt)"
            ) from error
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.base_comparador = base_comparador
        self.target = self.client[base_comparador].productos
        self.state = self.client[base_comparador].sync_state
        self.target.create_index([("almacen_id", 1), ("producto_id", 1)], unique=True)

    def _pipeline(self):
        return [{"$match": {
            "ns.db": {"$in": list(ALMACENES)},
            "ns.coll": "productos",
            "operationType": {"$in": ["insert", "update", "replace", "delete"]},
        }}]

    @staticmethod
    def _id_compuesto(documento, event):
        documento_id = documento.get("producto_id") if documento else None
        documento_id = documento_id or event.get("documentKey", {}).get("_id")
        almacen_id = documento.get("almacen_id") if documento else None
        if almacen_id is None:
            almacen_id = int(event["ns"]["db"].split("_")[1])
        if documento_id is None:
            raise ValueError("Evento sin producto_id/documentKey._id")
        return f"{almacen_id}_{documento_id}", int(almacen_id)

    def _replicar(self, event):
        operation = event["operationType"]
        if operation == "delete":
            compuesto, _ = self._id_compuesto(None, event)
            self.target.delete_one({"_id": compuesto})
            return

        documento = event.get("fullDocument")
        if documento is None:
            raise RuntimeError("Evento de cambio sin fullDocument")
        _, almacen_id = self._id_compuesto(documento, event)
        proyectado = dict(documento)
        producto_id = str(documento.get("producto_id", documento["_id"]))
        proyectado["_id"] = f"{almacen_id}_{producto_id}"
        proyectado["producto_id"] = producto_id
        proyectado["almacen_id"] = almacen_id
        proyectado["almacen_nombre"] = f"Almacen {almacen_id}"
        self.target.replace_one({"_id": proyectado["_id"]}, proyectado, upsert=True)

    def _punto_corte(self):
        return self.client.admin.command({"hello": 1}).get("operationTime")

    def reconciliar(self):
        ids_actuales = set()
        for nombre_db in ALMACENES:
            almacen_id = int(nombre_db.split("_")[1])
            for documento in self.client[nombre_db].productos.find():
                producto_id = str(documento.get("producto_id", documento["_id"]))
                proyectado = dict(documento)
                proyectado["_id"] = f"{almacen_id}_{producto_id}"
                proyectado["producto_id"] = producto_id
                proyectado["almacen_id"] = almacen_id
                proyectado["almacen_nombre"] = f"Almacen {almacen_id}"
                self.target.replace_one({"_id": proyectado["_id"]}, proyectado, upsert=True)
                ids_actuales.add(proyectado["_id"])
        self.target.delete_many({
            "almacen_id": {"$in": [1, 2, 3]},
            "_id": {"$nin": list(ids_actuales)},
        })

    def ejecutar(self, detener=None, max_reintentos=None):
        reintentos = 0
        resume_token = self.state.find_one({"_id": "global"})
        resume_token = resume_token.get("resume_token") if resume_token else None
        while detener is None or not detener():
            try:
                kwargs = {"full_document": "updateLookup"}
                if resume_token:
                    kwargs["resume_after"] = resume_token
                else:
                    corte = self._punto_corte()
                    self.reconciliar()
                    kwargs["start_at_operation_time"] = corte
                with self.client.watch(self._pipeline(), **kwargs) as stream:
                    for event in stream:
                        if detener is not None and detener():
                            return
                        self._replicar(event)
                        resume_token = event["_id"]
                        self.state.replace_one(
                            {"_id": "global"},
                            {"_id": "global", "resume_token": resume_token},
                            upsert=True,
                        )
                reintentos = 0
            except Exception as error:
                if getattr(error, "code", None) == HISTORY_LOST_CODE:
                    LOGGER.warning("Change stream history lost; reconciling")
                    resume_token = None
                    self.state.delete_one({"_id": "global"})
                else:
                    LOGGER.exception("Error replicando cambios de MongoDB")
                reintentos += 1
                if max_reintentos is not None and reintentos >= max_reintentos:
                    raise
                time.sleep(min(30, 2 ** min(reintentos, 5)))

    def close(self):
        self.client.close()
