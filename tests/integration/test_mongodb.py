"""Pruebas de integración con MongoDB real.

Se omiten si no existe ``MONGODB_URI``. En CI se levanta un servicio MongoDB.
"""

from __future__ import annotations

import os
import unittest
import uuid

from core.config import Settings
from infrastructure.mongodb import MongoInventarioRepository
from models.productos import Producto

MONGODB_URI = os.getenv("MONGODB_URI")


@unittest.skipUnless(MONGODB_URI, "MONGODB_URI no configurada")
class PruebasMongo(unittest.TestCase):
    def setUp(self) -> None:
        prefijo = f"test_{uuid.uuid4().hex[:10]}"
        self.settings = Settings.de_pruebas(
            mongodb_uri=MONGODB_URI or "",
            mongodb_db_prefix=prefijo,
        )
        self.repo = MongoInventarioRepository(
            self.settings.mongodb_uri,
            self.settings.almacenes,
            timeout_ms=3000,
        )

    def tearDown(self) -> None:
        try:
            for almacen in self.settings.almacenes:
                self.repo.client.drop_database(almacen.base_datos)
        finally:
            self.repo.close()

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


if __name__ == "__main__":
    unittest.main()
