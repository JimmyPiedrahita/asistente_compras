"""Pruebas unitarias de la replicación de catálogo y compras."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from infrastructure.mongodb.replicacion import ProyectorCompras, SincronizadorCatalogo
from models.almacenes import Almacen


class _ColeccionFake:
    def __init__(self, documentos: list[dict] | None = None) -> None:
        self.documentos = {str(doc["_id"]): doc for doc in documentos or []}

    def find_one(self, filtro: dict) -> dict | None:
        return self.documentos.get(str(filtro.get("_id")))


class _ReplicaFake:
    def __init__(self) -> None:
        self.productos: list[tuple[Almacen, dict]] = []
        self.productos_eliminados: list[tuple[str, str]] = []
        self.cupones: list[tuple[Almacen, dict]] = []
        self.cupones_eliminados: list[tuple[str, str]] = []

    def upsert_producto(self, almacen: Almacen, documento: dict) -> None:
        self.productos.append((almacen, documento))

    def eliminar_producto(self, almacen_id: str, producto_id: str) -> None:
        self.productos_eliminados.append((almacen_id, producto_id))

    def upsert_cupon(self, almacen: Almacen, documento: dict) -> None:
        self.cupones.append((almacen, documento))

    def eliminar_cupon(self, almacen_id: str, cupon_id: str) -> None:
        self.cupones_eliminados.append((almacen_id, cupon_id))


def _cambio(coleccion: str, operacion: str, documento_id: str) -> dict:
    return {
        "ns": {"coll": coleccion},
        "operationType": operacion,
        "documentKey": {"_id": documento_id},
    }


class PruebasSincronizadorCatalogo(unittest.TestCase):
    def setUp(self) -> None:
        self.almacen = Almacen(almacen_id="a1", nombre="Central", db_name="almacen_a1")
        self.replica = _ReplicaFake()
        self.sincronizador = SincronizadorCatalogo(
            settings=None,  # type: ignore[arg-type]
            fabrica=None,  # type: ignore[arg-type]
            conexiones=None,  # type: ignore[arg-type]
            repo_almacenes=None,  # type: ignore[arg-type]
            repo_replica=self.replica,  # type: ignore[arg-type]
        )

    def test_producto_insertado_o_actualizado(self) -> None:
        producto = {"_id": "p1", "tipo_producto": "arroz", "precio": 3000}
        base = {"productos": _ColeccionFake([producto]), "cupones": _ColeccionFake()}
        self.sincronizador._procesar(self.almacen, base, _cambio("productos", "insert", "p1"))
        self.assertEqual(self.replica.productos, [(self.almacen, producto)])

    def test_producto_eliminado(self) -> None:
        base = {"productos": _ColeccionFake(), "cupones": _ColeccionFake()}
        self.sincronizador._procesar(self.almacen, base, _cambio("productos", "delete", "p1"))
        self.assertEqual(self.replica.productos_eliminados, [("a1", "p1")])
        self.assertEqual(self.replica.productos, [])

    def test_producto_inexistente_se_elimina_de_la_replica(self) -> None:
        base = {"productos": _ColeccionFake(), "cupones": _ColeccionFake()}
        self.sincronizador._procesar(self.almacen, base, _cambio("productos", "update", "p1"))
        self.assertEqual(self.replica.productos_eliminados, [("a1", "p1")])

    def test_cupon_insertado_y_eliminado(self) -> None:
        cupon = {"_id": "c1", "codigo": "ARROZ10"}
        base = {"productos": _ColeccionFake(), "cupones": _ColeccionFake([cupon])}
        self.sincronizador._procesar(self.almacen, base, _cambio("cupones", "insert", "c1"))
        self.assertEqual(self.replica.cupones, [(self.almacen, cupon)])

        self.sincronizador._procesar(self.almacen, base, _cambio("cupones", "delete", "c1"))
        self.assertEqual(self.replica.cupones_eliminados, [("a1", "c1")])

    def test_coleccion_desconocida_no_hace_nada(self) -> None:
        base = {"productos": _ColeccionFake(), "cupones": _ColeccionFake()}
        self.sincronizador._procesar(self.almacen, base, _cambio("otra", "insert", "x"))
        self.assertEqual(self.replica.productos, [])
        self.assertEqual(self.replica.cupones, [])


class _RepoAlmacenesFake:
    def __init__(self, almacenes: list[Almacen]) -> None:
        self._almacenes = {almacen.almacen_id: almacen for almacen in almacenes}

    def obtener(self, almacen_id: str) -> Almacen | None:
        return self._almacenes.get(str(almacen_id))

    def listar(self) -> list[Almacen]:
        return list(self._almacenes.values())


class _RepoAlmacenFake:
    def __init__(self, ids: set[str] | None = None) -> None:
        self.compras: list[dict] = []
        self.eliminadas: list[str] = []
        self._ids = ids or set()

    def upsert_compra(self, documento: dict) -> None:
        self.compras.append(documento)

    def eliminar_compra(self, compra_id: str) -> None:
        self.eliminadas.append(compra_id)

    def listar_ids_compras(self) -> set[str]:
        return set(self._ids)


class _RepoComprasFake:
    def __init__(self, compras: list[dict] | None = None) -> None:
        self.compras = compras or []

    def listar_compras(self) -> list[dict]:
        return list(self.compras)


class _EstadoFake:
    def __init__(self) -> None:
        self.tokens: list[tuple[object, str]] = []

    def guardar_token(self, token: object, *, estado: str = "activo") -> None:
        self.tokens.append((token, estado))


class PruebasProyectorCompras(unittest.TestCase):
    def setUp(self) -> None:
        self.a = Almacen(almacen_id="a1", nombre="A", db_name="almacen_a1")
        self.b = Almacen(almacen_id="b1", nombre="B", db_name="almacen_b1")
        self.repo_a = _RepoAlmacenFake()
        self.repo_b = _RepoAlmacenFake()
        self.estado = _EstadoFake()
        self.proyector = ProyectorCompras(
            settings=None,  # type: ignore[arg-type]
            fabrica=None,  # type: ignore[arg-type]
            conexiones=None,  # type: ignore[arg-type]
            repo_almacenes=_RepoAlmacenesFake([self.a, self.b]),  # type: ignore[arg-type]
            repo_compras=_RepoComprasFake(),  # type: ignore[arg-type]
            repo_estado=self.estado,  # type: ignore[arg-type]
        )
        self._repos = {"a1": self.repo_a, "b1": self.repo_b}
        self._parche = patch.object(
            self.proyector,
            "_repositorio_almacen",
            side_effect=lambda almacen: self._repos[almacen.almacen_id],
        )
        self._parche.start()
        self.addCleanup(self._parche.stop)

    def _compra(self) -> dict:
        return {
            "_id": "compra-1",
            "cliente_id": "cliente-1",
            "cliente_nombre": "Ana",
            "fecha": "2026-01-01T00:00:00+00:00",
            "datos_entrega": {
                "telefono": "3001234567",
                "direccion": "Calle 1",
                "ciudad": "Bogotá",
            },
            "items": [
                {"almacen_id": "a1", "nombre": "Arroz", "cantidad": 2},
                {"almacen_id": "b1", "nombre": "Leche", "cantidad": 1},
            ],
            "por_almacen": [
                {"almacen_id": "a1", "subtotal": 6000, "total": 6000},
                {"almacen_id": "b1", "subtotal": 4500, "total": 4500},
            ],
            "pago": True,
            "pago_detalle": {"estado": "APPROVED"},
        }

    def test_proyecta_solo_la_parte_de_cada_almacen(self) -> None:
        self.proyector._proyectar(self._compra())

        self.assertEqual(len(self.repo_a.compras), 1)
        self.assertEqual([item["nombre"] for item in self.repo_a.compras[0]["items"]], ["Arroz"])
        self.assertEqual(self.repo_a.compras[0]["telefono"], "3001234567")
        self.assertEqual(self.repo_a.compras[0]["total"], 6000)

        self.assertEqual(len(self.repo_b.compras), 1)
        self.assertEqual([item["nombre"] for item in self.repo_b.compras[0]["items"]], ["Leche"])
        self.assertEqual(self.repo_b.compras[0]["total"], 4500)

    def test_compra_vacia_no_hace_nada(self) -> None:
        self.proyector._proyectar(None)
        self.proyector._proyectar({})
        self.assertEqual(self.repo_a.compras, [])
        self.assertEqual(self.repo_b.compras, [])

    def test_elimina_la_proyeccion_en_todos_los_almacenes(self) -> None:
        self.proyector._eliminar("compra-1")
        self.assertEqual(self.repo_a.eliminadas, ["compra-1"])
        self.assertEqual(self.repo_b.eliminadas, ["compra-1"])

    def test_compra_pendiente_solo_limpia_sus_almacenes(self) -> None:
        compra = self._compra()
        compra["pago"] = False
        compra["pago_detalle"] = {"estado": "PENDING"}
        compra["por_almacen"] = [{"almacen_id": "a1", "subtotal": 6000, "total": 6000}]

        self.proyector._proyectar(compra)

        self.assertEqual(self.repo_a.eliminadas, ["compra-1"])
        self.assertEqual(self.repo_b.eliminadas, [])
        self.assertEqual(self.repo_a.compras, [])
        self.assertEqual(self.repo_b.compras, [])

    def test_reconciliar_todo_elimina_proyecciones_obsoletas(self) -> None:
        self.repo_a._ids = {"compra-1", "obsoleta"}
        self.repo_b._ids = {"obsoleta"}
        self.proyector.repo_compras = _RepoComprasFake([self._compra()])

        self.proyector.reconciliar_todo()

        self.assertEqual(len(self.repo_a.compras), 1)
        self.assertEqual(len(self.repo_b.compras), 1)
        self.assertEqual(self.repo_a.eliminadas, ["obsoleta"])
        self.assertEqual(self.repo_b.eliminadas, ["obsoleta"])
        self.assertEqual(self.estado.tokens, [(None, "reconciliado")])


if __name__ == "__main__":
    unittest.main()
