"""Pruebas de configuración por variables de entorno."""

from __future__ import annotations

import unittest

from core.config import Settings
from core.errors import ConfiguracionInvalida

SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"

ENTORNO = {
    "MONGODB_HOST": "mongodb:27017",
    "MONGODB_REPLICA_SET": "rs0",
    "MONGODB_AUTH_SOURCE": "admin",
    "MONGODB_GLOBAL_DB": "global_asistente_compras",
    "MONGODB_ALMACEN_PREFIX": "almacen_",
    "MONGODB_WAREHOUSE_SECRET": SECRETO,
    "MONGO_CLIENTE_PASSWORD": "cliente-pass",
    "MONGO_ADMIN_APP_PASSWORD": "admin-app-pass",
    "MONGO_AUTH_PASSWORD": "auth-pass",
    "MONGO_VALIDADOR_PASSWORD": "validador-pass",
    "MONGO_CATALOGO_PASSWORD": "catalogo-pass",
    "MONGO_COMPRAS_PASSWORD": "compras-pass",
    "MONGO_PROVISIONER_PASSWORD": "provisioner-pass",
    "ADMIN_EMAIL": "Admin@Example.com",
    "ADMIN_PASSWORD": "clave-segura",
}


class PruebasConfiguracion(unittest.TestCase):
    def test_from_env_minimo(self) -> None:
        settings = Settings.from_env(ENTORNO)
        self.assertFalse(settings.modo_pruebas)
        self.assertEqual(settings.mongodb_host, "mongodb:27017")
        self.assertEqual(settings.mongodb_replica_set, "rs0")
        self.assertEqual(settings.mongodb_global_db, "global_asistente_compras")
        self.assertEqual(settings.mongodb_almacen_prefix, "almacen_")
        self.assertEqual(settings.mongo_cliente_user, "cliente_app")
        self.assertEqual(settings.admin_email, "admin@example.com")
        self.assertEqual(settings.admin_password, "clave-segura")
        self.assertEqual(settings.session_ttl_seconds, 3600)
        self.assertEqual(settings.max_sessions, 1000)

    def test_valores_personalizados(self) -> None:
        settings = Settings.from_env(
            {
                **ENTORNO,
                "MONGODB_GLOBAL_DB": "global_tienda",
                "MONGODB_ALMACEN_PREFIX": "tienda_",
                "MONGO_CLIENTE_USER": "cliente_tienda",
                "CORS_ORIGINS": "http://a.test, http://b.test",
                "SESSION_TTL_SECONDS": "60",
                "MAX_SESSIONS": "5",
                "MAX_CSV_BYTES": "2048",
                "MONGODB_TIMEOUT_MS": "1500",
                "LISTENER_REFRESH_SECONDS": "7",
                "ADMIN_NOMBRE": "Administrador",
            }
        )
        self.assertEqual(settings.mongodb_global_db, "global_tienda")
        self.assertEqual(settings.mongodb_almacen_prefix, "tienda_")
        self.assertEqual(settings.mongo_cliente_user, "cliente_tienda")
        self.assertEqual(settings.cors_origins, ("http://a.test", "http://b.test"))
        self.assertEqual(settings.session_ttl_seconds, 60)
        self.assertEqual(settings.max_sessions, 5)
        self.assertEqual(settings.max_csv_bytes, 2048)
        self.assertEqual(settings.mongodb_timeout_ms, 1500)
        self.assertEqual(settings.listener_refresh_seconds, 7)

    def test_modo_pruebas_por_uri(self) -> None:
        # Compatibilidad: sin MONGODB_HOST, un MONGODB_URI activa el modo de
        # pruebas y usa la misma base como global.
        settings = Settings.from_env(
            {
                "MONGODB_URI": "mongodb://localhost:27017",
                "MONGODB_DB": "pruebas",
                "ADMIN_EMAIL": "Admin@Example.com",
                "ADMIN_PASSWORD": "clave-segura",
            }
        )
        self.assertTrue(settings.modo_pruebas)
        self.assertEqual(settings.mongodb_uri, "mongodb://localhost:27017")
        self.assertEqual(settings.mongodb_global_db, "pruebas")
        self.assertEqual(settings.mongo_cliente_password, "pruebas")

    def test_errores_de_configuracion(self) -> None:
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({"MONGODB_HOST": "mongodb:27017"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "ADMIN_PASSWORD": "corta"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "ADMIN_EMAIL": "no-es-correo"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "ADMIN_EMAIL": "admin@asistente.local"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MONGODB_GLOBAL_DB": "base.invalida"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MONGODB_ALMACEN_PREFIX": "base.invalida"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MONGO_CLIENTE_USER": "usuario inválido"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MONGODB_WAREHOUSE_SECRET": "corto"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MONGO_AUTH_PASSWORD": ""})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "SESSION_TTL_SECONDS": "0"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MAX_SESSIONS": "abc"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MONGODB_TIMEOUT_MS": "50"})

    def test_configuracion_de_pruebas(self) -> None:
        settings = Settings.de_pruebas(mongodb_db="pruebas")
        self.assertTrue(settings.modo_pruebas)
        self.assertEqual(settings.mongodb_db, "pruebas")
        self.assertEqual(settings.mongodb_global_db, "pruebas")
        self.assertEqual(settings.admin_email, "admin@example.com")
        self.assertEqual(settings.cors_origins, ())
        self.assertTrue(settings.mongodb_warehouse_secret)


if __name__ == "__main__":
    unittest.main()
