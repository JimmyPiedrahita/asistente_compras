"""Pruebas del registro de sesiones: TTL, límite y aislamiento."""

from __future__ import annotations

import unittest

from controllers.sesiones import RegistroSesiones
from models.almacenes import GestorAlmacenes


class PruebasSesiones(unittest.TestCase):
    def setUp(self) -> None:
        self.reloj = [0.0]
        self.registro = RegistroSesiones(
            GestorAlmacenes(),
            admin_clave="admin123",
            ttl_seconds=10,
            max_sesiones=2,
            clock=lambda: self.reloj[0],
        )

    def test_crear_obtener_y_eliminar(self) -> None:
        sesion = self.registro.crear()
        self.assertIsNotNone(self.registro.obtener(sesion.token))
        self.assertEqual(len(self.registro), 1)
        self.registro.eliminar(sesion.token)
        self.assertIsNone(self.registro.obtener(sesion.token))
        self.assertEqual(len(self.registro), 0)

    def test_ttl_se_renueva_con_acceso(self) -> None:
        sesion = self.registro.crear()
        self.reloj[0] = 5
        self.assertIsNotNone(self.registro.obtener(sesion.token))
        self.reloj[0] = 14
        self.assertIsNotNone(self.registro.obtener(sesion.token))
        self.reloj[0] = 24
        self.assertIsNone(self.registro.obtener(sesion.token))

    def test_limite_maximo_expulsa_la_mas_antigua(self) -> None:
        primera = self.registro.crear()
        self.reloj[0] = 1
        segunda = self.registro.crear()
        self.reloj[0] = 2
        tercera = self.registro.crear()

        self.assertEqual(len(self.registro), 2)
        self.assertIsNone(self.registro.obtener(primera.token))
        self.assertIsNotNone(self.registro.obtener(segunda.token))
        self.assertIsNotNone(self.registro.obtener(tercera.token))

    def test_limpiar_expiradas(self) -> None:
        self.registro.crear()
        self.reloj[0] = 11
        self.assertEqual(self.registro.limpiar_expiradas(), 1)
        self.assertEqual(len(self.registro), 0)

    def test_sesiones_aisladas(self) -> None:
        primera = self.registro.crear()
        segunda = self.registro.crear()
        primera.controlador.registrar_usuario("Ana")
        primera.controlador.iniciar_sesion("Ana")
        primera.controlador.agregar_producto_usuario("Leche")

        self.assertEqual(primera.controlador.obtener_compras_usuario(), ["Leche"])
        self.assertEqual(segunda.controlador.obtener_compras_usuario(), [])
        self.assertEqual(segunda.controlador.obtener_rol(), "INVITADO")

    def test_login_admin_en_sesion(self) -> None:
        sesion = self.registro.crear()
        self.assertFalse(sesion.controlador.login_admin("mala"))
        self.assertTrue(sesion.controlador.login_admin("admin123"))
        self.assertEqual(sesion.controlador.obtener_rol(), "ADMIN")


if __name__ == "__main__":
    unittest.main()
