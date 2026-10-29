"""Pruebas de integración con MongoDB real.

Se omiten si no existe ``MONGODB_URI``. En CI se levanta un replica set de un
nodo para poder probar Change Streams.
"""

from __future__ import annotations

import os
import threading
import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from core.config import Settings
from core.errors import NoEncontrado
from infrastructure.mongodb import (
    MongoInventarioRepository,
    SincronizadorComparador,
)
from infrastructure.mongodb.documentos import documento_comparador
from models.productos import Producto

MONGODB_URI = os.getenv("MONGODB_URI")


@unittest.skipUnless(MONGODB_URI, "MONGODB_URI no configurada")
class PruebasMongo(unittest.TestCase):
    def setUp(self) -> None:
        self.prefijo = f"test_{uuid.uuid4().hex[:10]}"
        self.settings = Settings.de_pruebas(
            mongodb_uri=MONGODB_URI or "",
            mongodb_db_prefix=self.prefijo,
            mongodb_comparador_db=f"{self.prefijo}_comparador",
        )
        self.repo = MongoInventarioRepository(
            self.settings.mongodb_uri,
            self.settings.almacenes,
            comparador_db=self.settings.mongodb_comparador_db,
            timeout_ms=3000,
        )

    def tearDown(self) -> None:
        try:
            for almacen in self.settings.almacenes:
                self.repo.client.drop_database(almacen.base_datos)
            self.repo.client.drop_database(self.settings.mongodb_comparador_db)
        finally:
            self.repo.close()

    @staticmethod
    def _esperar(condicion, segundos: float = 15.0) -> None:
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            if condicion():
                return
            time.sleep(0.1)
        raise AssertionError("La condición no se cumplió dentro del tiempo esperado")

    def test_aislamiento_entre_almacenes(self) -> None:
        producto = Producto("Leche", 100, "Ilolay")
        self.repo.insertar(1, producto)

        almacen_1 = self.repo.cargar_almacen(1)
        almacen_2 = self.repo.cargar_almacen(2)
        self.assertEqual(len(almacen_1), 1)
        self.assertEqual(len(almacen_2), 0)
        self.assertEqual(almacen_1[0].producto_id, producto.producto_id)
        self.assertEqual(self.repo.contar(1), 1)
        self.assertEqual(self.repo.contar(2), 0)

    def test_actualizar_y_ping(self) -> None:
        producto = Producto("Pan", 50, "Bimbo")
        self.repo.insertar(1, producto)
        cargado = self.repo.cargar_almacen(1)[0]
        cargado.precio = 75
        self.repo.actualizar(1, cargado)

        actualizado = self.repo.cargar_almacen(1)[0]
        self.assertEqual(actualizado.precio, 75)
        self.repo.ping()

    def test_upsert_idempotente(self) -> None:
        producto = Producto("Café", 10, "Marca")
        self.assertEqual(self.repo.upsert_por_nombre_marca(1, producto), "insertado")
        producto.precio = 20
        self.assertEqual(self.repo.upsert_por_nombre_marca(1, producto), "actualizado")
        self.assertEqual(self.repo.contar(1), 1)
        self.assertEqual(self.repo.cargar_almacen(1)[0].precio, 20)

    def test_indices(self) -> None:
        coleccion = self.repo.client[self.settings.almacenes[0].base_datos]["productos"]
        indices = coleccion.index_information()
        campos = [info["key"] for info in indices.values()]
        self.assertIn([("nombre_normalizado", 1)], campos)
        self.assertIn([("nombre_normalizado", 1), ("marca_normalizada", 1)], campos)

    def test_indices_comparador(self) -> None:
        coleccion = self.repo.client[self.settings.mongodb_comparador_db]["productos"]
        indices = coleccion.index_information()
        campos = [info["key"] for info in indices.values()]
        self.assertIn([("nombre_normalizado", 1), ("precio_final", 1)], campos)
        self.assertIn(
            [("almacen_id", 1), ("nombre_normalizado", 1), ("precio_final", 1)],
            campos,
        )

    def test_listado_paginado_y_eliminar(self) -> None:
        for nombre in ("Arroz", "Cafe", "Aceite"):
            self.repo.insertar(1, Producto(nombre, 100))

        productos, total = self.repo.listar_productos(1, limit=1, offset=1)
        self.assertEqual(total, 3)
        self.assertEqual(len(productos), 1)

        self.repo.eliminar(1, productos[0].producto_id)
        self.assertEqual(self.repo.contar(1), 2)
        with self.assertRaises(NoEncontrado):
            self.repo.eliminar(1, productos[0].producto_id)

    def test_comparador_reconstruccion_y_busquedas(self) -> None:
        self.repo.insertar(1, Producto("Arroz", 1000, "Gallo"))
        self.repo.insertar(2, Producto("Arroz", 900, "Marolio"))
        self.repo.insertar(3, Producto("Cafe", 500, "Nestle"))

        resultado = self.repo.reconciliar_comparador()
        self.assertEqual(resultado["documentos"], 3)

        globales = self.repo.buscar_global(["Arroz"])
        self.assertEqual(len(globales), 1)
        self.assertEqual(globales[0]["almacen"].id_almacen, 2)
        self.assertEqual(globales[0]["precio"], 900)

        por_almacen = self.repo.buscar_mejor_precio(["Arroz"])
        self.assertEqual(len(por_almacen), 2)

        catalogo = self.repo.buscar_catalogo(["Arroz"], limit=1, offset=0)
        self.assertEqual(sum(len(lista) for lista in catalogo.values()), 1)

        estado = self.repo.estado_comparador()
        self.assertEqual(estado["documentos"], 3)

    def _coleccion_comparador(self):
        return self.repo.client[self.settings.mongodb_comparador_db]["productos"]

    def test_reconciliacion_elimina_documentos_obsoletos(self) -> None:
        self.repo.insertar(1, Producto("Arroz", 1000, "Gallo"))
        self.repo.reconciliar_comparador()

        fantasma = documento_comparador(
            1,
            "Almacen 1",
            Producto("Fantasma", 50),
            sincronizado_en=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        coleccion = self._coleccion_comparador()
        coleccion.replace_one({"_id": fantasma["_id"]}, fantasma, upsert=True)

        resultado = self.repo.reconciliar_comparador()
        self.assertEqual(resultado["documentos"], 1)
        self.assertIsNone(coleccion.find_one({"_id": fantasma["_id"]}))

    def test_reconciliacion_conserva_eventos_posteriores(self) -> None:
        self.repo.insertar(1, Producto("Arroz", 1000, "Gallo"))
        reciente = documento_comparador(
            1,
            "Almacen 1",
            Producto("Evento reciente", 10),
            sincronizado_en=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        coleccion = self._coleccion_comparador()
        coleccion.replace_one({"_id": reciente["_id"]}, reciente, upsert=True)

        # Simula un evento aplicado por otro proceso durante la reconciliación:
        # no lleva la marca de esta ejecución pero es posterior a su inicio.
        self.repo.reconciliar_comparador()
        self.assertIsNotNone(coleccion.find_one({"_id": reciente["_id"]}))

    def test_change_streams_propagan_cambios(self) -> None:
        sincronizador = SincronizadorComparador(
            self.settings.mongodb_uri,
            self.settings.almacenes,
            comparador_db=self.settings.mongodb_comparador_db,
            timeout_ms=3000,
        )
        try:
            sincronizador.verificar_replica_set()
        except RuntimeError:
            sincronizador.close()
            self.skipTest("MongoDB no está configurado como replica set")

        hilo = threading.Thread(target=sincronizador.ejecutar, daemon=True)
        hilo.start()
        try:
            self._esperar(
                lambda: sincronizador.estado().get("estado") in {"sincronizado", "escuchando"}
            )

            producto = Producto("Leche", 100, "Ilolay")
            self.repo.insertar(1, producto)
            self._esperar(lambda: bool(self.repo.buscar_global(["Leche"])))

            producto.precio = 80
            self.repo.actualizar(1, producto)
            self._esperar(lambda: self.repo.buscar_global(["Leche"])[0]["precio"] == 80)

            self.repo.eliminar(1, producto.producto_id)
            self._esperar(lambda: not self.repo.buscar_global(["Leche"]))
        finally:
            sincronizador.detener()
            hilo.join(timeout=10)
            sincronizador.close()


if __name__ == "__main__":
    unittest.main()
