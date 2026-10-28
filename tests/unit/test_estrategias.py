"""Pruebas unitarias de estrategias y búsquedas."""

from __future__ import annotations

import unittest

from models.almacenes import Almacen, GestorAlmacenes
from models.estrategias import (
    BusquedaCatalogoStrategy,
    BusquedaMejorPrecioStrategy,
    DescuentoFijo,
    DescuentoPorcentaje,
    MejorPrecioGlobalStrategy,
    SinDescuento,
)
from models.listas import ListaDoblementeEnlazada
from models.productos import Producto


def construir_gestor() -> GestorAlmacenes:
    almacen_1 = Almacen(1, "Almacen 1")
    almacen_2 = Almacen(2, "Almacen 2")
    almacen_1.agregar_producto(Producto("Leche", 1200, "Sancor"))
    almacen_1.agregar_producto(Producto("Leche", 1100, "LaSerenisima"))
    almacen_2.agregar_producto(Producto("Leche", 1000, "Ilolay"))
    almacen_2.agregar_producto(Producto("Pan", 500, "Bimbo"))
    return GestorAlmacenes(almacenes=(almacen_1, almacen_2))


class PruebasEstrategias(unittest.TestCase):
    def test_descuentos(self) -> None:
        self.assertAlmostEqual(SinDescuento().calcular(100), 100)
        self.assertAlmostEqual(DescuentoPorcentaje(15).calcular(100), 85)
        self.assertAlmostEqual(DescuentoFijo(30).calcular(100), 70)
        self.assertAlmostEqual(DescuentoFijo(300).calcular(100), 0)
        with self.assertRaises(ValueError):
            DescuentoPorcentaje(150)
        with self.assertRaises(ValueError):
            DescuentoFijo(-1)

    def test_busquedas(self) -> None:
        gestor = construir_gestor()
        lista = ListaDoblementeEnlazada()
        lista.agregar_al_final("Leche")

        por_almacen = BusquedaMejorPrecioStrategy().buscar(lista, gestor)
        self.assertEqual(len(por_almacen), 2)
        precios = sorted(
            producto.precio
            for lista_productos in por_almacen.values()
            for producto in lista_productos.mostrar()
        )
        self.assertEqual(precios, [1000, 1100])

        catalogo = BusquedaCatalogoStrategy().buscar(lista, gestor)
        total = sum(len(lista_productos) for lista_productos in catalogo.values())
        self.assertEqual(total, 3)

        globales = MejorPrecioGlobalStrategy().buscar(lista, gestor)
        self.assertEqual(len(globales), 1)
        self.assertEqual(globales[0]["precio"], 1000)
        self.assertEqual(globales[0]["almacen"].nombre, "Almacen 2")

    def test_busqueda_sin_coincidencias(self) -> None:
        gestor = construir_gestor()
        lista = ListaDoblementeEnlazada()
        lista.agregar_al_final("Arroz")
        self.assertEqual(BusquedaMejorPrecioStrategy().buscar(lista, gestor), {})
        self.assertEqual(MejorPrecioGlobalStrategy().buscar(lista, gestor), [])

    def test_indice_por_nombre(self) -> None:
        almacen = Almacen(1, "Almacen 1")
        almacen.agregar_producto(Producto("Cafe", 10))
        almacen.agregar_producto(Producto("CAFE", 20))
        self.assertEqual(len(list(almacen.productos_por_nombre(" cafe "))), 2)
        self.assertEqual(len(list(almacen.productos_por_nombre("Leche"))), 0)


if __name__ == "__main__":
    unittest.main()
