"""Pruebas del carrito, cupones y cálculo de totales."""

from __future__ import annotations

import unittest

from controllers.carrito import MAX_CUPONES, ControladorCarrito
from controllers.sesiones import Sesion
from core.errors import NoEncontrado, SolicitudInvalida
from models.almacenes import Almacen
from models.cupones import Cupon
from models.productos import Producto
from models.texto import normalizar_texto


class RepoFalso:
    def __init__(self) -> None:
        self.productos: dict[str, Producto] = {}
        self.almacenes: dict[str, Almacen] = {}
        self.cupones: dict[str, Cupon] = {}

    def obtener_producto(self, producto_id: str):
        return self.productos.get(str(producto_id))

    def obtener_almacen(self, almacen_id: str):
        return self.almacenes.get(str(almacen_id))

    def obtener_cupon_por_codigo(self, codigo: str):
        return self.cupones.get(normalizar_texto(codigo))


def crear_producto(producto_id: str, almacen_id: str, precio: float) -> Producto:
    return Producto.crear(
        producto_id=producto_id,
        almacen_id=almacen_id,
        tipo_producto="arroz",
        nombre=f"Producto {producto_id}",
        precio=precio,
        presentacion="500 g",
    )


class PruebasCarrito(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = RepoFalso()
        self.repo.almacenes["a"] = Almacen(almacen_id="a", nombre="Almacén A")
        self.repo.almacenes["b"] = Almacen(almacen_id="b", nombre="Almacén B")
        self.repo.productos["p1"] = crear_producto("p1", "a", 3000)
        self.repo.productos["p2"] = crear_producto("p2", "a", 2000)
        self.repo.productos["p3"] = crear_producto("p3", "b", 1000)
        self.repo.cupones["arroz10"] = Cupon("c1", "ARROZ10", "a", 10)
        self.repo.cupones["arroz20"] = Cupon("c2", "ARROZ20", "a", 20)
        self.repo.cupones["mitad"] = Cupon("c3", "MITAD", "b", 50)
        self.controlador = ControladorCarrito(self.repo)
        self.sesion = Sesion(
            token="token",
            usuario_id="u1",
            nombre="Ana",
            email="ana@example.com",
            rol="CLIENTE",
            almacen_id=None,
        )

    def test_agregar_y_actualizar_items(self) -> None:
        resumen = self.controlador.agregar_item(self.sesion, "a", "p1", 2)
        self.assertEqual(resumen["cantidad_items"], 2)
        self.assertEqual(resumen["subtotal"], 6000)
        resumen = self.controlador.agregar_item(self.sesion, "a", "p1", 1)
        self.assertEqual(resumen["cantidad_items"], 3)
        item = resumen["items"][0]
        resumen = self.controlador.actualizar_cantidad(self.sesion, item["item_id"], 2)
        self.assertEqual(resumen["subtotal"], 6000)
        resumen = self.controlador.quitar_item(self.sesion, item["item_id"])
        self.assertEqual(resumen["items"], [])

    def test_rechaza_producto_de_otro_almacen_o_cantidad_invalida(self) -> None:
        with self.assertRaises(NoEncontrado):
            self.controlador.agregar_item(self.sesion, "b", "p1", 1)
        with self.assertRaises(SolicitudInvalida):
            self.controlador.agregar_item(self.sesion, "a", "p1", 0)
        with self.assertRaises(NoEncontrado):
            self.controlador.actualizar_cantidad(self.sesion, "inexistente", 2)
        with self.assertRaises(NoEncontrado):
            self.controlador.quitar_item(self.sesion, "inexistente")

    def test_descuento_solo_sobre_el_almacen_del_cupon(self) -> None:
        self.controlador.agregar_item(self.sesion, "a", "p1", 2)
        self.controlador.agregar_item(self.sesion, "b", "p3", 1)
        resumen = self.controlador.aplicar_cupon(self.sesion, "arroz10")
        self.assertEqual(resumen["subtotal"], 7000)
        self.assertEqual(resumen["descuento_total"], 600)
        self.assertEqual(resumen["total"], 6400)
        parte_b = next(p for p in resumen["detalle_almacenes"] if p["almacen_id"] == "b")
        self.assertIsNone(parte_b["cupon_codigo"])
        self.assertEqual(parte_b["total"], 1000)

        resumen = self.controlador.aplicar_cupon(self.sesion, "MITAD")
        self.assertEqual(resumen["descuento_total"], 1100)
        self.assertEqual(resumen["total"], 5900)

    def test_cupon_requiere_productos_de_su_almacen(self) -> None:
        self.controlador.agregar_item(self.sesion, "a", "p1", 1)
        with self.assertRaises(SolicitudInvalida):
            self.controlador.aplicar_cupon(self.sesion, "MITAD")
        with self.assertRaises(SolicitudInvalida):
            self.controlador.aplicar_cupon(self.sesion, "NOEXISTE")

    def test_un_cupon_por_almacen_y_sin_duplicados(self) -> None:
        self.controlador.agregar_item(self.sesion, "a", "p1", 1)
        self.controlador.aplicar_cupon(self.sesion, "ARROZ10")
        with self.assertRaises(SolicitudInvalida):
            self.controlador.aplicar_cupon(self.sesion, "arroz10")
        with self.assertRaises(SolicitudInvalida):
            self.controlador.aplicar_cupon(self.sesion, "ARROZ20")
        resumen = self.controlador.quitar_cupon(self.sesion, "arroz10")
        self.assertEqual(resumen["cupones_aplicados"], [])
        with self.assertRaises(SolicitudInvalida):
            self.controlador.quitar_cupon(self.sesion, "arroz10")

    def test_maximo_tres_cupones(self) -> None:
        for indice in range(1, 5):
            almacen_id = f"extra{indice}"
            self.repo.almacenes[almacen_id] = Almacen(
                almacen_id=almacen_id, nombre=f"Almacén {indice}"
            )
            self.repo.productos[f"x{indice}"] = crear_producto(f"x{indice}", almacen_id, 100)
            self.repo.cupones[f"cupon{indice}"] = Cupon(
                f"cx{indice}", f"CUPON{indice}", almacen_id, 10
            )
            self.controlador.agregar_item(self.sesion, almacen_id, f"x{indice}", 1)
            if indice <= MAX_CUPONES:
                self.controlador.aplicar_cupon(self.sesion, f"CUPON{indice}")
        with self.assertRaises(SolicitudInvalida):
            self.controlador.aplicar_cupon(self.sesion, "CUPON4")

    def test_cupon_eliminado_se_retira_con_aviso(self) -> None:
        self.controlador.agregar_item(self.sesion, "a", "p1", 1)
        self.controlador.aplicar_cupon(self.sesion, "ARROZ10")
        self.repo.cupones.pop("arroz10")
        resumen = self.controlador.resumen(self.sesion)
        self.assertEqual(resumen["descuento_total"], 0)
        self.assertEqual(resumen["cupones_aplicados"], [])
        self.assertEqual(self.sesion.carrito.cupones, [])
        self.assertTrue(any("eliminado" in aviso for aviso in resumen["avisos"]))

    def test_producto_eliminado_se_retira_con_aviso(self) -> None:
        self.controlador.agregar_item(self.sesion, "a", "p1", 1)
        self.controlador.agregar_item(self.sesion, "b", "p3", 1)
        self.repo.productos.pop("p1")
        resumen = self.controlador.resumen(self.sesion)
        self.assertEqual(len(resumen["items"]), 1)
        self.assertEqual(resumen["total"], 1000)
        self.assertTrue(any("ya no está disponible" in aviso for aviso in resumen["avisos"]))

    def test_vaciar(self) -> None:
        self.controlador.agregar_item(self.sesion, "a", "p1", 1)
        self.controlador.aplicar_cupon(self.sesion, "ARROZ10")
        resumen = self.controlador.vaciar(self.sesion)
        self.assertEqual(resumen["items"], [])
        self.assertEqual(resumen["cupones_aplicados"], [])
        self.assertEqual(resumen["total"], 0)


if __name__ == "__main__":
    unittest.main()
