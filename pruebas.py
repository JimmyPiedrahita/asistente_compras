import os
import tempfile
import unittest

from models.almacenes import Almacen, GestorAlmacenes
from controllers import ControladorCompras
from models.estrategias import (
    DescuentoFijo, DescuentoPorcentaje, SinDescuento,
    BusquedaMejorPrecioStrategy, BusquedaCatalogoStrategy,
    MejorPrecioGlobalStrategy)
from models.listas import CarritoCompras, ListaDoblementeEnlazada, ListaSimple
from models.modelos import (
    FabricaProductos, Producto, ProductoDigital, ProductoFisico,
    ProductoSuscripcion)


class VistaFalsa:
    """Doble del observador HTTP para probar el controlador."""

    def __init__(self):
        self.notificaciones = []
        self.denegados = []
        self.carritos_mostrados = []

    def actualizar(self, sujeto, mensaje):
        self.notificaciones.append(mensaje)

    def notificar_denegado(self, permiso):
        self.denegados.append(permiso)

    def mostrar_carrito(self, productos, subtotal, total, descuento="Sin descuento"):
        self.carritos_mostrados.append((productos, subtotal, total, descuento))


def construir_gestor():
    gestor = GestorAlmacenes()
    almacen_1 = Almacen(1, "Almacen 1")
    almacen_2 = Almacen(2, "Almacen 2")
    almacen_1.inventario.agregar(Producto("Leche", 1200, "Sancor"))
    almacen_1.inventario.agregar(Producto("Leche", 1100, "LaSerenisima"))
    almacen_2.inventario.agregar(Producto("Leche", 1000, "Ilolay"))
    almacen_2.inventario.agregar(Producto("Pan", 500, "Bimbo"))
    gestor.agregar_almacen(almacen_1)
    gestor.agregar_almacen(almacen_2)
    return gestor


class PruebasListas(unittest.TestCase):
    def test_lista_simple(self):
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

    def test_lista_doblemente_enlazada(self):
        lista = ListaDoblementeEnlazada()
        lista.agregar_al_final("B")
        lista.agregar_al_inicio("A")
        lista.agregar_al_final("C")
        self.assertEqual(list(lista.mostrar()), ["A", "B", "C"])
        self.assertEqual(len(lista), 3)
        self.assertEqual(lista.obtener(1), "B")
        self.assertTrue(lista.eliminar("A"))
        self.assertTrue(lista.eliminar("C"))
        self.assertTrue(lista.eliminar("B"))
        self.assertTrue(lista.esta_vacia())
        self.assertFalse(lista.eliminar("Z"))

    def test_observer_notifica(self):
        carrito = CarritoCompras()
        vista = VistaFalsa()
        carrito.agregar_observador(vista)
        carrito.agregar_producto(Producto("Leche", 100))
        carrito.agregar_producto(Producto("Pan", 50))
        carrito.eliminar_producto(0)
        carrito.establecer_estrategia_descuento(SinDescuento())
        self.assertEqual(len(vista.notificaciones), 4)
        self.assertEqual(carrito.calcular_subtotal(), 50)


class PruebasModelo(unittest.TestCase):
    def test_factory_tipos_y_precios(self):
        normal = FabricaProductos.crear_producto("normal", "A", 100)
        fisico = FabricaProductos.crear_producto(
            "fisico", "B", 100, costo_envio=7)
        digital = FabricaProductos.crear_producto("digital", "C", 100)
        suscripcion = FabricaProductos.crear_producto(
            "suscripcion", "D", 10, meses=12)

        self.assertIs(type(normal), Producto)
        self.assertIs(type(fisico), ProductoFisico)
        self.assertIs(type(digital), ProductoDigital)
        self.assertIs(type(suscripcion), ProductoSuscripcion)
        self.assertAlmostEqual(normal.obtener_precio_final(), 100)
        self.assertAlmostEqual(fisico.obtener_precio_final(), 107)
        self.assertAlmostEqual(digital.obtener_precio_final(), 100)
        self.assertAlmostEqual(suscripcion.obtener_precio_final(), 120)

    def test_factory_marca_y_errores(self):
        producto = FabricaProductos.crear_producto(
            "fisico", "TV", 500, marca="Sony", categoria="Electronica",
            costo_envio=10)
        self.assertEqual(producto.marca, "Sony")
        self.assertEqual(producto.categoria, "Electronica")
        with self.assertRaises(ValueError):
            FabricaProductos.crear_producto("inexistente", "X", 1)
        with self.assertRaises(ValueError):
            FabricaProductos.crear_producto("normal", "", 1)
        with self.assertRaises(ValueError):
            FabricaProductos.crear_producto("normal", "X", -1)

    def test_clon_independiente(self):
        original = Producto("Leche", 100, "Marca")
        copia = original.clonar()
        original.precio = 999
        self.assertEqual(copia.precio, 100)
        self.assertEqual(copia.marca, "Marca")


