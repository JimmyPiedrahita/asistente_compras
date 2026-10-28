"""Pruebas de los controladores de casos de uso."""

from __future__ import annotations

import os
import tempfile
import unittest

from controllers import ControladorCompras
from core.errors import NoPermitido
from models.carrito import CarritoCompras


class VistaFalsa:
    """Doble del observador para comprobar notificaciones."""

    def __init__(self) -> None:
        self.notificaciones: list[str] = []
        self.denegados: list[str] = []
        self.carritos_mostrados: list[tuple] = []

    def actualizar(self, sujeto, mensaje: str) -> None:
        self.notificaciones.append(mensaje)

    def notificar_denegado(self, permiso: str) -> None:
        self.denegados.append(permiso)

    def mostrar_carrito(self, productos, subtotal, total, descuento="Sin descuento"):
        self.carritos_mostrados.append((productos, subtotal, total, descuento))


class PruebasControlador(unittest.TestCase):
    def setUp(self) -> None:
        self.carrito = CarritoCompras()
        self.vista = VistaFalsa()
        self.controlador = ControladorCompras(self.carrito, self.vista, clave_admin="admin123")
        self.controlador.registrar_usuario("Ana")
        self.controlador.iniciar_sesion("Ana")

    def test_invitado_sin_permisos(self) -> None:
        self.controlador.cerrar_sesion()
        self.assertEqual(self.controlador.agregar_producto_usuario("Leche"), "denegado")
        self.assertIn("crear_lista", self.vista.denegados)
        self.assertFalse(self.controlador.exportar_lista("no.csv")["ok"])
        self.assertEqual(self.controlador.establecer_descuento("porcentaje", 10), "denegado")
        with self.assertRaises(NoPermitido):
            self.controlador.ejecutar_busqueda_precios()

    def test_lista_usuario_y_duplicados(self) -> None:
        self.assertEqual(self.controlador.agregar_producto_usuario("Leche"), "ok")
        self.assertEqual(self.controlador.agregar_producto_usuario(" leche "), "duplicado")
        self.assertEqual(self.controlador.obtener_compras_usuario(), ["Leche"])
        self.assertEqual(self.controlador.eliminar_producto_usuario("LECHE"), "ok")
        self.assertEqual(self.controlador.eliminar_producto_usuario("Pan"), "no_encontrado")
        self.assertEqual(self.controlador.agregar_producto_usuario(""), "vacio")

    def test_login_admin(self) -> None:
        self.assertFalse(self.controlador.login_admin("incorrecta"))
        self.assertTrue(self.controlador.login_admin("admin123"))
        self.assertEqual(self.controlador.obtener_rol(), "ADMIN")

    def test_flujo_admin_y_carrito(self) -> None:
        self.assertTrue(self.controlador.login_admin("admin123"))
        self.assertTrue(
            self.controlador.agregar_producto_almacen(
                1, "Leche", 1000, marca="Ilolay", tipo="normal"
            )
        )
        self.assertTrue(
            self.controlador.agregar_producto_almacen(
                2, "Leche", 1200, marca="Sancor", tipo="normal"
            )
        )
        self.assertEqual(self.controlador.agregar_producto_usuario("Leche"), "ok")

        resultados = self.controlador.ejecutar_busqueda_precios()
        self.assertIn(
            "Leche",
            [
                producto.nombre
                for lista_productos in resultados.values()
                for producto in lista_productos.mostrar()
            ],
        )
        self.assertEqual(len(self.controlador.ejecutar_catalogo()), 2)

        globales = self.controlador.ejecutar_comparacion_global()
        self.assertEqual(globales[0]["precio"], 1000)
        producto = globales[0]["producto"]
        almacen = globales[0]["almacen"]

        self.assertTrue(self.controlador.agregar_seleccion_al_carrito(producto, almacen.id_almacen))
        self.assertEqual(self.controlador.obtener_resumen_carrito()["total"], 1000)

        self.assertEqual(self.controlador.establecer_descuento("porcentaje", 10), "ok")
        self.assertAlmostEqual(self.controlador.obtener_resumen_carrito()["total"], 900)
        self.assertEqual(self.controlador.establecer_descuento("porcentaje", 150), "invalido")

        self.assertTrue(self.controlador.quitar_producto_carrito(0))
        self.assertEqual(self.controlador.obtener_resumen_carrito()["total"], 0)
        self.assertFalse(self.controlador.quitar_producto_carrito(99))

    def test_editar_precio(self) -> None:
        self.controlador.login_admin("admin123")
        self.controlador.agregar_producto_almacen(1, "Leche", 1000)
        self.assertTrue(self.controlador.editar_precio(1, 0, 800))
        self.assertEqual(
            self.controlador.gestor_almacenes.obtener_almacen(1).inventario.obtener(0).precio,
            800,
        )
        self.assertFalse(self.controlador.editar_precio(1, 0, -5))
        self.assertFalse(self.controlador.editar_precio(1, 99, 10))
        self.assertFalse(self.controlador.editar_precio(9, 0, 10))

    def test_cargar_csv(self) -> None:
        self.controlador.login_admin("admin123")
        contenido = (
            "\ufeffalmacen,nombre,marca,categoria,tipo,precio,extra\n"
            "1,Leche,LaSerenisima,Lacteos,normal,100,\n"
            "2,Leche,Ilolay,Lacteos,normal,90,\n"
            "1,Curso,Udemy,Digital,digital,50,\n"
            "2,Caja,Generica,General,fisico,100,7\n"
            "1,Netflix,Netflix,Streaming,suscripcion,10,3\n"
            "3,Malo,Generica,General,normal,sin_precio,\n"
        )
        descriptor, ruta = tempfile.mkstemp(suffix=".csv", text=True)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
                archivo.write(contenido)
            resultado = self.controlador.cargar_csv(ruta)
        finally:
            os.unlink(ruta)

        self.assertEqual(resultado["importados"], 5)
        self.assertEqual(resultado["rechazados"], 1)
        self.assertEqual(len(resultado["errores"]), 1)

        productos = self.controlador.listar_productos(2)
        caja = next(p for p in productos if p.nombre == "Caja")
        self.assertAlmostEqual(caja.obtener_precio_final(), 107)

    def test_csv_rechaza_duplicados(self) -> None:
        self.controlador.login_admin("admin123")
        contenido = "almacen,nombre,marca,precio\n1,Leche,Ilolay,100\n1, leche , ilolay ,110\n"
        resultado = self.controlador.cargar_csv_contenido(contenido)
        self.assertEqual(resultado["importados"], 1)
        self.assertEqual(resultado["rechazados"], 1)

    def test_exportaciones(self) -> None:
        self.controlador.login_admin("admin123")
        self.controlador.agregar_producto_almacen(1, "Leche", 1000, marca="Ilolay")
        self.controlador.agregar_producto_usuario("Leche")
        self.controlador.agregar_producto_carrito(self.controlador.listar_productos(1)[0])

        contenido_lista = self.controlador.exportar_lista_csv()
        contenido_carrito = self.controlador.exportar_carrito_csv()
        self.assertIn("producto,marca,precio_final,almacen", contenido_lista)
        self.assertIn("Leche", contenido_lista)
        self.assertIn("total", contenido_carrito)

        ruta_lista = tempfile.mktemp(suffix=".csv")
        ruta_carrito = tempfile.mktemp(suffix=".csv")
        try:
            self.assertTrue(self.controlador.exportar_lista(ruta_lista)["ok"])
            self.assertTrue(self.controlador.exportar_carrito(ruta_carrito)["ok"])
        finally:
            for ruta in (ruta_lista, ruta_carrito):
                if os.path.exists(ruta):
                    os.unlink(ruta)

    def test_recargar_inventarios(self) -> None:
        self.controlador.login_admin("admin123")
        self.assertTrue(self.controlador.recargar_inventarios())
        self.controlador.cerrar_sesion()
        self.assertFalse(self.controlador.recargar_inventarios())

    def test_agregar_producto_invalido_y_duplicado(self) -> None:
        self.controlador.login_admin("admin123")
        self.assertFalse(self.controlador.agregar_producto_almacen(1, "", 10))
        self.assertFalse(self.controlador.agregar_producto_almacen(1, "X", -1))
        self.assertFalse(self.controlador.agregar_producto_almacen(99, "X", 10))
        self.assertTrue(
            self.controlador.agregar_producto_almacen(
                1,
                "Leche",
                100,
                producto_id="fijo",  # type: ignore[call-arg]
            )
        )
        self.assertFalse(
            self.controlador.agregar_producto_almacen(
                1,
                "Leche",
                100,
                producto_id="fijo",  # type: ignore[call-arg]
            )
        )

    def test_descuento_fijo_y_sin_descuento(self) -> None:
        self.controlador.login_admin("admin123")
        self.controlador.agregar_producto_almacen(1, "Leche", 1000)
        self.controlador.agregar_producto_carrito(self.controlador.listar_productos(1)[0])
        self.assertEqual(self.controlador.establecer_descuento("fijo", 100), "ok")
        self.assertEqual(self.controlador.obtener_resumen_carrito()["total"], 900)
        self.assertEqual(self.controlador.establecer_descuento("sin"), "ok")
        self.assertEqual(self.controlador.obtener_resumen_carrito()["total"], 1000)

    def test_carrito_por_id(self) -> None:
        self.controlador.login_admin("admin123")
        self.controlador.agregar_producto_almacen(1, "Leche", 1000)
        producto_id = self.controlador.listar_productos(1)[0].producto_id
        self.assertTrue(self.controlador.agregar_producto_carrito_por_id(1, producto_id))
        self.assertFalse(self.controlador.agregar_producto_carrito_por_id(1, "no-existe"))


if __name__ == "__main__":
    unittest.main()
