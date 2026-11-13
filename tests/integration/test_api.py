"""Pruebas de integración de la API HTTP con MongoDB real.

Se ejecutan solo cuando ``MONGODB_URI`` está definida. Cada prueba usa una base
de datos temporal que se elimina al terminar.
"""

from __future__ import annotations

import os
import unittest
import uuid

from fastapi.testclient import TestClient
from pymongo import MongoClient

from core.config import Settings
from views.api.app import create_app

MONGODB_URI = os.getenv("MONGODB_URI")

ADMIN_EMAIL = "admin-test@example.com"
ADMIN_PASSWORD = "AdminPass123"

REGISTRO = {
    "nombre": "Ana Cliente",
    "email": "ana@example.com",
    "password": "cliente123",
    "password_confirmacion": "cliente123",
    "telefono": "3001234567",
    "direccion": "Calle 10 # 20-30",
    "ciudad": "Bogotá",
    "autoriza_datos": True,
}


@unittest.skipUnless(MONGODB_URI, "MONGODB_URI no configurada")
class PruebasAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.base_datos = f"test_api_{uuid.uuid4().hex[:10]}"
        self.settings = Settings.de_pruebas(
            mongodb_uri=MONGODB_URI or "",
            mongodb_db=self.base_datos,
            admin_email=ADMIN_EMAIL,
            admin_password=ADMIN_PASSWORD,
        )
        self.app = create_app(self.settings)
        self.repo = self.app.state.repositorio
        self.client = TestClient(self.app)
        self._mongo = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        self.admin = self._login(ADMIN_EMAIL, ADMIN_PASSWORD)

    def tearDown(self) -> None:
        try:
            self._mongo.drop_database(self.base_datos)
        finally:
            self._mongo.close()
            self.repo.close()

    # Utilidades -------------------------------------------------------
    def _login(self, email: str, password: str) -> dict[str, str]:
        respuesta = self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return {"Authorization": f"Bearer {respuesta.json()['session_id']}"}

    def _crear_almacen(self, nombre: str) -> dict:
        respuesta = self.client.post(
            "/api/v1/admin-app/almacenes", json={"nombre": nombre}, headers=self.admin
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def _crear_admin_almacen(self, almacen_id: str, email: str) -> dict[str, str]:
        respuesta = self.client.post(
            "/api/v1/admin-app/administradores",
            json={
                "nombre": f"Admin {email}",
                "email": email,
                "password": "almacen123",
                "almacen_id": almacen_id,
            },
            headers=self.admin,
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return self._login(email, "almacen123")

    def _crear_producto(
        self,
        headers: dict[str, str],
        *,
        tipo: str,
        nombre: str,
        precio: float,
        presentacion: str,
        marca: str = "",
    ) -> dict:
        respuesta = self.client.post(
            "/api/v1/admin-almacen/productos",
            json={
                "tipo_producto": tipo,
                "nombre": nombre,
                "marca_variedad": marca,
                "precio": precio,
                "presentacion": presentacion,
            },
            headers=headers,
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def _preparar_dos_almacenes(self):
        central = self._crear_almacen("Almacén Central")
        norte = self._crear_almacen("Almacén Norte")
        admin_central = self._crear_admin_almacen(central["almacen_id"], "central@example.com")
        admin_norte = self._crear_admin_almacen(norte["almacen_id"], "norte@example.com")
        arroz_central = self._crear_producto(
            admin_central,
            tipo="arroz",
            nombre="Arroz Diana",
            marca="Diana",
            precio=3000,
            presentacion="500 g",
        )
        leche_central = self._crear_producto(
            admin_central,
            tipo="leche",
            nombre="Leche Entera",
            marca="Alpina",
            precio=4500,
            presentacion="1 litro",
        )
        arroz_norte = self._crear_producto(
            admin_norte,
            tipo="arroz",
            nombre="Arroz Roa",
            marca="Roa",
            precio=2500,
            presentacion="500 g",
        )
        return {
            "central": central,
            "norte": norte,
            "admin_central": admin_central,
            "admin_norte": admin_norte,
            "arroz_central": arroz_central,
            "leche_central": leche_central,
            "arroz_norte": arroz_norte,
        }

    def _registrar_cliente(self) -> dict[str, str]:
        respuesta = self.client.post("/api/v1/auth/register", json=REGISTRO)
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return {"Authorization": f"Bearer {respuesta.json()['session_id']}"}

    # Pruebas ----------------------------------------------------------
    def test_estado_inicial_y_cuenta_admin(self) -> None:
        self.assertEqual(self.admin.get("Authorization", "")[:7], "Bearer ")
        sesion = self.client.get("/api/v1/auth/me", headers=self.admin).json()
        self.assertEqual(sesion["rol"], "ADMINISTRADOR_APP")
        self.assertEqual(sesion["email"], ADMIN_EMAIL)

        self.assertEqual(self._mongo[self.base_datos]["almacenes"].count_documents({}), 0)
        self.assertEqual(self._mongo[self.base_datos]["productos"].count_documents({}), 0)
        self.assertEqual(self._mongo[self.base_datos]["cupones"].count_documents({}), 0)
        self.assertEqual(self._mongo[self.base_datos]["compras"].count_documents({}), 0)
        self.assertEqual(self._mongo[self.base_datos]["usuarios"].count_documents({}), 1)

        self.assertEqual(
            self.client.get("/api/v1/admin-app/almacenes", headers=self.admin).json(), []
        )
        self.assertEqual(
            self.client.get("/api/v1/admin-app/administradores", headers=self.admin).json(), []
        )

        incorrecto = self.client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": "incorrecta"},
        )
        self.assertEqual(incorrecto.status_code, 401)
        self.assertEqual(incorrecto.json()["error"], "Credenciales incorrectas")

        # La cuenta inicial no se duplica al reiniciar la aplicación.
        self.repo.inicializar(
            admin_email=ADMIN_EMAIL,
            admin_password=ADMIN_PASSWORD,
            admin_nombre="Administrador",
        )
        self.assertEqual(self._mongo[self.base_datos]["usuarios"].count_documents({}), 1)

    def test_restricciones_por_rol(self) -> None:
        datos = self._preparar_dos_almacenes()
        cliente = self._registrar_cliente()

        # El administrador de la app no accede a funciones del almacén.
        for ruta in (
            "/api/v1/admin-almacen/productos",
            "/api/v1/admin-almacen/cupones",
            "/api/v1/admin-almacen/compras",
            "/api/v1/admin-almacen/estadisticas",
        ):
            self.assertEqual(self.client.get(ruta, headers=self.admin).status_code, 403, ruta)
        self.assertEqual(
            self.client.get("/api/v1/shopping-list", headers=self.admin).status_code, 403
        )
        self.assertEqual(self.client.get("/api/v1/cart", headers=self.admin).status_code, 403)

        # El administrador de almacén no accede a funciones de la app.
        for ruta in ("/api/v1/admin-app/almacenes", "/api/v1/admin-app/administradores"):
            self.assertEqual(
                self.client.get(ruta, headers=datos["admin_central"]).status_code, 403, ruta
            )
        # Ni a funciones del cliente.
        self.assertEqual(
            self.client.get("/api/v1/cart", headers=datos["admin_central"]).status_code, 403
        )
        # Ni a datos de otro almacén.
        productos_norte = self.client.get(
            "/api/v1/admin-almacen/productos", headers=datos["admin_norte"]
        ).json()
        self.assertEqual([p["nombre"] for p in productos_norte], ["Arroz Roa"])

        # El cliente no accede a funciones administrativas.
        for ruta in (
            "/api/v1/admin-almacen/productos",
            "/api/v1/admin-app/almacenes",
        ):
            self.assertEqual(self.client.get(ruta, headers=cliente).status_code, 403, ruta)
        self.assertEqual(
            self.client.post(
                "/api/v1/admin-app/almacenes", json={"nombre": "Otro"}, headers=cliente
            ).status_code,
            403,
        )

        self.assertEqual(
            self.client.get("/api/v1/health/live").status_code,
            200,
        )

    def test_flujo_completo_de_compra(self) -> None:
        datos = self._preparar_dos_almacenes()
        cliente = self._registrar_cliente()

        # Lista de compras.
        self.assertEqual(
            self.client.post(
                "/api/v1/shopping-list", json={"nombre": "arroz"}, headers=cliente
            ).json(),
            {"lista": ["arroz"]},
        )
        self.client.post("/api/v1/shopping-list", json={"nombre": "leche"}, headers=cliente)
        self.assertEqual(
            self.client.post(
                "/api/v1/shopping-list", json={"nombre": "Arroz"}, headers=cliente
            ).status_code,
            400,
        )

        # Tres filtros: catálogo, más barato por almacén y más barato global.
        catalogo = self.client.post(
            "/api/v1/search", json={"modo": "catalogo"}, headers=cliente
        ).json()
        self.assertTrue(catalogo["hay_productos"])
        self.assertEqual(catalogo["total_resultados"], 3)
        self.assertEqual(len(catalogo["grupos"]), 2)

        por_almacen = self.client.post(
            "/api/v1/search", json={"modo": "mejor_precio"}, headers=cliente
        ).json()
        arroz = por_almacen["grupos"][0]["resultados"]
        self.assertEqual(
            [(fila["almacen"], fila["producto"]["precio"]) for fila in arroz],
            [("Almacén Central", 3000), ("Almacén Norte", 2500)],
        )

        global_ = self.client.post(
            "/api/v1/search", json={"modo": "global"}, headers=cliente
        ).json()
        self.assertEqual(global_["total_resultados"], 2)
        self.assertEqual(global_["grupos"][0]["resultados"][0]["almacen"], "Almacén Norte")
        self.assertEqual(global_["grupos"][1]["resultados"][0]["almacen"], "Almacén Central")

        # Carrito con productos de dos almacenes.
        for almacen_id, producto in (
            (datos["central"]["almacen_id"], datos["arroz_central"]),
            (datos["central"]["almacen_id"], datos["leche_central"]),
            (datos["norte"]["almacen_id"], datos["arroz_norte"]),
        ):
            respuesta = self.client.post(
                "/api/v1/cart/items",
                json={
                    "almacen_id": almacen_id,
                    "producto_id": producto["producto_id"],
                    "cantidad": 1,
                },
                headers=cliente,
            )
            self.assertEqual(respuesta.status_code, 200, respuesta.text)

        # Cupón del almacén central: solo descuenta su subtotal.
        cupon = self.client.post(
            "/api/v1/admin-almacen/cupones",
            json={"codigo": "CENTRAL10", "porcentaje": 10},
            headers=datos["admin_central"],
        )
        self.assertEqual(cupon.status_code, 201, cupon.text)
        resumen = self.client.post(
            "/api/v1/cart/coupons", json={"codigo": "central10"}, headers=cliente
        ).json()
        self.assertEqual(resumen["subtotal"], 10000)
        self.assertEqual(resumen["descuento_total"], 750)
        self.assertEqual(resumen["total"], 9250)
        self.assertEqual(len(resumen["cupones_aplicados"]), 1)

        # El mismo código no puede repetirse en otro almacén.
        duplicado = self.client.post(
            "/api/v1/admin-almacen/cupones",
            json={"codigo": "CENTRAL10", "porcentaje": 5},
            headers=datos["admin_norte"],
        )
        self.assertEqual(duplicado.status_code, 409)

        # Un total desactualizado obliga a revisar el resumen.
        conflicto = self.client.post(
            "/api/v1/checkout",
            json={
                "telefono": "3009999999",
                "direccion": "Carrera 5 # 6-7",
                "ciudad": "Medellín",
                "total_esperado": 1,
                "clave_idempotencia": "compra-1",
            },
            headers=cliente,
        )
        self.assertEqual(conflicto.status_code, 409)
        self.assertEqual(conflicto.json()["detalles"]["resumen"]["total"], 9250)

        compra = self.client.post(
            "/api/v1/checkout",
            json={
                "telefono": "3009999999",
                "direccion": "Carrera 5 # 6-7",
                "ciudad": "Medellín",
                "total_esperado": 9250,
                "clave_idempotencia": "compra-1",
            },
            headers=cliente,
        )
        self.assertEqual(compra.status_code, 200, compra.text)
        comprobante = compra.json()
        self.assertTrue(comprobante["pago"])
        self.assertEqual(comprobante["total"], 9250)
        self.assertEqual(comprobante["datos_entrega"]["ciudad"], "Medellín")
        self.assertEqual(len(comprobante["por_almacen"]), 2)
        self.assertEqual(self.client.get("/api/v1/cart", headers=cliente).json()["items"], [])

        # No se duplica la compra: un reintento con la misma clave devuelve la
        # compra existente aunque el carrito ya esté vacío.
        repetida = self.client.post(
            "/api/v1/checkout",
            json={
                "telefono": "3009999999",
                "direccion": "Carrera 5 # 6-7",
                "ciudad": "Medellín",
                "total_esperado": 9250,
                "clave_idempotencia": "compra-1",
            },
            headers=cliente,
        )
        self.assertEqual(repetida.status_code, 200, repetida.text)
        self.assertEqual(repetida.json()["compra_id"], comprobante["compra_id"])
        self.assertEqual(self._mongo[self.base_datos]["compras"].count_documents({}), 1)

        # Cada almacén ve solo su parte de la compra.
        compras_central = self.client.get(
            "/api/v1/admin-almacen/compras", headers=datos["admin_central"]
        ).json()
        self.assertEqual(len(compras_central), 1)
        parte = compras_central[0]
        self.assertEqual(
            {item["nombre"] for item in parte["items"]}, {"Arroz Diana", "Leche Entera"}
        )
        self.assertEqual(parte["subtotal"], 7500)
        self.assertEqual(parte["descuento"], 750)
        self.assertEqual(parte["total"], 6750)
        self.assertEqual(parte["cliente_nombre"], "Ana Cliente")
        self.assertEqual(parte["telefono"], "3009999999")
        self.assertEqual(parte["cupon_codigo"], "CENTRAL10")

        compras_norte = self.client.get(
            "/api/v1/admin-almacen/compras", headers=datos["admin_norte"]
        ).json()
        self.assertEqual(len(compras_norte), 1)
        self.assertEqual([item["nombre"] for item in compras_norte[0]["items"]], ["Arroz Roa"])
        self.assertEqual(compras_norte[0]["total"], 2500)
        self.assertIsNone(compras_norte[0]["cupon_codigo"])

        # Estadísticas por unidades, incluyendo productos con cero ventas.
        self._crear_producto(
            datos["admin_central"],
            tipo="huevos",
            nombre="Huevos AA",
            precio=12000,
            presentacion="docena",
        )
        estadisticas = self.client.get(
            "/api/v1/admin-almacen/estadisticas", headers=datos["admin_central"]
        ).json()
        self.assertTrue(estadisticas["hay_productos"])
        self.assertTrue(estadisticas["hay_ventas"])
        self.assertEqual(
            [(fila["nombre"], fila["unidades_vendidas"]) for fila in estadisticas["mas_vendidos"]],
            [("Arroz Diana", 1), ("Leche Entera", 1), ("Huevos AA", 0)],
        )
        self.assertEqual(estadisticas["menos_vendidos"][0]["nombre"], "Huevos AA")

    def test_csv_completo_o_nada_y_presentacion(self) -> None:
        datos = self._preparar_dos_almacenes()

        # La presentación estándar es común entre almacenes.
        incorrecto = self.client.post(
            "/api/v1/admin-almacen/productos",
            json={
                "tipo_producto": "arroz",
                "nombre": "Arroz Grande",
                "precio": 5000,
                "presentacion": "1 kg",
            },
            headers=datos["admin_norte"],
        )
        self.assertEqual(incorrecto.status_code, 409)

        # Un CSV con una fila inválida no importa nada.
        contenido_invalido = (
            "tipo_producto,nombre,marca_variedad,precio,presentacion\n"
            "arroz,Arroz Integral,Diana,2800,500 g\n"
            "arroz,Arroz Grande,Roa,5000,1 kg\n"
        )
        respuesta = self.client.post(
            "/api/v1/admin-almacen/productos/importar",
            json={"contenido": contenido_invalido, "nombre_archivo": "productos.csv"},
            headers=datos["admin_central"],
        )
        self.assertEqual(respuesta.status_code, 400)
        errores = respuesta.json()["detalles"]["errores"]
        self.assertEqual(errores[0]["fila"], 3)
        self.assertEqual(
            self.client.get("/api/v1/admin-almacen/productos", headers=datos["admin_central"])
            .json()
            .__len__(),
            2,
        )

        # Encabezados y columnas se validan.
        respuesta = self.client.post(
            "/api/v1/admin-almacen/productos/importar",
            json={"contenido": "nombre,precio\nArroz,3000\n", "nombre_archivo": "x.csv"},
            headers=datos["admin_central"],
        )
        self.assertEqual(respuesta.status_code, 400)

        # Un CSV válido agrega todos los productos.
        contenido_valido = (
            "tipo_producto,nombre,marca_variedad,precio,presentacion\n"
            "arroz,Arroz Integral,Diana,2800,500 g\n"
            "arroz,Arroz Premier,Roa,3200,500 g\n"
        )
        respuesta = self.client.post(
            "/api/v1/admin-almacen/productos/importar",
            json={"contenido": contenido_valido, "nombre_archivo": "productos.csv"},
            headers=datos["admin_central"],
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json(), {"importados": 2, "errores": []})
        self.assertEqual(
            len(
                self.client.get(
                    "/api/v1/admin-almacen/productos", headers=datos["admin_central"]
                ).json()
            ),
            4,
        )

    def test_actualizacion_de_credenciales(self) -> None:
        self._preparar_dos_almacenes()
        usuarios = self.client.get("/api/v1/admin-app/administradores", headers=self.admin).json()
        admin_central = next(u for u in usuarios if u["email"] == "central@example.com")

        respuesta = self.client.patch(
            f"/api/v1/admin-app/administradores/{admin_central['usuario_id']}/credenciales",
            json={"email": "nuevo-central@example.com", "password": "nuevaClave123"},
            headers=self.admin,
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        self.assertEqual(respuesta.json()["email"], "nuevo-central@example.com")

        self.assertEqual(
            self.client.post(
                "/api/v1/auth/login",
                json={"email": "central@example.com", "password": "almacen123"},
            ).status_code,
            401,
        )
        self._login("nuevo-central@example.com", "nuevaClave123")

        # El correo no puede repetirse.
        respuesta = self.client.patch(
            f"/api/v1/admin-app/administradores/{admin_central['usuario_id']}/credenciales",
            json={"email": "norte@example.com"},
            headers=self.admin,
        )
        self.assertEqual(respuesta.status_code, 409)

        # El rol del administrador de la app no puede actualizarse por esta vía.
        sesion_admin = self.client.get("/api/v1/auth/me", headers=self.admin).json()
        respuesta = self.client.patch(
            f"/api/v1/admin-app/administradores/{sesion_admin['usuario_id']}/credenciales",
            json={"password": "otraClave123"},
            headers=self.admin,
        )
        self.assertEqual(respuesta.status_code, 404)


if __name__ == "__main__":
    unittest.main()