class PruebasEstrategias(unittest.TestCase):
    def test_descuentos(self):
        self.assertAlmostEqual(SinDescuento().calcular(100), 100)
        self.assertAlmostEqual(DescuentoPorcentaje(15).calcular(100), 85)
        self.assertAlmostEqual(DescuentoFijo(30).calcular(100), 70)
        self.assertAlmostEqual(DescuentoFijo(300).calcular(100), 0)

    def test_busquedas(self):
        gestor = construir_gestor()
        lista = ListaDoblementeEnlazada()
        lista.agregar_al_final("Leche")

        por_almacen = BusquedaMejorPrecioStrategy().buscar(lista, gestor)
        self.assertEqual(len(por_almacen), 2)
        precios = sorted(p.precio for lista_p in por_almacen.values()
                         for p in lista_p.mostrar())
        self.assertEqual(precios, [1000, 1100])

        catalogo = BusquedaCatalogoStrategy().buscar(lista, gestor)
        total = sum(len(lista_p) for lista_p in catalogo.values())
        self.assertEqual(total, 3)

        globales = MejorPrecioGlobalStrategy().buscar(lista, gestor)
        self.assertEqual(len(globales), 1)
        self.assertEqual(globales[0]["precio"], 1000)
        self.assertEqual(globales[0]["almacen"].nombre, "Almacen 2")

    def test_busqueda_sin_coincidencias(self):
        gestor = construir_gestor()
        lista = ListaDoblementeEnlazada()
        lista.agregar_al_final("Arroz")
        self.assertEqual(BusquedaMejorPrecioStrategy().buscar(lista, gestor), {})
        self.assertEqual(MejorPrecioGlobalStrategy().buscar(lista, gestor), [])


