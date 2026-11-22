"""Pruebas de la fábrica de URIs y de las credenciales por almacén."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from urllib.parse import quote_plus

from core.config import Settings
from infrastructure.mongodb.uri import FabricaURIs
from models.almacenes import Almacen

SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"


def _settings(**cambios: object) -> Settings:
    datos: dict[str, object] = {
        "modo_pruebas": False,
        "mongodb_host": "mongodb:27017",
        "mongodb_replica_set": "rs0",
        "mongodb_auth_source": "admin",
        "mongodb_global_db": "global_asistente_compras",
        "mongodb_almacen_prefix": "almacen_",
        "mongodb_warehouse_secret": SECRETO,
        "mongo_cliente_user": "cliente_app",
        "mongo_cliente_password": "cliente pass/2026",
        "mongo_admin_app_user": "admin_app",
        "mongo_admin_app_password": "admin-app-pass",
        "mongo_auth_user": "auth_service",
        "mongo_auth_password": "auth-pass",
        "mongo_validador_user": "validador_catalogo",
        "mongo_validador_password": "validador-pass",
        "mongo_catalogo_user": "replicador_catalogo",
        "mongo_catalogo_password": "catalogo-pass",
        "mongo_compras_user": "proyector_compras",
        "mongo_compras_password": "compras-pass",
        "mongo_provisioner_user": "provisioner",
        "mongo_provisioner_password": "provisioner-pass",
        "admin_email": "admin@example.com",
        "admin_password": "clave-segura",
    }
    datos.update(cambios)
    return Settings(**datos)  # type: ignore[arg-type]


class PruebasFabricaURIs(unittest.TestCase):
    def test_nombres_de_base_y_usuario(self) -> None:
        fabrica = FabricaURIs(_settings())
        db = fabrica.nombre_base_almacen("Almacén Central", "abcdef123456")
        self.assertEqual(db, "almacen_almacen_central_abcdef")
        self.assertEqual(fabrica.usuario_almacen(db), f"{db}_app")

        # Sin id se usa un sufijo aleatorio, pero siempre con el prefijo.
        otra = fabrica.nombre_base_almacen("Almacén Central")
        self.assertTrue(otra.startswith("almacen_almacen_central_"))
        self.assertNotEqual(otra, db)

    def test_nombres_invalidos(self) -> None:
        # ``Settings`` valida el prefijo al construirse, así que aquí se usa un
        # doble mínimo para comprobar la validación defensiva de la fábrica.
        fabrica = FabricaURIs(  # type: ignore[arg-type]
            SimpleNamespace(mongodb_almacen_prefix="prefijo.invalido")
        )
        with self.assertRaises(ValueError):
            fabrica.nombre_base_almacen("Central", "abcdef")
        with self.assertRaises(ValueError):
            fabrica.usuario_almacen("usuario inválido")

    def test_password_derivada_es_estable_y_distinta(self) -> None:
        fabrica = FabricaURIs(_settings())
        primera = fabrica.password_almacen("almacen-a")
        self.assertEqual(primera, fabrica.password_almacen("almacen-a"))
        self.assertNotEqual(primera, fabrica.password_almacen("almacen-b"))
        self.assertNotIn("=", primera)
        self.assertNotIn("+", primera)
        self.assertNotIn("/", primera)

        # Cambiar el secreto cambia la contraseña derivada.
        otra = FabricaURIs(_settings(mongodb_warehouse_secret="otro-" + SECRETO))
        self.assertNotEqual(primera, otra.password_almacen("almacen-a"))

    def test_password_sin_secreto(self) -> None:
        fabrica = FabricaURIs(  # type: ignore[arg-type]
            SimpleNamespace(mongodb_warehouse_secret="")
        )
        with self.assertRaises(ValueError):
            fabrica.password_almacen("almacen-a")

    def test_uris_por_rol(self) -> None:
        fabrica = FabricaURIs(_settings())
        uri = fabrica.uri_cliente()
        self.assertTrue(uri.startswith("mongodb://cliente_app:"))
        self.assertIn("@mongodb:27017/global_asistente_compras", uri)
        self.assertIn("authSource=admin", uri)
        self.assertIn("replicaSet=rs0", uri)
        # Las credenciales se codifican para que la URI siga siendo válida.
        self.assertIn(quote_plus("cliente pass/2026"), uri)

        self.assertIn("admin_app:", fabrica.uri_admin_app())
        self.assertIn("auth_service:", fabrica.uri_auth())
        self.assertIn("validador_catalogo:", fabrica.uri_validador())
        self.assertIn("replicador_catalogo:", fabrica.uri_catalogo())
        self.assertIn("proyector_compras:", fabrica.uri_compras())
        self.assertIn("/admin?", fabrica.uri_provisioner())

    def test_uri_almacen_usa_su_base_y_usuario(self) -> None:
        fabrica = FabricaURIs(_settings())
        almacen = Almacen(
            almacen_id="abcdef123456",
            nombre="Central",
            db_name="almacen_central_abcdef",
            mongo_user="almacen_central_abcdef_app",
        )
        uri = fabrica.uri_almacen(almacen)
        self.assertIn("almacen_central_abcdef_app:", uri)
        self.assertIn("/almacen_central_abcdef?", uri)
        self.assertEqual(fabrica.base_datos_almacen(almacen), almacen.db_name)

    def test_modo_pruebas_reutiliza_la_uri(self) -> None:
        fabrica = FabricaURIs(_settings(modo_pruebas=True, mongodb_uri="mongodb://localhost:27017"))
        self.assertEqual(fabrica.uri_cliente(), "mongodb://localhost:27017")
        self.assertEqual(fabrica.uri_admin_app(), "mongodb://localhost:27017")
        self.assertEqual(fabrica.uri_auth(), "mongodb://localhost:27017")
        self.assertEqual(fabrica.uri_validador(), "mongodb://localhost:27017")
        self.assertEqual(fabrica.uri_catalogo(), "mongodb://localhost:27017")
        self.assertEqual(fabrica.uri_compras(), "mongodb://localhost:27017")
        self.assertEqual(fabrica.uri_provisioner(), "mongodb://localhost:27017")

    def test_repr_no_filtra_credenciales(self) -> None:
        fabrica = FabricaURIs(_settings())
        texto = repr(fabrica)
        self.assertIn("mongodb:27017", texto)
        self.assertNotIn("cliente pass/2026", texto)
        self.assertNotIn(SECRETO, texto)

    def test_uri_sin_credenciales(self) -> None:
        fabrica = FabricaURIs(  # type: ignore[arg-type]
            SimpleNamespace(
                modo_pruebas=False,
                mongodb_host="mongodb:27017",
                mongodb_auth_source="admin",
                mongodb_replica_set="rs0",
                mongodb_global_db="global_asistente_compras",
                mongo_cliente_user="cliente_app",
                mongo_cliente_password="",
            )
        )
        with self.assertRaises(ValueError):
            fabrica.uri_cliente()


if __name__ == "__main__":
    unittest.main()
