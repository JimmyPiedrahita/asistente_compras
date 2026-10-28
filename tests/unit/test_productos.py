"""Pruebas unitarias de productos y Factory Method."""

from __future__ import annotations

import unittest

from models.productos import (
    FabricaProductos,
    Producto,
    ProductoDigital,
    ProductoFisico,
    ProductoSuscripcion,
)


class PruebasProducto(unittest.TestCase):
    def test_factory_tipos_y_precios(self) -> None:
        normal = FabricaProductos.crear_producto("normal", "A", 100)
        fisico = FabricaProductos.crear_producto("fisico", "B", 100, costo_envio=7)
        digital = FabricaProductos.crear_producto("digital", "C", 100)
        suscripcion = FabricaProductos.crear_producto("suscripcion", "D", 10, meses=12)

        self.assertIs(type(normal), Producto)
        self.assertIs(type(fisico), ProductoFisico)
        self.assertIs(type(digital), ProductoDigital)
        self.assertIs(type(suscripcion), ProductoSuscripcion)
        self.assertAlmostEqual(normal.obtener_precio_final(), 100)
        self.assertAlmostEqual(fisico.obtener_precio_final(), 107)
        self.assertAlmostEqual(digital.obtener_precio_final(), 100)
        self.assertAlmostEqual(suscripcion.obtener_precio_final(), 120)

    def test_factory_marca_y_errores(self) -> None:
        producto = FabricaProductos.crear_producto(
            "fisico",
            "TV",
            500,
            marca="Sony",
            categoria="Electronica",
            costo_envio=10,
        )
        self.assertEqual(producto.marca, "Sony")
        self.assertEqual(producto.categoria, "Electronica")
        with self.assertRaises(ValueError):
            FabricaProductos.crear_producto("inexistente", "X", 1)
        with self.assertRaises(ValueError):
            FabricaProductos.crear_producto("normal", "", 1)
        with self.assertRaises(ValueError):
            FabricaProductos.crear_producto("normal", "X", -1)

    def test_clon_independiente(self) -> None:
        original = Producto("Leche", 100, "Marca")
        copia = original.clonar()
        original.precio = 999
        self.assertEqual(copia.precio, 100)
        self.assertEqual(copia.marca, "Marca")
        self.assertIsNot(original, copia)

    def test_validaciones_de_subclases(self) -> None:
        with self.assertRaises(ValueError):
            ProductoFisico("X", 10, costo_envio=-1)
        with self.assertRaises(ValueError):
            ProductoSuscripcion("X", 10, meses=0)
        with self.assertRaises(ValueError):
            Producto("", 10)


if __name__ == "__main__":
    unittest.main()
