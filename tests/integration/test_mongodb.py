"""Pruebas del repositorio MongoDB real.

Se ejecutan solo cuando ``MONGODB_URI`` está definida.
"""

from __future__ import annotations

import os
import unittest
import uuid

from pymongo import MongoClient

from core.errors import Conflicto, NoEncontrado
from infrastructure.mongodb.repositorio import RepositorioMongo
from models.seguridad import verificar_password

MONGODB_URI = os.getenv("MONGODB_URI")

ADMIN_EMAIL = "repo-admin@example.com"
ADMIN_PASSWORD = "RepoAdmin123"


@unittest.skipUnless(MONGODB_URI, "MONGODB_URI no configurada")
class PruebasRepositorioMongo(unittest.TestCase):
    def setUp(self) -> None:
        self.base_datos = f"test_repo_{uuid.uuid4().hex[:10]}"
        self.repo = RepositorioMongo(MONGODB_URI or "", base_datos=self.base_datos)
        self.repo.inicializar(
            admin_email=ADMIN_EMAIL,
            admin_password=ADMIN_PASSWORD,
            admin_nombre="Administrador de pruebas",
        )
        self._mongo = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)

    def tearDown(self) -> None:
        try:
            self._mongo.drop_database(self.base_datos)
        finally:
            self._mongo.close()
            self.repo.close()

    def test_cuenta_inicial_idempotente(self) -> None:
        usuario = self.repo.buscar_usuario_por_email(ADMIN_EMAIL)
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.rol, "ADMINISTRADOR_APP")  # type: ignore[union-attr]
        self.assertTrue(
            verificar_password(ADMIN_PASSWORD, usuario.password_hash)  # type: ignore[union-attr]
        )
        self.repo.inicializar(
            admin_email=ADMIN_EMAIL,
            admin_password=ADMIN_PASSWORD,
            admin_nombre="Administrador de pruebas",
        )
        self.assertEqual(self.repo.usuarios.count_documents({"rol": "ADMINISTRADOR_APP"}), 1)

    def test_almacenes_productos_y_presentacion(self) -> None:
        almacen = self.repo.crear_almacen("  Almacén   Central ")
        self.assertEqual(almacen.nombre, "Almacén Central")
        with self.assertRaises(Conflicto):
            self.repo.crear_almacen("almacén central")

        producto = self.repo.crear_producto(
            almacen_id=almacen.almacen_id,
            tipo_producto="arroz",
            nombre="Arroz Diana",
            precio="3000",
            presentacion="500 g",
        )
        self.assertEqual(producto.precio, 3000)
        self.assertEqual(self.repo.contar_productos(almacen.almacen_id), 1)
        self.assertEqual(self.repo.presentaciones_del_tipo("arroz"), {"500 g"})

        with self.assertRaises(Conflicto):
            self.repo.crear_producto(
                almacen_id=almacen.almacen_id,
                tipo_producto="arroz",
                nombre="Arroz Grande",
                precio=5000,
                presentacion="1 kg",
            )

        actualizado = self.repo.actualizar_producto(
            producto.producto_id, almacen.almacen_id, {"precio": 3200, "nombre": "Arroz Diana 2"}
        )
        self.assertEqual(actualizado.precio, 3200)
        self.assertEqual(actualizado.nombre, "Arroz Diana 2")

        with self.assertRaises(NoEncontrado):
            self.repo.actualizar_producto(producto.producto_id, "otro", {"precio": 1})
        with self.assertRaises(NoEncontrado):
            self.repo.eliminar_producto(producto.producto_id, "otro")
        self.repo.eliminar_producto(producto.producto_id, almacen.almacen_id)
        self.assertEqual(self.repo.contar_productos(almacen.almacen_id), 0)

    def test_cupones_unicos_y_por_almacen(self) -> None:
        a = self.repo.crear_almacen("Almacén A")
        b = self.repo.crear_almacen("Almacén B")
        cupon = self.repo.crear_cupon(codigo="arroz10", almacen_id=a.almacen_id, porcentaje=10)
        self.assertEqual(cupon.codigo, "ARROZ10")
        self.assertEqual(cupon.porcentaje, 10)
        with self.assertRaises(Conflicto):
            self.repo.crear_cupon(codigo="ARROZ10", almacen_id=b.almacen_id, porcentaje=20)
        with self.assertRaises(Conflicto):
            self.repo.crear_cupon(codigo="OTRO", almacen_id=a.almacen_id, porcentaje=0)

        self.assertEqual(len(self.repo.listar_cupones(a.almacen_id)), 1)
        self.assertEqual(self.repo.listar_cupones(b.almacen_id), [])
        self.assertIsNotNone(self.repo.obtener_cupon_por_codigo(" arroz10 "))

        with self.assertRaises(NoEncontrado):
            self.repo.eliminar_cupon(cupon.cupon_id, b.almacen_id)
        self.repo.eliminar_cupon(cupon.cupon_id, a.almacen_id)
        self.assertIsNone(self.repo.obtener_cupon_por_codigo("ARROZ10"))

    def test_compra_idempotente_visibilidad_y_estadisticas(self) -> None:
        a = self.repo.crear_almacen("Almacén A")
        b = self.repo.crear_almacen("Almacén B")
        p1 = self.repo.crear_producto(
            almacen_id=a.almacen_id,
            tipo_producto="arroz",
            nombre="Arroz Diana",
            precio=3000,
            presentacion="500 g",
        )
        p2 = self.repo.crear_producto(
            almacen_id=b.almacen_id,
            tipo_producto="leche",
            nombre="Leche Entera",
            precio=4500,
            presentacion="1 litro",
        )
        documento = {
            "_id": uuid.uuid4().hex,
            "cliente_nombre": "Ana",
            "datos_entrega": {
                "nombre": "Ana",
                "telefono": "3001234567",
                "direccion": "Calle 1",
                "ciudad": "Bogotá",
            },
            "items": [
                {
                    "almacen_id": a.almacen_id,
                    "almacen_nombre": "Almacén A",
                    "producto_id": p1.producto_id,
                    "tipo_producto": "arroz",
                    "nombre": "Arroz Diana",
                    "marca_variedad": "",
                    "presentacion": "500 g",
                    "precio_unitario": 3000,
                    "cantidad": 2,
                    "importe": 6000,
                },
                {
                    "almacen_id": b.almacen_id,
                    "almacen_nombre": "Almacén B",
                    "producto_id": p2.producto_id,
                    "tipo_producto": "leche",
                    "nombre": "Leche Entera",
                    "marca_variedad": "",
                    "presentacion": "1 litro",
                    "precio_unitario": 4500,
                    "cantidad": 1,
                    "importe": 4500,
                },
            ],
            "por_almacen": [
                {
                    "almacen_id": a.almacen_id,
                    "almacen_nombre": "Almacén A",
                    "subtotal": 6000,
                    "cupon_codigo": None,
                    "cupon_porcentaje": None,
                    "descuento": 0,
                    "total": 6000,
                },
                {
                    "almacen_id": b.almacen_id,
                    "almacen_nombre": "Almacén B",
                    "subtotal": 4500,
                    "cupon_codigo": None,
                    "cupon_porcentaje": None,
                    "descuento": 0,
                    "total": 4500,
                },
            ],
            "subtotal": 10500,
            "descuento_total": 0,
            "total": 10500,
            "autorizacion_datos": True,
            "pago_simulado": True,
        }

        compra, creada = self.repo.crear_compra(
            documento, cliente_id="cliente-1", clave_idempotencia="clave-1"
        )
        self.assertTrue(creada)
        repetida, creada = self.repo.crear_compra(
            documento, cliente_id="cliente-1", clave_idempotencia="clave-1"
        )
        self.assertFalse(creada)
        self.assertEqual(repetida["_id"], compra["_id"])
        self.assertEqual(self.repo.compras.count_documents({}), 1)

        compras_a = self.repo.listar_compras_por_almacen(a.almacen_id)
        self.assertEqual(len(compras_a), 1)
        self.assertEqual([item["nombre"] for item in compras_a[0]["items"]], ["Arroz Diana"])
        self.assertEqual(compras_a[0]["subtotal"], 6000)
        self.assertEqual(compras_a[0]["telefono"], "3001234567")

        compras_b = self.repo.listar_compras_por_almacen(b.almacen_id)
        self.assertEqual([item["nombre"] for item in compras_b[0]["items"]], ["Leche Entera"])

        # Producto sin ventas incluido en las estadísticas.
        self.repo.crear_producto(
            almacen_id=a.almacen_id,
            tipo_producto="arroz",
            nombre="Arroz Roa",
            precio=2500,
            presentacion="500 g",
        )
        filas = self.repo.estadisticas_almacen(a.almacen_id)
        por_nombre = {fila["nombre"]: fila["unidades_vendidas"] for fila in filas}
        self.assertEqual(por_nombre, {"Arroz Diana": 2, "Arroz Roa": 0})


if __name__ == "__main__":
    unittest.main()
