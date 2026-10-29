"""Pruebas unitarias de la proyección integrada y del pipeline de cambios."""

from __future__ import annotations

import unittest

from core.config import crear_almacenes
from infrastructure.mongodb.comparador import SincronizadorComparador
from infrastructure.mongodb.documentos import (
    documento_comparador,
    documento_producto,
    id_comparador,
)
from models.almacenes import Almacen, GestorAlmacenes
from models.productos import Producto


class PruebasDocumentosComparador(unittest.TestCase):
    def test_documento_producto_normaliza_campos(self) -> None:
        producto = Producto("  Arroz  Integral ", 950, "Gallo", "Almacen")
        documento = documento_producto(producto)
        self.assertEqual(documento["nombre"], "Arroz  Integral")
        self.assertEqual(documento["nombre_normalizado"], "arroz integral")
        self.assertEqual(documento["marca_normalizada"], "gallo")
        self.assertEqual(documento["_id"], producto.producto_id)

    def test_documento_comparador_usa_id_compuesto_y_precio_final(self) -> None:
        producto = Producto("Arroz", 100, "Gallo")
        documento = documento_comparador(2, "Almacen 2", producto)
        self.assertEqual(documento["_id"], id_comparador(2, producto.producto_id))
        self.assertEqual(documento["producto_id"], producto.producto_id)
        self.assertEqual(documento["almacen_id"], 2)
        self.assertEqual(documento["almacen_nombre"], "Almacen 2")
        self.assertEqual(documento["precio_final"], 100)

    def test_pipeline_incluye_los_almacenes_configurados(self) -> None:
        almacenes = crear_almacenes("tienda")
        pipeline = SincronizadorComparador._pipeline(almacenes)
        match = pipeline[0]["$match"]
        self.assertEqual(match["ns.db"]["$in"], ["tienda_1", "tienda_2", "tienda_3"])
        self.assertIn("delete", match["operationType"]["$in"])

    def test_busquedas_en_memoria_sin_persistencia(self) -> None:
        almacen_1 = Almacen(1, "Almacen 1")
        almacen_2 = Almacen(2, "Almacen 2")
        almacen_1.agregar_producto(Producto("Arroz", 1200, "Gallo"))
        almacen_2.agregar_producto(Producto("Arroz", 900, "Marolio"))
        gestor = GestorAlmacenes(almacenes=(almacen_1, almacen_2))

        globales = gestor.buscar_global(["arroz"])
        self.assertEqual(len(globales), 1)
        self.assertEqual(globales[0]["almacen"].id_almacen, 2)
        self.assertEqual(globales[0]["precio"], 900)

        catalogo = gestor.buscar_catalogo(["Arroz"], limit=1, offset=0)
        self.assertEqual(sum(len(lista) for lista in catalogo.values()), 1)


if __name__ == "__main__":
    unittest.main()
