"""Pruebas del registro de sesiones en memoria."""

from __future__ import annotations

import unittest

from controllers.sesiones import RegistroSesiones
from models.seguridad import Usuario


def usuario(numero: int = 1, rol: str = "CLIENTE") -> Usuario:
    return Usuario(
        usuario_id=f"u{numero}",
        nombre=f"Usuario {numero}",
        email=f"usuario{numero}@example.com",
        password_hash="hash",
        rol=rol,
        almacen_id="a1" if rol == "ADMINISTRADOR_ALMACEN" else None,
        telefono="3000000000",
        direccion="Calle 1",
        ciudad="Ciudad",
    )


class PruebasSesiones(unittest.TestCase):
    def setUp(self) -> None:
        self.reloj = [0.0]
        self.registro = RegistroSesiones(
            ttl_seconds=10,
            max_sesiones=2,
            clock=lambda: self.reloj[0],
        )

    def test_crear_obtener_y_eliminar(self) -> None:
        sesion = self.registro.crear(usuario())
        self.assertIsNotNone(self.registro.obtener(sesion.token))
        self.assertEqual(len(self.registro), 1)
        self.assertEqual(sesion.publica()["rol"], "CLIENTE")
        self.registro.eliminar(sesion.token)
        self.assertIsNone(self.registro.obtener(sesion.token))
        self.assertEqual(len(self.registro), 0)

    def test_ttl_se_renueva_con_acceso(self) -> None:
        sesion = self.registro.crear(usuario())
        self.reloj[0] = 5
        self.assertIsNotNone(self.registro.obtener(sesion.token))
        self.reloj[0] = 14
        self.assertIsNotNone(self.registro.obtener(sesion.token))
        self.reloj[0] = 24
        self.assertIsNone(self.registro.obtener(sesion.token))

    def test_limite_expulsa_la_mas_antigua(self) -> None:
        primera = self.registro.crear(usuario(1))
        self.reloj[0] = 1
        segunda = self.registro.crear(usuario(2))
        self.reloj[0] = 2
        tercera = self.registro.crear(usuario(3))
        self.assertEqual(len(self.registro), 2)
        self.assertIsNone(self.registro.obtener(primera.token))
        self.assertIsNotNone(self.registro.obtener(segunda.token))
        self.assertIsNotNone(self.registro.obtener(tercera.token))

    def test_sesiones_aisladas(self) -> None:
        primera = self.registro.crear(usuario(1))
        segunda = self.registro.crear(usuario(2))
        primera.lista.append("arroz")
        primera.carrito.agregar("a1", "p1")
        self.assertEqual(segunda.lista, [])
        self.assertEqual(len(segunda.carrito), 0)

    def test_limpiar_expiradas(self) -> None:
        self.registro.crear(usuario())
        self.reloj[0] = 11
        self.assertEqual(self.registro.limpiar_expiradas(), 1)
        self.assertEqual(len(self.registro), 0)


if __name__ == "__main__":
    unittest.main()
