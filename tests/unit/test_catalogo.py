"""Pruebas de lista de compras y filtros de búsqueda."""

from __future__ import annotations

import unittest

from controllers.catalogo import ControladorCatalogo
from controllers.sesiones import Sesion
from core.errors import SolicitudInvalida
from models.almacenes import Almacen
from models.productos import Producto


def producto(
    producto_id: str,
    almacen_id: str,
    nombre: str,
    precio: float,
    tipo: str = "arroz",
) -> Producto:
    return Producto.crear(
        producto_id=producto_id,
        almacen_id=almacen_id,
        tipo_producto=tipo,
        nombre=nombre,
        precio=precio,
        presentacion="500 g",
    )


class RepoFalso:
    def __init__(self, filas: list[tuple[Producto, Almacen]]) -> None:
        self.filas = filas

    def contar_productos(self) -> int:
        return len(self.filas)

    def buscar_por_tipos(self, tipos):
        normalizados = {" ".join(str(t).casefold().split()) for t in tipos}
        return [
            (producto, almacen)
            for producto, almacen in self.filas
            if producto.tipo_normalizado in normalizados
        ]


def sesion(lista: list[str]) -> Sesion:
    creada = Sesion(
        token="token",
        usuario_id="u1",
        nombre="Ana",
        email="ana@example.com",
        rol="CLIENTE",
        almacen_id=None,
    )
    creada.lista = list(lista)
    return creada


class PruebasLista(unittest.TestCase):
    def setUp(self) -> None:
        self.controlador = ControladorCatalogo(RepoFalso([]))

    def test_agregar_y_quitar_sin_duplicados(self) -> None:
        creada = sesion([])
        self.assertEqual(self.controlador.agregar_a_lista(creada, "  Arroz  "), ["Arroz"])
        with self.assertRaises(SolicitudInvalida):
            self.controlador.agregar_a_lista(creada, "arroz")
        self.assertEqual(self.controlador.agregar_a_lista(creada, "Leche"), ["Arroz", "Leche"])
        self.assertEqual(self.controlador.quitar_de_lista(creada, "ARROZ"), ["Leche"])
        with self.assertRaises(SolicitudInvalida):
            self.controlador.quitar_de_lista(creada, "Pan")
        with self.assertRaises(SolicitudInvalida):
            self.controlador.agregar_a_lista(creada, "   ")


class PruebasBusqueda(unittest.TestCase):
    def setUp(self) -> None:
        self.a = Almacen(almacen_id="a", nombre="Almacén A")
        self.b = Almacen(almacen_id="b", nombre="Almacén B")
        self.filas = [
            (producto("p1", "a", "Zeta", 1000), self.a),
            (producto("p2", "a", "Alfa", 1000), self.a),
            (producto("p3", "b", "Beta", 900), self.b),
            (producto("p4", "b", "Arroz Integral", 2500, "arroz integral"), self.b),
        ]
        self.controlador = ControladorCatalogo(RepoFalso(self.filas))

    def test_catalogo_muestra_todas_las_coincidencias(self) -> None:
        resultado = self.controlador.buscar(sesion(["arroz"]), "catalogo")
        grupo = resultado["grupos"][0]
        self.assertTrue(resultado["hay_productos"])
        self.assertEqual(resultado["total_resultados"], 3)
        self.assertEqual(
            [fila["producto"]["producto_id"] for fila in grupo["resultados"]],
            ["p2", "p1", "p3"],
        )
        self.assertFalse(grupo["sin_resultados"])

    def test_mejor_precio_por_almacen(self) -> None:
        resultado = self.controlador.buscar(sesion(["arroz"]), "mejor_precio")
        filas = resultado["grupos"][0]["resultados"]
        self.assertEqual(len(filas), 2)
        # En el almacén A hay empate al mismo precio: gana "Alfa" alfabéticamente.
        self.assertEqual(filas[0]["producto"]["producto_id"], "p2")
        self.assertEqual(filas[1]["producto"]["producto_id"], "p3")

    def test_mejor_precio_global_usa_desempate_por_almacen(self) -> None:
        self.filas.append((producto("p5", "b", "Aaa", 900), self.b))
        # Ante empate de precio, el desempate global mira primero el nombre del
        # almacén; ambos candidatos a 900 son del almacén B, así que decide el
        # nombre del producto.
        resultado = self.controlador.buscar(sesion(["arroz"]), "global")
        filas = resultado["grupos"][0]["resultados"]
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["producto"]["producto_id"], "p5")

    def test_global_prioriza_nombre_de_almacen(self) -> None:
        filas = [
            (producto("p1", "b", "Arroz B", 1000), self.b),
            (producto("p2", "a", "Arroz Z", 1000), self.a),
        ]
        controlador = ControladorCatalogo(RepoFalso(filas))
        resultado = controlador.buscar(sesion(["arroz"]), "global")
        self.assertEqual(resultado["grupos"][0]["resultados"][0]["producto"]["producto_id"], "p2")

    def test_grupos_sin_resultados_y_catalogo_vacio(self) -> None:
        resultado = self.controlador.buscar(sesion(["arroz", "leche"]), "catalogo")
        self.assertEqual(len(resultado["grupos"]), 2)
        self.assertTrue(resultado["grupos"][1]["sin_resultados"])
        self.assertEqual(resultado["total_resultados"], 3)

        vacio = ControladorCatalogo(RepoFalso([]))
        resultado = vacio.buscar(sesion(["arroz"]), "catalogo")
        self.assertFalse(resultado["hay_productos"])
        self.assertEqual(resultado["total_resultados"], 0)

    def test_modo_invalido_y_lista_vacia(self) -> None:
        with self.assertRaises(SolicitudInvalida):
            self.controlador.buscar(sesion(["arroz"]), "otro")
        with self.assertRaises(SolicitudInvalida):
            self.controlador.buscar(sesion([]), "catalogo")


if __name__ == "__main__":
    unittest.main()
