"""Pruebas unitarias de las estructuras de datos."""

from __future__ import annotations

import unittest

from core.observer import SujetoObservable
from models.carrito import CarritoCompras
from models.listas import ListaDoblementeEnlazada, ListaSimple
from models.productos import Producto


class ObservadorFalso:
    def __init__(self) -> None:
        self.notificaciones: list[str] = []

    def actualizar(self, sujeto, mensaje: str) -> None:
        self.notificaciones.append(mensaje)

    def notificar_denegado(self, permiso: str) -> None:
        return None


class PruebasListas(unittest.TestCase):
    def test_lista_simple(self) -> None:
        lista = ListaSimple()
        self.assertTrue(lista.esta_vacia())
        for valor in (10, 20, 30):
            lista.agregar(valor)
        self.assertEqual(len(lista), 3)
        self.assertEqual(list(lista.mostrar()), [10, 20, 30])
        self.assertEqual(lista.obtener(0), 10)
        self.assertEqual(lista.obtener(-1), 30)
        self.assertTrue(lista.reemplazar(1, 99))
        self.assertEqual(lista.obtener(1), 99)
        self.assertFalse(lista.reemplazar(9, 0))
        with self.assertRaises(IndexError):
            lista.obtener(5)
        lista.limpiar()
        self.assertEqual(len(lista), 0)

    def test_lista_doblemente_enlazada(self) -> None:
        lista = ListaDoblementeEnlazada()
        lista.agregar_al_final("B")
        lista.agregar_al_inicio("A")
        lista.agregar_al_final("C")
        self.assertEqual(list(lista.mostrar()), ["A", "B", "C"])
        self.assertEqual(len(lista), 3)
        self.assertEqual(lista.obtener(1), "B")
        self.assertEqual(lista.eliminar_en(1), "B")
        self.assertEqual(list(lista.mostrar()), ["A", "C"])
        self.assertTrue(lista.eliminar("A"))
        self.assertTrue(lista.eliminar("C"))
        self.assertTrue(lista.esta_vacia())
        self.assertFalse(lista.eliminar("Z"))

    def test_observer_notifica(self) -> None:
        carrito = CarritoCompras()
        vista = ObservadorFalso()
        carrito.agregar_observador(vista)
        carrito.agregar_producto(Producto("Leche", 100))
        carrito.agregar_producto(Producto("Pan", 50))
        carrito.eliminar_producto(0)
        carrito.establecer_estrategia_descuento(None)
        self.assertEqual(len(vista.notificaciones), 4)
        self.assertEqual(carrito.calcular_subtotal(), 50)

    def test_sujeto_observable_no_duplica(self) -> None:
        sujeto = SujetoObservable()
        vista = ObservadorFalso()
        sujeto.agregar_observador(vista)
        sujeto.agregar_observador(vista)
        sujeto.notificar_observadores("hola")
        self.assertEqual(vista.notificaciones, ["hola"])
        sujeto.remover_observador(vista)
        sujeto.notificar_observadores("adios")
        self.assertEqual(vista.notificaciones, ["hola"])


if __name__ == "__main__":
    unittest.main()
