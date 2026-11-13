"""Pruebas unitarias de configuración."""

from __future__ import annotations

import unittest

from core.config import Settings, crear_almacenes
from core.errors import ConfiguracionInvalida


class PruebasConfiguracion(unittest.TestCase):
    def test_from_env_minimo(self) -> None:
        settings = Settings.from_env(
            {
                "MONGODB_URI": "mongodb://localhost:27017",
                "ADMIN_CLAVE": "clave-segura",
            }
        )
        self.assertEqual(settings.mongodb_uri, "mongodb://localhost:27017")
        self.assertEqual(settings.admin_clave, "clave-segura")
        self.assertEqual(len(settings.almacenes), 3)
        self.assertEqual(settings.almacenes[0].base_datos, "warehouse_1")
        self.assertEqual(settings.mongodb_comparador_db, "comparador")

    def test_prefijo_y_almacenes_personalizados(self) -> None:
        settings = Settings.from_env(
            {
                "MONGODB_URI": "mongodb://localhost:27017",
                "ADMIN_CLAVE": "clave-segura",
                "MONGODB_DB_PREFIX": "tienda",
                "WAREHOUSES": "1:Centro,2:Norte",
                "CORS_ORIGINS": "http://a.test, http://b.test",
            }
        )
        self.assertEqual([a.id for a in settings.almacenes], [1, 2])
        self.assertEqual(settings.almacenes[0].base_datos, "tienda_1")
        self.assertEqual(settings.almacenes[0].nombre, "Centro")
        self.assertEqual(settings.cors_origins, ("http://a.test", "http://b.test"))

    def test_errores(self) -> None:
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({"MONGODB_URI": "mongodb://x"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env({"MONGODB_URI": "mongodb://x", "ADMIN_CLAVE": "123"})
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env(
                {
                    "MONGODB_URI": "mongodb://x",
                    "ADMIN_CLAVE": "clave-segura",
                    "MONGODB_DB_PREFIX": "prefijo.invalido",
                }
            )

    def test_crear_almacenes(self) -> None:
        almacenes = crear_almacenes("x")
        self.assertEqual([a.id for a in almacenes], [1, 2, 3])
        self.assertEqual(almacenes[2].base_datos, "x_3")

    def test_base_comparador(self) -> None:
        settings = Settings.from_env(
            {
                "MONGODB_URI": "mongodb://localhost:27017",
                "ADMIN_CLAVE": "clave-segura",
                "MONGODB_COMPARADOR_DB": "integrada",
            }
        )
        self.assertEqual(settings.mongodb_comparador_db, "integrada")

        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env(
                {
                    "MONGODB_URI": "mongodb://localhost:27017",
                    "ADMIN_CLAVE": "clave-segura",
                    "MONGODB_COMPARADOR_DB": "nombre.invalido",
                }
            )
        with self.assertRaises(ConfiguracionInvalida):
            Settings.from_env(
                {
                    "MONGODB_URI": "mongodb://localhost:27017",
                    "ADMIN_CLAVE": "clave-segura",
                    "MONGODB_DB_PREFIX": "tienda",
                    "MONGODB_COMPARADOR_DB": "tienda_1",
                }
            )

    def test_prefijo_deriva_almacenes_en_construccion_directa(self) -> None:
        settings = Settings(
            mongodb_uri="mongodb://localhost:27017",
            admin_clave="clave-segura",
            mongodb_db_prefix="directo",
        )
        self.assertEqual(
            [a.base_datos for a in settings.almacenes or ()],
            ["directo_1", "directo_2", "directo_3"],
        )

    def test_de_pruebas_deriva_almacenes_del_prefijo(self) -> None:
        settings = Settings.de_pruebas(mongodb_db_prefix="test_aislado")
        self.assertEqual(
            [a.base_datos for a in settings.almacenes or ()],
            ["test_aislado_1", "test_aislado_2", "test_aislado_3"],
        )


if __name__ == "__main__":
    unittest.main()