class PruebasControlador(unittest.TestCase):
    def setUp(self):
        self.carrito = CarritoCompras()
        self.vista = VistaFalsa()
        self.controlador = ControladorCompras(self.carrito, self.vista)
        self.controlador.registrar_usuario("Ana")
        self.controlador.iniciar_sesion("Ana")

    def test_invitado_sin_permisos(self):
        self.controlador.cerrar_sesion()
        self.assertEqual(self.controlador.agregar_producto_usuario("Leche"),
                         "denegado")
        self.assertIn("crear_lista", self.vista.denegados)
        self.assertEqual(self.controlador.exportar_lista("no.csv")["ok"], False)
        self.assertEqual(self.controlador.establecer_descuento("porcentaje", 10),
                         "denegado")

    def test_lista_usuario_y_duplicados(self):
        self.assertEqual(self.controlador.agregar_producto_usuario("Leche"), "ok")
        self.assertEqual(self.controlador.agregar_producto_usuario(" leche "),
                         "duplicado")
        self.assertEqual(self.controlador.obtener_compras_usuario(), ["Leche"])
        self.assertEqual(self.controlador.eliminar_producto_usuario("LECHE"), "ok")
        self.assertEqual(self.controlador.eliminar_producto_usuario("Pan"),
                         "no_encontrado")

    def test_login_admin(self):
        self.assertFalse(self.controlador.login_admin("incorrecta"))
        self.assertTrue(self.controlador.login_admin("admin123"))
        self.assertEqual(self.controlador.obtener_rol(), "ADMIN")

    def test_flujo_admin_y_carrito(self):
        self.assertTrue(self.controlador.login_admin("admin123"))
        self.assertTrue(self.controlador.agregar_producto_almacen(
            1, "Leche", 1000, marca="Ilolay", tipo="normal"))
        self.assertTrue(self.controlador.agregar_producto_almacen(
            2, "Leche", 1200, marca="Sancor", tipo="normal"))
        self.assertEqual(self.controlador.agregar_producto_usuario("Leche"), "ok")

        resultados = self.controlador.ejecutar_busqueda_precios()
        self.assertIn("Leche", [p.nombre for lista_p in resultados.values()
                                for p in lista_p.mostrar()])
        self.assertEqual(len(self.controlador.ejecutar_catalogo()), 2)

        globales = self.controlador.ejecutar_comparacion_global()
        self.assertEqual(globales[0]["precio"], 1000)
        producto = globales[0]["producto"]
        almacen = globales[0]["almacen"]

        self.assertTrue(self.controlador.agregar_seleccion_al_carrito(
            producto, almacen.id_almacen))
        self.assertEqual(self.controlador.obtener_resumen_carrito()["total"], 1000)

        self.assertEqual(self.controlador.establecer_descuento("porcentaje", 10),
                         "ok")
        self.assertAlmostEqual(
            self.controlador.obtener_resumen_carrito()["total"], 900)
        self.assertEqual(self.controlador.establecer_descuento("porcentaje", 150),
                         "invalido")

        self.assertTrue(self.controlador.quitar_producto_carrito(0))
        self.assertEqual(self.controlador.obtener_resumen_carrito()["total"], 0)

    def test_editar_precio(self):
        self.controlador.login_admin("admin123")
        self.controlador.agregar_producto_almacen(1, "Leche", 1000)
        self.assertTrue(self.controlador.editar_precio(1, 0, 800))
        self.assertEqual(
            self.controlador.gestor_almacenes.obtener_almacen(1)
            .inventario.obtener(0).precio, 800)
        self.assertFalse(self.controlador.editar_precio(1, 0, -5))
        self.assertFalse(self.controlador.editar_precio(1, 99, 10))
        self.assertFalse(self.controlador.editar_precio(9, 0, 10))

    def test_cargar_csv(self):
        self.controlador.login_admin("admin123")
        contenido = (
            "almacen,nombre,marca,categoria,tipo,precio,extra\n"
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

        almacen_1 = self.controlador.gestor_almacenes.obtener_almacen(1)
        almacen_2 = self.controlador.gestor_almacenes.obtener_almacen(2)
        self.assertEqual(len(almacen_1.inventario), 3)
        self.assertEqual(len(almacen_2.inventario), 2)
        netflix = [p for p in almacen_1.inventario.mostrar()
                   if p.nombre == "Netflix"][0]
        self.assertEqual(netflix.obtener_precio_final(), 30)

    def test_exportaciones(self):
        self.controlador.login_admin("admin123")
        self.controlador.agregar_producto_almacen(1, "Leche", 1000)
        self.controlador.agregar_producto_usuario("Leche")
        self.controlador.agregar_producto_carrito(
            self.controlador.gestor_almacenes.obtener_almacen(1)
            .inventario.obtener(0))

        descriptor_lista, ruta_lista = tempfile.mkstemp(suffix=".csv")
        descriptor_carrito, ruta_carrito = tempfile.mkstemp(suffix=".csv")
        os.close(descriptor_lista)
        os.close(descriptor_carrito)
        try:
            resultado_lista = self.controlador.exportar_lista(ruta_lista)
            resultado_carrito = self.controlador.exportar_carrito(ruta_carrito)
            self.assertTrue(resultado_lista["ok"])
            self.assertEqual(resultado_lista["filas"], 1)
            self.assertTrue(resultado_carrito["ok"])
            with open(ruta_carrito, newline="", encoding="utf-8") as archivo:
                texto = archivo.read()
            self.assertIn("total", texto)
        finally:
            os.unlink(ruta_lista)
            os.unlink(ruta_carrito)


if __name__ == "__main__":
    unittest.main(verbosity=2)
