"""Pruebas de integración de los repositorios MongoDB.

Se ejecutan solo cuando ``MONGODB_URI`` está definida. Cada prueba crea una base
global temporal y, mediante el servicio de aprovisionamiento, una o más bases
de almacén que se eliminan al terminar.

La consistencia entre la base global y las bases de almacén es eventual. Como
el listener no corre en estas pruebas, la reconciliación se ejecuta de forma
explícita.
"""

from __future__ import annotations

import os
import unittest
import uuid

from pymongo import MongoClient

from core.config import Settings
from core.errors import Conflicto, NoEncontrado
from infrastructure.mongodb.contexto import construir_contexto
from models.permisos import ADMINISTRADOR_APP
from models.productos import Producto
from models.seguridad import verificar_password

MONGODB_URI = os.getenv("MONGODB_URI")

ADMIN_EMAIL = "repo-admin@example.com"
ADMIN_PASSWORD = "RepoAdmin123"


@unittest.skipUnless(MONGODB_URI, "MONGODB_URI no configurada")
class PruebasRepositoriosMongo(unittest.TestCase):
    def setUp(self) -> None:
        self.base_datos = f"test_repo_{uuid.uuid4().hex[:10]}"
        self._mongo = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        self._mongo.drop_database(self.base_datos)
        self.settings = Settings.de_pruebas(
            mongodb_uri=MONGODB_URI or "",
            mongodb_db=self.base_datos,
            admin_email=ADMIN_EMAIL,
            admin_password=ADMIN_PASSWORD,
        )
        self.ctx = construir_contexto(self.settings)

    def tearDown(self) -> None:
        try:
            for almacen in self.ctx.repo_almacenes.listar():
                if almacen.db_name:
                    self._mongo.drop_database(almacen.db_name)
            self._mongo.drop_database(self.base_datos)
        finally:
            self._mongo.close()
            self.ctx.cerrar()

    # Utilidades -------------------------------------------------------
    def _crear_almacen(self, nombre: str):
        return self.ctx.aprovisionamiento.crear_almacen(nombre)

    def _crear_producto(
        self,
        almacen_id: str,
        *,
        tipo: str = "arroz",
        nombre: str = "Arroz Diana",
        precio: float = 3000,
        presentacion: str = "500 g",
        marca: str = "Diana",
    ) -> Producto:
        return Producto.crear(
            producto_id=uuid.uuid4().hex,
            almacen_id=almacen_id,
            tipo_producto=tipo,
            nombre=nombre,
            precio=precio,
            presentacion=presentacion,
            marca_variedad=marca,
        )

    # Pruebas ----------------------------------------------------------
    def test_cuenta_inicial_idempotente(self) -> None:
        usuario = self.ctx.repo_usuarios.buscar_usuario_por_email(ADMIN_EMAIL)
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.rol, ADMINISTRADOR_APP)  # type: ignore[union-attr]
        self.assertTrue(
            verificar_password(ADMIN_PASSWORD, usuario.password_hash)  # type: ignore[union-attr]
        )

        self.ctx.repo_usuarios.asegurar_admin(
            admin_email=ADMIN_EMAIL,
            admin_password=ADMIN_PASSWORD,
            admin_nombre="Administrador de pruebas",
        )
        self.assertEqual(
            self._mongo[self.base_datos]["usuarios"].count_documents({"rol": ADMINISTRADOR_APP}),
            1,
        )

    def test_aprovisionamiento_y_aislamiento_entre_almacenes(self) -> None:
        a = self._crear_almacen("  Almacén   Central ")
        self.assertEqual(a.nombre, "Almacén Central")
        self.assertEqual(a.estado, "activo")
        self.assertTrue(a.db_name.startswith("almacen_"))
        self.assertTrue(a.mongo_user.endswith("_app"))

        b = self._crear_almacen("Almacén Norte")
        self.assertNotEqual(a.db_name, b.db_name)
        self.assertNotEqual(a.mongo_user, b.mongo_user)

        with self.assertRaises(Conflicto):
            self._crear_almacen("almacén central")

        repo_a = self.ctx.directorio.repositorio(a.almacen_id)
        repo_b = self.ctx.directorio.repositorio(b.almacen_id)
        producto = self._crear_producto(a.almacen_id)
        repo_a.insertar_producto(producto)

        self.assertIsNotNone(repo_a.obtener_producto(producto.producto_id))
        self.assertIsNone(repo_b.obtener_producto(producto.producto_id))
        self.assertEqual(repo_a.listar_productos()[1], 1)
        self.assertEqual(repo_b.listar_productos()[1], 0)
        self.assertEqual(self.ctx.repo_almacenes.contar_productos(), 0)

        # El repositorio de un almacén nunca opera sobre otro.
        with self.assertRaises(NoEncontrado):
            repo_b.eliminar_producto(producto.producto_id)
        self.assertIsNotNone(repo_a.obtener_producto(producto.producto_id))

        repo_a.eliminar_producto(producto.producto_id)
        self.assertIsNone(repo_a.obtener_producto(producto.producto_id))

    def test_presentacion_global_y_replicacion_de_catalogo(self) -> None:
        almacen = self._crear_almacen("Almacén Central")
        repo = self.ctx.directorio.repositorio(almacen.almacen_id)
        producto = self._crear_producto(almacen.almacen_id)
        repo.insertar_producto(producto)

        self.assertEqual(repo.presentaciones_del_tipo("arroz"), {"500 g"})

        # Sin listener, la réplica global se reconstruye explícitamente.
        self.ctx.sincronizador.reconciliar_almacen(almacen)
        replicado = self.ctx.repo_catalogo.obtener_producto(producto.producto_id)
        self.assertIsNotNone(replicado)
        self.assertEqual(replicado.almacen_id, almacen.almacen_id)  # type: ignore[union-attr]
        self.assertEqual(self.ctx.repo_almacenes.contar_productos(almacen.almacen_id), 1)

        valido = self._crear_producto(almacen.almacen_id, nombre="Arroz Roa")
        self.ctx.validador.validar_presentacion(
            valido, locales=repo.presentaciones_del_tipo("arroz")
        )

        invalido = self._crear_producto(
            almacen.almacen_id, nombre="Arroz Grande", presentacion="1 kg"
        )
        with self.assertRaises(Conflicto):
            self.ctx.validador.validar_presentacion(
                invalido, locales=repo.presentaciones_del_tipo("arroz")
            )

        # Cada colección mantiene su propio token de Change Stream.
        self.ctx.repo_replica.guardar_token(
            almacen.almacen_id, "productos", {"_data": "token-productos"}
        )
        self.ctx.repo_replica.guardar_token(
            almacen.almacen_id, "cupones", {"_data": "token-cupones"}
        )
        self.assertEqual(
            set(self.ctx.repo_replica.leer_tokens(almacen.almacen_id)),
            {"productos", "cupones"},
        )
        self.ctx.repo_replica.reiniciar_tokens(almacen.almacen_id)
        self.assertEqual(self.ctx.repo_replica.leer_tokens(almacen.almacen_id), {})

        # Al eliminar el producto, la reconciliación limpia la réplica global.
        repo.eliminar_producto(producto.producto_id)
        self.ctx.sincronizador.reconciliar_almacen(almacen)
        self.assertIsNone(self.ctx.repo_catalogo.obtener_producto(producto.producto_id))

    def test_cupones_unicos_y_replicados_a_la_base_global(self) -> None:
        a = self._crear_almacen("Almacén A")
        b = self._crear_almacen("Almacén B")
        repo_a = self.ctx.directorio.repositorio(a.almacen_id)
        repo_b = self.ctx.directorio.repositorio(b.almacen_id)

        cupon = repo_a.crear_cupon(codigo="arroz10", porcentaje=10)
        self.assertEqual(cupon.codigo, "ARROZ10")
        self.assertEqual(cupon.porcentaje, 10)

        with self.assertRaises(Conflicto):
            repo_a.crear_cupon(codigo="ARROZ10", porcentaje=20)
        with self.assertRaises(Conflicto):
            repo_a.crear_cupon(codigo="OTRO", porcentaje=0)

        self.ctx.sincronizador.reconciliar_almacen(a)
        global_ = self.ctx.repo_catalogo.obtener_cupon_por_codigo(" arroz10 ")
        self.assertIsNotNone(global_)
        self.assertEqual(global_.almacen_id, a.almacen_id)  # type: ignore[union-attr]

        # La unicidad global se valida con la conexión de solo lectura.
        with self.assertRaises(Conflicto):
            self.ctx.validador.validar_cupon_unico("arroz10")

        self.assertEqual(len(repo_a.listar_cupones()), 1)
        self.assertEqual(repo_b.listar_cupones(), [])
        self.assertIsNotNone(repo_a.obtener_cupon_por_codigo(" arroz10 "))
        self.assertIsNone(repo_b.obtener_cupon_por_codigo("ARROZ10"))

        with self.assertRaises(NoEncontrado):
            repo_b.eliminar_cupon(cupon.cupon_id)
        repo_a.eliminar_cupon(cupon.cupon_id)
        self.ctx.sincronizador.reconciliar_almacen(a)

        self.assertIsNone(self.ctx.repo_catalogo.obtener_cupon_por_codigo("ARROZ10"))
        self.ctx.validador.validar_cupon_unico("ARROZ10")

    def test_compra_idempotente_proyeccion_y_estadisticas(self) -> None:
        a = self._crear_almacen("Almacén A")
        b = self._crear_almacen("Almacén B")
        repo_a = self.ctx.directorio.repositorio(a.almacen_id)
        repo_b = self.ctx.directorio.repositorio(b.almacen_id)

        p1 = self._crear_producto(a.almacen_id)
        p2 = self._crear_producto(
            b.almacen_id,
            tipo="leche",
            nombre="Leche Entera",
            precio=4500,
            presentacion="1 litro",
            marca="Alpina",
        )
        repo_a.insertar_producto(p1)
        repo_b.insertar_producto(p2)

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
                    "marca_variedad": "Diana",
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
                    "marca_variedad": "Alpina",
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
            "pago": True,
        }

        compra, creada = self.ctx.repo_compras.crear_compra(
            documento, cliente_id="cliente-1", clave_idempotencia="clave-1"
        )
        self.assertTrue(creada)
        repetida, creada = self.ctx.repo_compras.crear_compra(
            documento, cliente_id="cliente-1", clave_idempotencia="clave-1"
        )
        self.assertFalse(creada)
        self.assertEqual(repetida["_id"], compra["_id"])
        self.assertEqual(self._mongo[self.base_datos]["compras"].count_documents({}), 1)

        # El proyector no corre en las pruebas: se reconcilian las compras.
        self.ctx.proyector.reconciliar_todo()

        compras_a = repo_a.listar_compras_por_almacen()
        self.assertEqual(len(compras_a), 1)
        self.assertEqual([item["nombre"] for item in compras_a[0]["items"]], ["Arroz Diana"])
        self.assertEqual(compras_a[0]["subtotal"], 6000)
        self.assertEqual(compras_a[0]["telefono"], "3001234567")

        compras_b = repo_b.listar_compras_por_almacen()
        self.assertEqual(len(compras_b), 1)
        self.assertEqual([item["nombre"] for item in compras_b[0]["items"]], ["Leche Entera"])
        self.assertEqual(compras_b[0]["total"], 4500)

        # Producto sin ventas incluido en las estadísticas.
        p3 = self._crear_producto(a.almacen_id, nombre="Arroz Roa", precio=2500)
        repo_a.insertar_producto(p3)
        filas = repo_a.estadisticas_almacen()
        por_nombre = {fila["nombre"]: fila["unidades_vendidas"] for fila in filas}
        self.assertEqual(por_nombre, {"Arroz Diana": 2, "Arroz Roa": 0})


if __name__ == "__main__":
    unittest.main()
