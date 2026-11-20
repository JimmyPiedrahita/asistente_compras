"""Pruebas de las entidades del dominio."""

from __future__ import annotations

import unittest

from infrastructure.mongodb.almacen import _producto, _producto_documento
from models.carrito import Carrito
from models.cupones import Cupon, validar_porcentaje
from models.productos import Producto, validar_precio
from models.seguridad import es_email_valido, hashear_password, verificar_password
from models.texto import normalizar_texto


class PruebasProducto(unittest.TestCase):
    def test_validar_precio(self) -> None:
        self.assertEqual(validar_precio("3000"), 3000.0)
        self.assertEqual(validar_precio(3.456), 3.46)
        for valor in (0, -1, "abc", float("inf"), None, 0.001):
            with self.assertRaises(ValueError):
                validar_precio(valor)

    def test_crear_normaliza_y_valida(self) -> None:
        producto = Producto.crear(
            producto_id="p1",
            almacen_id="a1",
            tipo_producto="  Arroz   Integral ",
            nombre="  Arroz  Diana ",
            marca_variedad="  Diana ",
            precio="3000",
            presentacion=" 500   g ",
        )
        self.assertEqual(producto.tipo_producto, "Arroz Integral")
        self.assertEqual(producto.tipo_normalizado, "arroz integral")
        self.assertEqual(producto.nombre, "Arroz Diana")
        self.assertEqual(producto.marca_variedad, "Diana")
        self.assertEqual(producto.presentacion, "500 g")
        self.assertEqual(producto.presentacion_normalizada, "500 g")
        self.assertEqual(producto.precio, 3000.0)
        self.assertEqual(producto.publico()["producto_id"], "p1")

    def test_crear_rechaza_campos_obligatorios(self) -> None:
        base = {
            "producto_id": "p1",
            "almacen_id": "a1",
            "tipo_producto": "arroz",
            "nombre": "Arroz",
            "precio": 1000,
            "presentacion": "500 g",
        }
        for campo in ("tipo_producto", "nombre", "presentacion"):
            with self.assertRaises(ValueError):
                Producto.crear(**{**base, campo: "  "})
        with self.assertRaises(ValueError):
            Producto.crear(**{**base, "precio": 0})

    def test_imagen_opcional_y_compatibilidad(self) -> None:
        producto = Producto.crear(
            producto_id="p1",
            almacen_id="a1",
            tipo_producto="arroz",
            nombre="Arroz",
            precio=1000,
            presentacion="500 g",
        )
        self.assertEqual(producto.imagen_url, "")
        self.assertEqual(producto.imagen_public_id, "")
        self.assertEqual(producto.publico()["imagen_url"], "")

        producto.imagen_url = "https://res.cloudinary.com/demo/imagen.webp"
        producto.imagen_public_id = "asistente-compras/a1/p1"
        self.assertEqual(producto.publico()["imagen_url"], producto.imagen_url)

        documento = _producto_documento(producto)
        self.assertEqual(documento["imagen_url"], producto.imagen_url)
        self.assertEqual(documento["imagen_public_id"], producto.imagen_public_id)
        recuperado = _producto(documento)
        self.assertEqual(recuperado.imagen_url, producto.imagen_url)
        self.assertEqual(recuperado.imagen_public_id, producto.imagen_public_id)

        # Los documentos antiguos no tienen los campos de imagen.
        antiguo = dict(documento)
        antiguo.pop("imagen_url")
        antiguo.pop("imagen_public_id")
        recuperado_antiguo = _producto(antiguo)
        self.assertEqual(recuperado_antiguo.imagen_url, "")
        self.assertEqual(recuperado_antiguo.imagen_public_id, "")


class PruebasCupon(unittest.TestCase):
    def test_validar_porcentaje(self) -> None:
        self.assertEqual(validar_porcentaje("10"), 10.0)
        self.assertEqual(validar_porcentaje(100), 100.0)
        for valor in (0, -1, 100.01, "x", 0.001):
            with self.assertRaises(ValueError):
                validar_porcentaje(valor)

    def test_publico(self) -> None:
        cupon = Cupon(cupon_id="c1", codigo="ARROZ10", almacen_id="a1", porcentaje=10)
        self.assertEqual(cupon.codigo_normalizado, "arroz10")
        self.assertEqual(cupon.publico()["codigo"], "ARROZ10")
        self.assertIsNone(cupon.publico()["creado_en"])


class PruebasSeguridad(unittest.TestCase):
    def test_email(self) -> None:
        self.assertTrue(es_email_valido("persona@example.com"))
        self.assertFalse(es_email_valido("persona@"))
        self.assertFalse(es_email_valido("persona@asistente.local"))
        self.assertFalse(es_email_valido(""))

    def test_hash_y_verificacion(self) -> None:
        hash_generado = hashear_password("secreta123")
        self.assertNotIn("secreta123", hash_generado)
        self.assertTrue(verificar_password("secreta123", hash_generado))
        self.assertFalse(verificar_password("otra", hash_generado))
        self.assertFalse(verificar_password("secreta123", "formato-invalido"))


class PruebasCarrito(unittest.TestCase):
    def test_agregar_actualizar_y_quitar(self) -> None:
        carrito = Carrito()
        item = carrito.agregar("a1", "p1", 2)
        self.assertEqual(item.cantidad, 2)
        carrito.agregar("a1", "p1", 3)
        self.assertEqual(len(carrito), 1)
        self.assertEqual(item.cantidad, 5)
        self.assertTrue(carrito.actualizar_cantidad(item.item_id, 2))
        self.assertEqual(item.cantidad, 2)
        with self.assertRaises(ValueError):
            carrito.actualizar_cantidad(item.item_id, 0)
        self.assertFalse(carrito.actualizar_cantidad("inexistente", 1))
        self.assertTrue(carrito.quitar(item.item_id))
        self.assertFalse(carrito.quitar(item.item_id))
        self.assertTrue(carrito.almacenes() == set())

    def test_vaciar_limpia_cupones(self) -> None:
        carrito = Carrito()
        carrito.agregar("a1", "p1")
        carrito.cupones.append("ARROZ10")
        carrito.vaciar()
        self.assertEqual(len(carrito), 0)
        self.assertEqual(carrito.cupones, [])


class PruebasTexto(unittest.TestCase):
    def test_normalizar(self) -> None:
        self.assertEqual(normalizar_texto("  Arroz   DIANA \ufeff"), "arroz diana")
        self.assertEqual(normalizar_texto(None), "")


if __name__ == "__main__":
    unittest.main()
