import unittest

from fastapi.testclient import TestClient

from views.api.app import create_app


class _Admin:
    def command(self, name):
        if name != "ping":
            raise ValueError(name)
        return {"ok": 1}


class PersistenciaFalsa:
    def __init__(self, uri):
        self.uri = uri
        self.client = type("Cliente", (), {"admin": _Admin()})()

    def cargar_almacen(self, id_almacen):
        return []

    def insertar(self, id_almacen, producto):
        return None

    def actualizar(self, id_almacen, producto):
        return None


class PruebasApi(unittest.TestCase):
    def setUp(self):
        self.cliente = TestClient(
            create_app(
                "mongodb://pruebas",
                repository_factory=PersistenciaFalsa,
            )
        )

    def test_api_exige_uri(self):
        with self.assertRaises(RuntimeError):
            create_app(None)

    def test_flujo_usuario_lista_carrito_y_descuento(self):
        respuesta = self.cliente.post(
            "/api/sessions/user", json={"nombre": "Ana"}
        )
        self.assertEqual(respuesta.status_code, 201)
        token = respuesta.json()["session_id"]

        respuesta = self.cliente.post(
            f"/api/sessions/{token}/shopping-list",
            json={"nombre": "Leche"},
        )
        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            self.cliente.post(
                f"/api/sessions/{token}/cart/discount",
                json={"tipo": "porcentaje", "valor": 10},
            ).status_code,
            200,
        )
        carrito = self.cliente.get(f"/api/sessions/{token}/cart").json()
        self.assertEqual(carrito["total"], 0)

    def test_login_admin_y_alta_de_producto(self):
        respuesta = self.cliente.post(
            "/api/sessions/admin", json={"clave": "admin123"}
        )
        self.assertEqual(respuesta.status_code, 201)
        token = respuesta.json()["session_id"]
        respuesta = self.cliente.post(
            f"/api/sessions/{token}/admin/warehouses/1/products",
            json={"nombre": "Leche", "precio": 100},
        )
        self.assertEqual(respuesta.status_code, 200)

    def test_sesion_invalida(self):
        respuesta = self.cliente.get("/api/sessions/inexistente")
        self.assertEqual(respuesta.status_code, 401)

    def test_api_v1_expone_health_y_almacenes(self):
        health = self.cliente.get("/api/v1/health/live")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})

        almacenes = self.cliente.get("/api/v1/warehouses")
        self.assertEqual(almacenes.status_code, 200)
        self.assertEqual([item["id"] for item in almacenes.json()], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
