"""Fachada de casos de uso compatible con la API anterior.

Cada sesión HTTP tiene una instancia de ``ControladorCompras``. La fachada
delega en controladores pequeños para que la lógica no quede concentrada en
una sola clase.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from core.config import Settings
from core.logging import obtener_logger
from core.observer import Observador, ObservadorNulo
from models.almacenes import GestorAlmacenes
from models.carrito import CarritoCompras
from models.listas import ListaDoblementeEnlazada

from .busqueda import ControladorBusqueda
from .carrito import ControladorCarrito
from .contexto import ContextoSesion
from .exportacion import ControladorExportacion
from .inventario import ControladorInventario
from .lista_compra import ControladorListaCompra
from .sesion import ControladorSesion


class ControladorCompras:
    def __init__(
        self,
        carrito: CarritoCompras | None = None,
        vista: Observador | None = None,
        gestor_almacenes: GestorAlmacenes | None = None,
        *,
        clave_admin: str | None = None,
        settings: Settings | None = None,
        max_csv_bytes: int | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if settings is not None:
            clave_admin = settings.admin_clave if clave_admin is None else clave_admin
            if max_csv_bytes is None:
                max_csv_bytes = settings.max_csv_bytes
        self._clave_admin = clave_admin if clave_admin is not None else os.getenv("ADMIN_CLAVE", "")

        self.vista = vista or ObservadorNulo()
        self.carrito = carrito or CarritoCompras()
        self.gestor_almacenes = gestor_almacenes or GestorAlmacenes()
        self.lista_compras = ListaDoblementeEnlazada()
        self.logger = logger or obtener_logger("asistente_compras.compras")

        self.sesion = ControladorSesion(self._clave_admin)
        self.contexto = ContextoSesion(
            sesion=self.sesion,
            carrito=self.carrito,
            lista_compras=self.lista_compras,
            gestor_almacenes=self.gestor_almacenes,
            vista=self.vista,
            logger=self.logger,
        )
        self.lista_compra = ControladorListaCompra(self.contexto)
        self.busqueda = ControladorBusqueda(self.contexto)
        self.carrito_controller = ControladorCarrito(self.contexto)
        self.inventario = ControladorInventario(
            self.contexto, max_csv_bytes=max_csv_bytes or 1_000_000
        )
        self.exportacion = ControladorExportacion(self.contexto, self.carrito_controller)

        self.carrito.agregar_observador(self.vista)

    # Sesión y permisos -------------------------------------------------

    def _autorizar(self, permiso: str) -> bool:
        return self.contexto.autorizar(permiso)

    def registrar_usuario(self, nombre: str) -> bool:
        return self.sesion.registrar_usuario(nombre)

    def iniciar_sesion(self, nombre: str) -> bool:
        return self.sesion.iniciar_sesion(nombre)

    def cerrar_sesion(self) -> None:
        self.sesion.cerrar_sesion()
        self.carrito_controller.limpiar_descuento()

    def obtener_usuario_actual(self) -> str | None:
        return self.sesion.usuario_actual

    def obtener_rol(self) -> str:
        return self.sesion.rol

    def login_admin(self, clave: str) -> bool:
        return self.sesion.login_admin(clave)

    # Lista de compras --------------------------------------------------

    def agregar_producto_usuario(self, nombre: str):
        return self.lista_compra.agregar(nombre)

    def eliminar_producto_usuario(self, nombre: str):
        return self.lista_compra.eliminar(nombre)

    def obtener_compras_usuario(self) -> list[str]:
        return self.lista_compra.obtener()

    # Búsquedas ---------------------------------------------------------

    def ejecutar_busqueda_precios(self) -> Any:
        return self.busqueda.mejor_precio_por_almacen()

    def ejecutar_catalogo(self) -> Any:
        return self.busqueda.catalogo_completo()

    def ejecutar_comparacion_global(self) -> list[dict[str, Any]]:
        return self.busqueda.mejor_precio_global()

    # Carrito -----------------------------------------------------------

    def agregar_producto_carrito(self, producto: Any):
        return self.carrito_controller.agregar_producto(producto)

    def agregar_seleccion_al_carrito(self, producto: Any, id_almacen: int):
        return self.carrito_controller.agregar_seleccion(producto, id_almacen)

    def agregar_producto_carrito_por_id(self, id_almacen: int, producto_id: str):
        return self.carrito_controller.agregar_por_id(id_almacen, producto_id)

    def quitar_producto_carrito(self, indice: int):
        return self.carrito_controller.quitar(indice)

    def vaciar_carrito(self):
        return self.carrito_controller.vaciar()

    def establecer_descuento(self, opcion: str, valor: Any = None):
        return self.carrito_controller.establecer_descuento(opcion, valor)

    def obtener_resumen_carrito(self) -> dict[str, Any]:
        return self.carrito_controller.resumen()

    @property
    def descuento_actual(self) -> str:
        return self.carrito_controller.descuento_actual

    # Inventario --------------------------------------------------------

    def agregar_producto_almacen(
        self,
        id_almacen: int,
        nombre: str,
        precio: float,
        marca: str = "Generica",
        categoria: str = "General",
        tipo: str = "normal",
        **extra: Any,
    ):
        return self.inventario.agregar_producto(
            id_almacen, nombre, precio, marca, categoria, tipo, **extra
        )

    def editar_precio(self, id_almacen: int, indice: int, nuevo_precio: float):
        return self.inventario.editar_precio(id_almacen, indice, nuevo_precio)

    def editar_precio_por_id(self, id_almacen: int, producto_id: str, nuevo_precio: float):
        return self.inventario.editar_precio_por_id(id_almacen, producto_id, nuevo_precio)

    def cargar_csv(self, ruta: str) -> dict[str, Any]:
        return self.inventario.cargar_csv(ruta)

    def cargar_csv_contenido(self, contenido: str) -> dict[str, Any]:
        return self.inventario.cargar_csv_contenido(contenido)

    def listar_productos(self, id_almacen: int) -> list[Any]:
        return self.inventario.listar_productos(id_almacen)

    def recargar_inventarios(self):
        return self.inventario.recargar_inventarios()

    # Exportación -------------------------------------------------------

    def exportar_lista(self, ruta: str) -> dict[str, Any]:
        return self.exportacion.exportar_lista(ruta)

    def exportar_carrito(self, ruta: str) -> dict[str, Any]:
        return self.exportacion.exportar_carrito(ruta)

    def exportar_lista_csv(self) -> str:
        return self.exportacion.exportar_lista_csv()[0]

    def exportar_carrito_csv(self) -> str:
        return self.exportacion.exportar_carrito_csv()[0]


__all__ = ["ControladorCompras"]
