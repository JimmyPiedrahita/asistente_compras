"""Pruebas de configuración por variables de entorno."""

from __future__ import annotations

import unittest

from core.config import Settings
from core.errors import ConfiguracionInvalida

ENTORNO = {
    "MONGODB_URI": "mongodb://localhost:27017",
    "ADMIN_EMAIL": "Admin@Example.com",
    "ADMIN_PASSWORD": "clave-segura",
}


class PruebasConfiguracion(unittest.TestCase):
    def test_from_env_minimo(self) -> None:
        settings = Settings.from_env(ENTORNO)
        self.assertEqual(settings.mongodb_uri, "mongodb://localhost:27017")
        self.assertEqual(settings.mongodb_db, "asistente_compras")
        self.assertEqual(settings.admin_email, "admin@example.com")
        self.assertEqual(settings.admin_password, "clave-segura")
        self.assertEqual(settings.session_ttl_seconds, 3600)
        self.assertEqual(settings.max_sessions, 1000)

    def test_valores_personalizados(self) -> None:
        settings = Settings.from_env(
            {
                **ENTORNO,
                "MONGODB_DB": "tienda_test",
                "CORS_ORIGINS": "http://a.test, http://b.test",
                "SESSION_TTL_SECONDS": "60",
                "MAX_SESSIONS": "5",
                "MAX_CSV_BYTES": "2048",
                "MONGODB_TIMEOUT_MS": "1500",
                "ADMIN_NOMBRE": "Administrador",
            }
        )
        self.assertEqual(settings.mongodb_db, "tienda_test")
        self.assertEqual(settings.cors_origins, ("http://a.test", "http://b.test"))
        self.assertEqual(settings.session_ttl_seconds, 60)
        self.assertEqual(settings.max_sessions, 5)
        self.assertEqual(settings.max_csv_bytes, 2048)
        self.assertEqual(settings.mongodb_timeout_ms, 1500)

    def test_errores_de_configuracion(self) -> None:
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({"MONGODB_URI": "mongodb://x"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "ADMIN_PASSWORD": "corta"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "ADMIN_EMAIL": "no-es-correo"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "ADMIN_EMAIL": "admin@asistente.local"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MONGODB_DB": "base.invalida"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "SESSION_TTL_SECONDS": "0"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({**ENTORNO, "MAX_SESSIONS": "abc"})

    def test_configuracion_de_pruebas(self) -> None:
        settings = Settings.de_pruebas(mongodb_db="pruebas")
        self.assertEqual(settings.mongodb_db, "pruebas")
        self.assertEqual(settings.admin_email, "admin@example.com")
        self.assertEqual(settings.cors_origins, ())


if __name__ == "__main__":
    unittest.main()
