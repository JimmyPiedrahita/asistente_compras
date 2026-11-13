"""Pruebas de integración de la API HTTP con una persistencia falsa."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from core.config import Settings
from core.errors import Conflicto, NoEncontrado
from models.almacenes import Almacen
from models.listas import ListaSimple
from models.productos import Producto
from models.texto import normalizar_texto
from views.api.app import create_app


class PersistenciaFalsa:
    """Repositorio en memoria que imita el contrato de MongoDB.

    Las escrituras actualizan ``datos`` y ``comparador`` de forma síncrona para
    simular lo que el listener hace con Change Streams.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.datos: dict[int, list[Producto]] = {almacen.id: [] for almacen in settings.almacenes}
        self.comparador: dict[tuple[int, str], Producto] = {}
        self._modelos = {
            almacen.id: Almacen(almacen.id, almacen.nombre) for almacen in settings.almacenes
        }
        self.reconciliaciones = 0

    def _proyectar(self, id_almacen: int, producto: Producto) -> None:
        self.comparador[(int(id_almacen), producto.producto_id)] = producto.clonar()

    def _desproyectar(self, id_almacen: int, producto_id: str) -> None:
        self.comparador.pop((int(id_almacen), str(producto_id)), None)

    def cargar_almacen(self, id_almacen: int) -> list[Producto]:
        return [producto.clonar() for producto in self.datos.get(id_almacen, [])]

    def listar_productos(
        self, id_almacen: int, limit: int = 100, offset: int = 0
    ) -> tuple[list[Producto], int]:
        productos = self.datos.get(id_almacen, [])
        return (
            [producto.clonar() for producto in productos[offset : offset + limit]],
            len(productos),
        )

    def producto_en_indice(self, id_almacen: int, indice: int) -> Producto | None:
        try:
            return self.datos.get(id_almacen, [])[indice].clonar()
        except IndexError:
            return None

    def obtener_producto(self, id_almacen: int, producto_id: str) -> Producto | None:
        for producto in self.datos.get(id_almacen, []):
            if producto.producto_id == str(producto_id):
                return producto.clonar()
        return None

    def existe_nombre_marca(self, id_almacen: int, nombre: str, marca: str | None = None) -> bool:
        for producto in self.datos.get(id_almacen, []):
            if normalizar_texto(producto.nombre) != normalizar_texto(nombre):
                continue
            if marca is None or normalizar_texto(producto.marca) == normalizar_texto(marca):
                return True
        return False

    def contar(self, id_almacen: int) -> int:
        return len(self.datos.get(id_almacen, []))

    def insertar(self, id_almacen: int, producto: Producto) -> None:
        if any(
            actual.producto_id == producto.producto_id for actual in self.datos.get(id_almacen, [])
        ):
            raise Conflicto(f"El producto {producto.producto_id} ya existe")
        self.datos.setdefault(id_almacen, []).append(producto.clonar())
        self._proyectar(id_almacen, producto)

    def actualizar(self, id_almacen: int, producto: Producto) -> None:
        for indice, actual in enumerate(self.datos.get(id_almacen, [])):
            if actual.producto_id == producto.producto_id:
                self.datos[id_almacen][indice] = producto.clonar()
                self._proyectar(id_almacen, producto)
                return
        raise NoEncontrado(f"Producto no encontrado: {producto.producto_id}")

    def eliminar(self, id_almacen: int, producto_id: str) -> None:
        productos = self.datos.get(id_almacen, [])
        for indice, actual in enumerate(productos):
            if actual.producto_id == str(producto_id):
                productos.pop(indice)
                self._desproyectar(id_almacen, producto_id)
                return
        raise NoEncontrado(f"Producto no encontrado: {producto_id}")

    def buscar_mejor_precio(self, nombres) -> dict[Almacen, ListaSimple]:
        buscados = {normalizar_texto(nombre) for nombre in nombres}
        mejores: dict[tuple[int, str], Producto] = {}
        for (id_almacen, _), producto in self.comparador.items():
            nombre = normalizar_texto(producto.nombre)
            if nombre not in buscados:
                continue
            clave = (id_almacen, nombre)
            actual = mejores.get(clave)
            if actual is None or producto.obtener_precio_final() < actual.obtener_precio_final():
                mejores[clave] = producto

        resultado: dict[Almacen, ListaSimple] = {}
        for (id_almacen, _), producto in sorted(mejores.items()):
            resultado.setdefault(self._modelos[id_almacen], ListaSimple()).agregar(
                producto.clonar()
            )
        return resultado

    def buscar_catalogo(self, nombres, limit: int = 100, offset: int = 0) -> dict:
        buscados = {normalizar_texto(nombre) for nombre in nombres}
        encontrados = [
            (id_almacen, producto)
            for (id_almacen, _), producto in self.comparador.items()
            if normalizar_texto(producto.nombre) in buscados
        ]
        encontrados.sort(
            key=lambda item: (
                item[0],
                normalizar_texto(item[1].nombre),
                item[1].obtener_precio_final(),
                item[1].producto_id,
            )
        )
        resultado: dict[Almacen, ListaSimple] = {}
        for id_almacen, producto in encontrados[offset : offset + limit]:
            resultado.setdefault(self._modelos[id_almacen], ListaSimple()).agregar(
                producto.clonar()
            )
        return resultado

    def buscar_global(self, nombres) -> list[dict]:
        resultado = []
        for nombre in nombres:
            buscado = normalizar_texto(nombre)
            candidatos = [
                (id_almacen, producto)
                for (id_almacen, _), producto in self.comparador.items()
                if normalizar_texto(producto.nombre) == buscado
            ]
            if not candidatos:
                continue
            id_almacen, producto = min(candidatos, key=lambda item: item[1].obtener_precio_final())
            resultado.append(
                {
                    "nombre": producto.nombre,
                    "producto": producto.clonar(),
                    "almacen": self._modelos[id_almacen],
                    "precio": producto.obtener_precio_final(),
                }
            )
        return resultado

    def estado_comparador(self) -> dict:
        return {
            "estado": "sincronizado",
            "documentos": len(self.comparador),
            "ultima_sincronizacion": None,
            "ultimo_evento": "prueba",
            "tiene_resume_token": True,
        }

    def reconciliar_comparador(self) -> dict:
        self.comparador.clear()
        for id_almacen, productos in self.datos.items():
            for producto in productos:
                self._proyectar(id_almacen, producto)
        self.reconciliaciones += 1
        return {
            "documentos": len(self.comparador),
            "reconciliados": len(self.comparador),
        }

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

    def test_busqueda_global_devuelve_solo_el_mas_barato(self) -> None:
        admin = self._sesion_admin()
        self._agregar_producto(admin, almacen=1, precio=1200, marca="Sancor")
        self._agregar_producto(admin, almacen=2, precio=1000, marca="Ilolay")
        self._agregar_producto(admin, almacen=3, precio=1500, marca="LaSerenisima")

        usuario = self._sesion_usuario()
        self.cliente.post(f"/api/sessions/{usuario}/shopping-list", json={"nombre": "Leche"})

        globales = self.cliente.post(f"/api/sessions/{usuario}/search", json={"modo": "global"})
        self.assertEqual(globales.status_code, 200, globales.text)
        resultados = globales.json()["resultados"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["almacen_id"], 2)
        self.assertEqual(resultados[0]["producto"]["precio"], 1000)

        catalogo = self.cliente.post(f"/api/sessions/{usuario}/search", json={"modo": "catalogo"})
        self.assertEqual(catalogo.status_code, 200, catalogo.text)
        self.assertEqual(len(catalogo.json()["resultados"]), 3)

    def test_paginacion_de_productos(self) -> None:
        admin = self._sesion_admin()
        for nombre in ("Arroz", "Cafe", "Aceite"):
            self._agregar_producto(admin, nombre=nombre, precio=100)

        primera = self.cliente.get("/api/v1/warehouses/1/products?limit=1&offset=0")
        self.assertEqual(primera.status_code, 200, primera.text)
        self.assertEqual(len(primera.json()), 1)
        self.assertEqual(primera.headers["X-Total-Count"], "3")

        segunda = self.cliente.get("/api/v1/warehouses/1/products?limit=1&offset=1")
        self.assertEqual(segunda.status_code, 200, segunda.text)
        self.assertEqual(len(segunda.json()), 1)
        self.assertNotEqual(primera.json()[0]["producto_id"], segunda.json()[0]["producto_id"])

        fuera = self.cliente.get("/api/v1/warehouses/1/products?limit=1&offset=99")
        self.assertEqual(fuera.status_code, 200)
        self.assertEqual(fuera.json(), [])

    def test_eliminar_producto_y_comparador(self) -> None:
        admin = self._sesion_admin()
        self._agregar_producto(admin, almacen=1, nombre="Arroz", precio=900)
        producto = self._producto(1)

        usuario = self._sesion_usuario()
        self.cliente.post(f"/api/sessions/{usuario}/shopping-list", json={"nombre": "Arroz"})
        antes = self.cliente.post(f"/api/sessions/{usuario}/search", json={"modo": "global"})
        self.assertEqual(len(antes.json()["resultados"]), 1)

        borrado = self.cliente.delete(
            f"/api/sessions/{admin}/admin/warehouses/1/products/{producto['producto_id']}"
        )
        self.assertEqual(borrado.status_code, 200, borrado.text)
        self.assertEqual(self.cliente.get("/api/v1/warehouses/1/products").json(), [])

        despues = self.cliente.post(f"/api/sessions/{usuario}/search", json={"modo": "global"})
        self.assertEqual(despues.json()["resultados"], [])

        repetido = self.cliente.delete(
            f"/api/sessions/{admin}/admin/warehouses/1/products/{producto['producto_id']}"
        )
        self.assertEqual(repetido.status_code, 404)

    def test_estado_y_reconciliacion_de_comparador(self) -> None:
        admin = self._sesion_admin()
        self._agregar_producto(admin, almacen=1)
        estado = self.cliente.get(f"/api/sessions/{admin}/admin/comparador/status")
        self.assertEqual(estado.status_code, 200, estado.text)
        self.assertEqual(estado.json()["documentos"], 1)

        reconciliacion = self.cliente.post(f"/api/sessions/{admin}/admin/comparador/reconciliar")
        self.assertEqual(reconciliacion.status_code, 200, reconciliacion.text)

        usuario = self._sesion_usuario()
        denegado = self.cliente.get(f"/api/sessions/{usuario}/admin/comparador/status")
        self.assertEqual(denegado.status_code, 403)

    def test_openapi(self) -> None:
        esquema = self.cliente.get("/openapi.json")
        self.assertEqual(esquema.status_code, 200)
        self.assertIn("/api/v1/sessions/user", esquema.json()["paths"])

    # Roles, usuarios y proveedor --------------------------------------
    def _crear_proveedor(self, admin: str, nombre: str = "Proveedor Uno", almacen: int = 1):
        respuesta = self.cliente.post(
            f"/api/sessions/{admin}/users/providers",
            json={"nombre": nombre, "almacen_id": almacen},
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()

    def _sesion_proveedor(self, nombre: str = "Proveedor Uno") -> str:
        respuesta = self.cliente.post("/api/sessions/provider", json={"nombre": nombre})
        self.assertEqual(respuesta.status_code, 201, respuesta.text)
        return respuesta.json()["session_id"]

    def test_catalogo_de_roles_y_permisos(self) -> None:
        respuesta = self.cliente.get("/api/v1/roles")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        datos = respuesta.json()
        roles = {rol["rol"]: rol for rol in datos["roles"]}
        self.assertEqual(set(roles), {"INVITADO", "CLIENTE", "PROVEEDOR", "ADMIN"})
        self.assertIn("gestionar_inventario", roles["PROVEEDOR"]["permisos"])
        self.assertNotIn("crear_lista", roles["PROVEEDOR"]["permisos"])
        self.assertNotIn("gestionar_usuarios", roles["CLIENTE"]["permisos"])
        self.assertIn("gestionar_usuarios", roles["ADMIN"]["permisos"])
        permisos = {permiso["codigo"] for permiso in datos["permisos"]}
        self.assertIn("editar_precio", permisos)
        self.assertIn("importar_csv", permisos)

        proveedor = self.cliente.get("/api/v1/roles/proveedor")
        self.assertEqual(proveedor.status_code, 200)
        self.assertEqual(proveedor.json()["rol"], "PROVEEDOR")

        inexistente = self.cliente.get("/api/v1/roles/OTRO")
        self.assertEqual(inexistente.status_code, 404)

    def test_admin_gestiona_proveedores(self) -> None:
        admin = self._sesion_admin()
        proveedor = self._crear_proveedor(admin, "Distribuidora Norte", 2)
        self.assertEqual(proveedor["rol"], "PROVEEDOR")
        self.assertEqual(proveedor["almacen_id"], 2)
        self.assertTrue(proveedor["activo"])

        duplicado = self.cliente.post(
            f"/api/sessions/{admin}/users/providers",
            json={"nombre": "Distribuidora Norte", "almacen_id": 1},
        )
        self.assertEqual(duplicado.status_code, 409)

        almacen_invalido = self.cliente.post(
            f"/api/sessions/{admin}/users/providers",
            json={"nombre": "Otro", "almacen_id": 99},
        )
        self.assertEqual(almacen_invalido.status_code, 404)

        listado = self.cliente.get(f"/api/sessions/{admin}/users")
        self.assertEqual(listado.status_code, 200)
        self.assertEqual([u["nombre"] for u in listado.json()], ["Distribuidora Norte"])

        usuario_id = proveedor["usuario_id"]
        desactivado = self.cliente.patch(
            f"/api/sessions/{admin}/users/{usuario_id}",
            json={"activo": False},
        )
        self.assertEqual(desactivado.status_code, 200, desactivado.text)
        self.assertFalse(desactivado.json()["activo"])

        login_inactivo = self.cliente.post(
            "/api/sessions/provider", json={"nombre": "Distribuidora Norte"}
        )
        self.assertEqual(login_inactivo.status_code, 401)

        reactivado = self.cliente.patch(
            f"/api/sessions/{admin}/users/{usuario_id}",
            json={"activo": True, "almacen_id": 3},
        )
        self.assertEqual(reactivado.status_code, 200, reactivado.text)
        self.assertEqual(reactivado.json()["almacen_id"], 3)

        proveedor_sin_almacen = self.cliente.patch(
            f"/api/sessions/{admin}/users/{usuario_id}",
            json={"almacen_id": None},
        )
        self.assertEqual(proveedor_sin_almacen.status_code, 400)

    def test_proveedor_solo_opera_su_almacen(self) -> None:
        admin = self._sesion_admin()
        self._crear_proveedor(admin, "Proveedor Norte", 1)
        proveedor = self._sesion_proveedor("Proveedor Norte")

        crear_propio = self.cliente.post(
            f"/api/sessions/{proveedor}/admin/warehouses/1/products",
            json={"nombre": "Leche", "precio": 1000},
        )
        self.assertEqual(crear_propio.status_code, 200, crear_propio.text)

        crear_ajeno = self.cliente.post(
            f"/api/sessions/{proveedor}/admin/warehouses/2/products",
            json={"nombre": "Pan", "precio": 500},
        )
        self.assertEqual(crear_ajeno.status_code, 403)
        self.assertIn("almacén", crear_ajeno.json()["error"].lower())

        producto = self._producto(1)
        precio_propio = self.cliente.patch(
            f"/api/sessions/{proveedor}/admin/warehouses/1/products",
            json={"producto_id": producto["producto_id"], "precio": 900},
        )
        self.assertEqual(precio_propio.status_code, 200, precio_propio.text)
        self.assertEqual(self._producto(1)["precio"], 900)

        precio_ajeno = self.cliente.patch(
            f"/api/sessions/{proveedor}/admin/warehouses/2/products",
            json={"producto_id": producto["producto_id"], "precio": 800},
        )
        self.assertEqual(precio_ajeno.status_code, 403)

        csv = self.cliente.post(
            f"/api/sessions/{proveedor}/admin/csv",
            json={
                "contenido": (
                    "almacen,nombre,marca,precio\n1,Arroz,Generica,100\n2,Fideos,Generica,200\n"
                )
            },
        )
        self.assertEqual(csv.status_code, 200, csv.text)
        self.assertEqual(csv.json()["importados"], 1)
        self.assertEqual(csv.json()["rechazados"], 1)

        estado = self.cliente.get(f"/api/sessions/{proveedor}")
        self.assertEqual(estado.status_code, 200)
        self.assertEqual(estado.json()["rol"], "PROVEEDOR")
        self.assertEqual(estado.json()["almacen_id"], 1)
        self.assertIn("gestionar_inventario", estado.json()["permisos"])
        self.assertNotIn("crear_lista", estado.json()["permisos"])

        comparador = self.cliente.get(f"/api/sessions/{proveedor}/admin/comparador/status")
        self.assertEqual(comparador.status_code, 403)

        busqueda = self.cliente.post(f"/api/sessions/{proveedor}/search", json={})
        self.assertEqual(busqueda.status_code, 403)

        usuarios = self.cliente.get(f"/api/sessions/{proveedor}/users")
        self.assertEqual(usuarios.status_code, 403)

    def test_cliente_no_puede_gestionar_usuarios_ni_inventario(self) -> None:
        cliente = self._sesion_usuario("Cliente Uno")
        usuarios = self.cliente.get(f"/api/sessions/{cliente}/users")
        self.assertEqual(usuarios.status_code, 403)
        self.assertIn("Listar usuarios", usuarios.json()["error"])

        inventario = self.cliente.post(
            f"/api/sessions/{cliente}/admin/warehouses/1/products",
            json={"nombre": "Leche", "precio": 100},
        )
        self.assertEqual(inventario.status_code, 403)

    def test_login_proveedor_inexistente(self) -> None:
        respuesta = self.cliente.post("/api/sessions/provider", json={"nombre": "Nadie"})
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["codigo"], "credenciales_invalidas")


if __name__ == "__main__":
    unittest.main()
