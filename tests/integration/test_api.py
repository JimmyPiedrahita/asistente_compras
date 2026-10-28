"""Pruebas de integración de la API HTTP con una persistencia falsa."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from core.config import Settings
from core.errors import NoEncontrado
from models.productos import Producto
from views.api.app import create_app


class PersistenciaFalsa:
    """Repositorio en memoria que imita el contrato de MongoDB."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.datos: dict[int, list[Producto]] = {almacen.id: [] for almacen in settings.almacenes}

    def cargar_almacen(self, id_almacen: int) -> list[Producto]:
        return [producto.clonar() for producto in self.datos.get(id_almacen, [])]

    def insertar(self, id_almacen: int, producto: Producto) -> None:
        self.datos.setdefault(id_almacen, []).append(producto.clonar())

    def actualizar(self, id_almacen: int, producto: Producto) -> None:
        for indice, actual in enumerate(self.datos.get(id_almacen, [])):
            if actual.producto_id == producto.producto_id:
                self.datos[id_almacen][indice] = producto.clonar()
                return
        raise NoEncontrado(f"Producto no encontrado: {producto.producto_id}")

    def ping(self) -> None:
        return None

    def close(self) -> None:
        return None


class PruebasApi(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings.de_pruebas()
        self.app = create_app(self.settings, repository_factory=PersistenciaFalsa)
        self.cliente = TestClient(self.app)

    # Utilidades --------------------------------------------------------

    def _sesion_usuario(self, nombre: str = "Ana") -> str:
        respuesta = self.cliente.post("/api/sessions/user", json={"nombre": nombre})
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["session_id"]

    def _sesion_admin(self) -> str:
        respuesta = self.cliente.post("/api/sessions/admin", json={"clave": "admin123"})
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["session_id"]

    def _agregar_producto(
        self,
        token: str,
        almacen: int = 1,
        nombre: str = "Leche",
        precio: float = 1000,
        marca: str = "Ilolay",
        tipo: str = "normal",
        **extra,
    ) -> dict:
        respuesta = self.cliente.post(
            f"/api/sessions/{token}/admin/warehouses/{almacen}/products",
            json={
                "nombre": nombre,
                "precio": precio,
                "marca": marca,
                "tipo": tipo,
                **extra,
            },
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return respuesta.json()

    def _producto(self, almacen: int = 1) -> dict:
        respuesta = self.cliente.get(f"/api/v1/warehouses/{almacen}/products")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return respuesta.json()[0]

    # Pruebas -----------------------------------------------------------

    def test_api_exige_uri(self) -> None:
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(RuntimeError):
            create_app(None)

    def test_health_y_request_id(self) -> None:
        respuesta = self.cliente.get("/api/v1/health")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["database"], "mongodb")
        self.assertIn("X-Request-ID", respuesta.headers)

        viva = self.cliente.get("/api/v1/health/live", headers={"X-Request-ID": "abc-123"})
        self.assertEqual(viva.status_code, 200)
        self.assertEqual(viva.json(), {"status": "ok"})
        self.assertEqual(viva.headers["X-Request-ID"], "abc-123")

        lista = self.cliente.get("/api/v1/health/ready")
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(lista.json()["status"], "ready")

    def test_legacy_y_v1(self) -> None:
        legacy = self.cliente.get("/api/warehouses")
        moderno = self.cliente.get("/api/v1/warehouses")
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(moderno.status_code, 200)
        self.assertEqual(
            [item["id"] for item in legacy.json()],
            [1, 2, 3],
        )
        self.assertEqual(legacy.json(), moderno.json())

    def test_flujo_usuario_lista_carrito_y_descuento(self) -> None:
        token = self._sesion_usuario()

        respuesta = self.cliente.post(
            f"/api/sessions/{token}/shopping-list",
            json={"nombre": "Leche"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"lista": ["Leche"]})

        duplicado = self.cliente.post(
            f"/api/sessions/{token}/shopping-list",
            json={"nombre": " leche "},
        )
        self.assertEqual(duplicado.status_code, 409)

        listado = self.cliente.get(f"/api/sessions/{token}/shopping-list")
        self.assertEqual(listado.json(), {"lista": ["Leche"]})

        descuento = self.cliente.post(
            f"/api/sessions/{token}/cart/discount",
            json={"tipo": "porcentaje", "valor": 10},
        )
        self.assertEqual(descuento.status_code, 200, descuento.text)
        self.assertEqual(descuento.json()["total"], 0)

        estado = self.cliente.get(f"/api/sessions/{token}")
        self.assertEqual(estado.status_code, 200)
        self.assertEqual(estado.json()["usuario"], "Ana")
        self.assertEqual(estado.json()["rol"], "CLIENTE")
        self.assertEqual(estado.json()["lista"], ["Leche"])

        borrar = self.cliente.delete(f"/api/sessions/{token}/shopping-list/Leche")
        self.assertEqual(borrar.status_code, 200)
        self.assertEqual(borrar.json(), {"lista": []})

    def test_login_admin_alta_busqueda_y_carrito(self) -> None:
        admin = self._sesion_admin()
        self._agregar_producto(admin, almacen=1, precio=1000)
        self._agregar_producto(admin, almacen=2, precio=1200, marca="Sancor")

        almacenes = self.cliente.get("/api/v1/warehouses")
        self.assertEqual([item["products"] for item in almacenes.json()], [1, 1, 0])

        productos = self.cliente.get("/api/v1/warehouses/1/products")
        self.assertEqual(productos.status_code, 200)
        self.assertEqual(len(productos.json()), 1)
        producto = productos.json()[0]
        self.assertEqual(producto["nombre"], "Leche")
        self.assertEqual(producto["precio_final"], 1000)

        inexistente = self.cliente.get("/api/v1/warehouses/99/products")
        self.assertEqual(inexistente.status_code, 404)

        usuario = self._sesion_usuario()
        self.cliente.post(f"/api/sessions/{usuario}/shopping-list", json={"nombre": "Leche"})

        busqueda = self.cliente.post(f"/api/sessions/{usuario}/search", json={"modo": "global"})
        self.assertEqual(busqueda.status_code, 200, busqueda.text)
        resultados = busqueda.json()["resultados"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["almacen_id"], 1)

        agregar = self.cliente.post(
            f"/api/sessions/{usuario}/cart/items",
            json={
                "almacen_id": resultados[0]["almacen_id"],
                "producto_id": resultados[0]["producto"]["producto_id"],
            },
        )
        self.assertEqual(agregar.status_code, 200, agregar.text)
        self.assertEqual(agregar.json()["total"], 1000)

        descuento = self.cliente.post(
            f"/api/sessions/{usuario}/cart/discount",
            json={"tipo": "fijo", "valor": 100},
        )
        self.assertEqual(descuento.status_code, 200)
        self.assertEqual(descuento.json()["total"], 900)

        quitar = self.cliente.delete(f"/api/sessions/{usuario}/cart/items/0")
        self.assertEqual(quitar.status_code, 200)
        self.assertEqual(quitar.json()["total"], 0)

        vaciar = self.cliente.delete(f"/api/sessions/{usuario}/cart")
        self.assertEqual(vaciar.status_code, 200)
        self.assertEqual(vaciar.json()["productos"], [])

    def test_admin_denegado_y_validaciones(self) -> None:
        usuario = self._sesion_usuario()
        denegado = self.cliente.post(
            f"/api/sessions/{usuario}/admin/warehouses/1/products",
            json={"nombre": "Leche", "precio": 100},
        )
        self.assertEqual(denegado.status_code, 403)
        self.assertEqual(denegado.json()["codigo"], "operacion_no_permitida")

        modo_invalido = self.cliente.post(f"/api/sessions/{usuario}/search", json={"modo": "otro"})
        self.assertEqual(modo_invalido.status_code, 422)

        sin_producto = self.cliente.post(
            f"/api/sessions/{usuario}/cart/items",
            json={"almacen_id": 1, "producto_id": "no-existe"},
        )
        self.assertEqual(sin_producto.status_code, 404)

        csv_denegado = self.cliente.post(
            f"/api/sessions/{usuario}/admin/csv",
            json={"contenido": "almacen,nombre,precio\n1,Leche,100\n"},
        )
        self.assertEqual(csv_denegado.status_code, 403)

    def test_patch_precio(self) -> None:
        admin = self._sesion_admin()
        self._agregar_producto(admin)
        producto = self._producto(1)

        actualizado = self.cliente.patch(
            f"/api/sessions/{admin}/admin/warehouses/1/products",
            json={"producto_id": producto["producto_id"], "precio": 800},
        )
        self.assertEqual(actualizado.status_code, 200, actualizado.text)
        self.assertEqual(self._producto(1)["precio"], 800)

        no_encontrado = self.cliente.patch(
            f"/api/sessions/{admin}/admin/warehouses/1/products",
            json={"producto_id": "no-existe", "precio": 800},
        )
        self.assertEqual(no_encontrado.status_code, 404)

        precio_invalido = self.cliente.patch(
            f"/api/sessions/{admin}/admin/warehouses/1/products",
            json={"producto_id": producto["producto_id"], "precio": -1},
        )
        self.assertEqual(precio_invalido.status_code, 422)

    def test_csv_y_recarga(self) -> None:
        admin = self._sesion_admin()
        contenido = (
            "almacen,nombre,marca,precio\n1,Leche,Ilolay,100\n1,Leche,Ilolay,110\n2,Pan,Bimbo,50\n"
        )
        respuesta = self.cliente.post(
            f"/api/sessions/{admin}/admin/csv",
            json={"contenido": contenido},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["importados"], 2)
        self.assertEqual(respuesta.json()["rechazados"], 1)

        recarga = self.cliente.post(f"/api/sessions/{admin}/admin/reload")
        self.assertEqual(recarga.status_code, 200, recarga.text)
        self.assertEqual(len(self.cliente.get("/api/v1/warehouses/1/products").json()), 1)

    def test_exportaciones(self) -> None:
        admin = self._sesion_admin()
        self._agregar_producto(admin)
        usuario = self._sesion_usuario()
        self.cliente.post(f"/api/sessions/{usuario}/shopping-list", json={"nombre": "Leche"})
        producto = self._producto(1)
        self.cliente.post(
            f"/api/sessions/{usuario}/cart/items",
            json={"almacen_id": 1, "producto_id": producto["producto_id"]},
        )

        lista = self.cliente.get(f"/api/sessions/{usuario}/export/shopping-list")
        self.assertEqual(lista.status_code, 200)
        self.assertIn("text/csv", lista.headers["content-type"])
        self.assertIn("producto,marca,precio_final,almacen", lista.text)
        self.assertIn("Leche", lista.text)

        carrito = self.cliente.get(f"/api/sessions/{usuario}/export/cart")
        self.assertEqual(carrito.status_code, 200)
        self.assertIn("total", carrito.text)

    def test_sesion_invalida_y_cierre(self) -> None:
        invalida = self.cliente.get("/api/sessions/inexistente")
        self.assertEqual(invalida.status_code, 401)

        token = self._sesion_usuario()
        cierre = self.cliente.delete(f"/api/sessions/{token}")
        self.assertEqual(cierre.status_code, 204)
        despues = self.cliente.get(f"/api/sessions/{token}")
        self.assertEqual(despues.status_code, 401)

    def test_bearer_token(self) -> None:
        token = self._sesion_usuario()
        respuesta = self.cliente.get(
            "/api/v1/sessions/ruta-ignorada",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["usuario"], "Ana")

    def test_aliases_historicos(self) -> None:
        admin = self._sesion_admin()
        self._agregar_producto(
            admin,
            nombre="Fisico Alias",
            precio=100,
            tipo="Fisico",
            costo_envio=5,
        )
        usuario = self._sesion_usuario()
        self.cliente.post(
            f"/api/sessions/{usuario}/shopping-list",
            json={"nombre": "Fisico Alias"},
        )

        busqueda = self.cliente.post(f"/api/sessions/{usuario}/search", json={"modo": " GLOBAL "})
        self.assertEqual(busqueda.status_code, 200, busqueda.text)
        self.assertEqual(busqueda.json()["modo"], "global")
        self.assertEqual(busqueda.json()["resultados"][0]["producto"]["precio_final"], 105)

        descuento = self.cliente.post(
            f"/api/sessions/{usuario}/cart/discount",
            json={"tipo": "porcentaje (%)", "valor": 10},
        )
        self.assertEqual(descuento.status_code, 200, descuento.text)
        self.assertEqual(descuento.json()["descuento"], "10%")

        sin_descuento = self.cliente.post(
            f"/api/sessions/{usuario}/cart/discount",
            json={"tipo": "sin descuento"},
        )
        self.assertEqual(sin_descuento.status_code, 200, sin_descuento.text)
        self.assertEqual(sin_descuento.json()["descuento"], "Sin descuento")

    def test_openapi(self) -> None:
        esquema = self.cliente.get("/openapi.json")
        self.assertEqual(esquema.status_code, 200)
        self.assertIn("/api/v1/sessions/user", esquema.json()["paths"])


if __name__ == "__main__":
    unittest.main()
