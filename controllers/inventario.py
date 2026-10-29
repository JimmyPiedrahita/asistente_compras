"""Casos de uso administrativos de inventario."""

from __future__ import annotations

import csv
import io
import math
from typing import Any

from core.errors import (
    Conflicto,
    NoEncontrado,
    NoPermitido,
    ServicioNoDisponible,
    SolicitudInvalida,
)
from core.results import Resultado
from models.permisos import CARGAR_CSV, EDITAR_PRECIO, GESTIONAR_ALMACENES
from models.productos import FabricaProductos, Producto
from models.texto import normalizar_texto

from .contexto import ContextoSesion


class ControladorInventario:
    def __init__(self, contexto: ContextoSesion, max_csv_bytes: int = 1_000_000) -> None:
        self.contexto = contexto
        self.max_csv_bytes = max_csv_bytes

    def agregar_producto(
        self,
        id_almacen: int,
        nombre: str,
        precio: float,
        marca: str = "Generica",
        categoria: str = "General",
        tipo: str = "normal",
        **extra: Any,
    ) -> Resultado:
        if not self.contexto.autorizar(GESTIONAR_ALMACENES):
            return Resultado.DENEGADO
        try:
            producto = FabricaProductos.crear_producto(
                tipo, nombre, precio, marca=marca, categoria=categoria, **extra
            )
        except (ValueError, TypeError) as error:
            self.contexto.registrar("ADMIN", "Producto rechazado", str(error))
            return Resultado.INVALIDO

        try:
            agregado = self.contexto.gestor_almacenes.agregar_producto(id_almacen, producto)
        except NoEncontrado:
            return Resultado.NO_ENCONTRADO
        except Conflicto:
            return Resultado.CONFLICTO
        if not agregado:
            return Resultado.NO_ENCONTRADO

        self.contexto.registrar(
            "ADMIN", "Producto en inventario", f"{producto} -> Almacen {id_almacen}"
        )
        return Resultado.OK

    def editar_precio(self, id_almacen: int, indice: int, nuevo_precio: float) -> Resultado:
        if not self.contexto.autorizar(EDITAR_PRECIO):
            return Resultado.DENEGADO
        producto = self.contexto.gestor_almacenes.producto_en_indice(id_almacen, indice)
        if producto is None:
            return Resultado.NO_ENCONTRADO
        return self._aplicar_precio(id_almacen, producto, nuevo_precio)

    def editar_precio_por_id(
        self, id_almacen: int, producto_id: str, nuevo_precio: float
    ) -> Resultado:
        if not self.contexto.autorizar(EDITAR_PRECIO):
            return Resultado.DENEGADO
        producto = self.contexto.gestor_almacenes.obtener_producto(id_almacen, producto_id)
        if producto is None:
            return Resultado.NO_ENCONTRADO
        return self._aplicar_precio(id_almacen, producto, nuevo_precio)

    def _aplicar_precio(
        self, id_almacen: int, producto: Producto, nuevo_precio: float
    ) -> Resultado:
        try:
            precio = float(nuevo_precio)
        except (TypeError, ValueError, OverflowError):
            return Resultado.INVALIDO
        if not math.isfinite(precio) or precio < 0:
            return Resultado.INVALIDO

        anterior = producto.precio
        producto.precio = precio
        try:
            actualizado = self.contexto.gestor_almacenes.actualizar_producto(id_almacen, producto)
        except NoEncontrado:
            producto.precio = anterior
            return Resultado.NO_ENCONTRADO
        except ServicioNoDisponible:
            producto.precio = anterior
            raise
        except Exception:
            producto.precio = anterior
            self.contexto.registrar(
                "ERROR", "Precio no actualizado", "No se pudo persistir en MongoDB"
            )
            return Resultado.ERROR
        if not actualizado:
            producto.precio = anterior
            return Resultado.NO_ENCONTRADO

        self.contexto.registrar(
            "ADMIN",
            "Precio actualizado",
            f"{producto.nombre}: ${anterior:.2f} -> ${precio:.2f}",
        )
        return Resultado.OK

    def cargar_csv(self, ruta: str) -> dict[str, Any]:
        """Compatibilidad: lee un archivo y delega en el parser en memoria."""
        try:
            with open(ruta, encoding="utf-8-sig") as archivo:
                contenido = archivo.read()
        except OSError as error:
            return {
                "importados": 0,
                "rechazados": 0,
                "errores": [f"No se pudo abrir el archivo: {error}"],
            }
        try:
            return self.cargar_csv_contenido(contenido)
        except NoPermitido:
            return {
                "importados": 0,
                "rechazados": 0,
                "errores": ["Permiso denegado para cargar_csv"],
            }
        except SolicitudInvalida as error:
            return {"importados": 0, "rechazados": 0, "errores": [error.mensaje]}

    def cargar_csv_contenido(self, contenido: str) -> dict[str, Any]:
        if not self.contexto.autorizar(CARGAR_CSV):
            raise NoPermitido(CARGAR_CSV)
        if not isinstance(contenido, str) or not contenido.strip():
            raise SolicitudInvalida("El CSV está vacío")
        if len(contenido.encode("utf-8")) > self.max_csv_bytes:
            raise SolicitudInvalida(f"El CSV supera el tamaño máximo de {self.max_csv_bytes} bytes")

        resultado: dict[str, Any] = {
            "importados": 0,
            "rechazados": 0,
            "errores": [],
        }
        lector = csv.DictReader(io.StringIO(contenido))
        columnas = {normalizar_texto(columna) for columna in (lector.fieldnames or [])}
        requeridas = {"almacen", "nombre", "precio"}
        if not requeridas.issubset(columnas):
            raise SolicitudInvalida("Cabecera inválida: se requieren almacen, nombre y precio")

        claves_vistas: set[tuple[int, str, str]] = set()
        for numero, fila in enumerate(lector, start=2):
            try:
                datos = {
                    normalizar_texto(clave): str(valor or "").strip()
                    for clave, valor in fila.items()
                    if clave is not None
                }
                id_almacen = int(datos.get("almacen", ""))
                nombre = datos.get("nombre", "")
                precio = float(datos.get("precio", ""))
                marca = datos.get("marca") or "Generica"
                categoria = datos.get("categoria") or "General"
                tipo = datos.get("tipo") or "normal"
                extra = datos.get("extra") or ""

                kwargs: dict[str, Any] = {}
                if normalizar_texto(tipo) == "fisico":
                    kwargs["costo_envio"] = float(extra) if extra else 5.0
                elif normalizar_texto(tipo) == "suscripcion":
                    kwargs["meses"] = int(extra) if extra else 1

                producto = FabricaProductos.crear_producto(
                    tipo, nombre, precio, marca=marca, categoria=categoria, **kwargs
                )
                almacen = self.contexto.gestor_almacenes.obtener_almacen(id_almacen)
                if almacen is None:
                    raise ValueError(f"almacén {id_almacen} inexistente")

                clave = (
                    id_almacen,
                    normalizar_texto(nombre),
                    normalizar_texto(marca),
                )
                if clave in claves_vistas or self.contexto.gestor_almacenes.existe_nombre_marca(
                    id_almacen, nombre, marca
                ):
                    raise ValueError("producto duplicado en el almacén")

                if not self.contexto.gestor_almacenes.agregar_producto(id_almacen, producto):
                    raise ValueError(f"almacén {id_almacen} inexistente")
                claves_vistas.add(clave)
                resultado["importados"] += 1
            except (ValueError, TypeError) as error:
                resultado["rechazados"] += 1
                resultado["errores"].append(f"Línea {numero}: {error}")

        self.contexto.registrar(
            "ADMIN",
            "Carga CSV finalizada",
            f"{resultado['importados']} importados, {resultado['rechazados']} rechazados",
        )
        return resultado

    def listar_productos(
        self, id_almacen: int, limit: int = 100, offset: int = 0
    ) -> list[Producto]:
        productos, _ = self.listar_productos_paginados(id_almacen, limit, offset)
        return productos

    def listar_productos_paginados(
        self, id_almacen: int, limit: int = 100, offset: int = 0
    ) -> tuple[list[Producto], int]:
        almacen = self.contexto.gestor_almacenes.obtener_almacen(id_almacen)
        if almacen is None:
            raise NoEncontrado(f"Almacén no encontrado: {id_almacen}")
        return self.contexto.gestor_almacenes.listar_productos(id_almacen, limit, offset)

    def eliminar_producto(self, id_almacen: int, producto_id: str) -> Resultado:
        if not self.contexto.autorizar(GESTIONAR_ALMACENES):
            return Resultado.DENEGADO
        try:
            eliminado = self.contexto.gestor_almacenes.eliminar_producto(id_almacen, producto_id)
        except NoEncontrado:
            return Resultado.NO_ENCONTRADO
        if not eliminado:
            return Resultado.NO_ENCONTRADO
        self.contexto.registrar(
            "ADMIN", "Producto eliminado", f"{producto_id} -> Almacen {id_almacen}"
        )
        return Resultado.OK

    def estado_comparador(self) -> dict[str, Any]:
        if not self.contexto.autorizar(GESTIONAR_ALMACENES):
            raise NoPermitido(GESTIONAR_ALMACENES)
        return self.contexto.gestor_almacenes.estado_comparador()

    def recargar_inventarios(self) -> Resultado:
        """Reconstruye la proyección integrada desde las bases fuente."""
        if not self.contexto.autorizar(GESTIONAR_ALMACENES):
            return Resultado.DENEGADO
        resultado = self.contexto.gestor_almacenes.reconciliar_comparador()
        self.contexto.registrar(
            "ADMIN",
            "Comparador reconstruido desde MongoDB",
            f"{resultado.get('reconciliados', 0)} productos",
        )
        return Resultado.OK


__all__ = ["ControladorInventario"]
