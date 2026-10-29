"""Casos de uso de exportación a CSV."""

from __future__ import annotations

import csv
import io
from typing import Any

from core.errors import NoPermitido
from models.permisos import EXPORTAR

from .carrito import ControladorCarrito
from .contexto import ContextoSesion


class ControladorExportacion:
    def __init__(self, contexto: ContextoSesion, carrito: ControladorCarrito) -> None:
        self.contexto = contexto
        self.carrito = carrito

    def _verificar_permiso(self) -> None:
        if not self.contexto.autorizar(EXPORTAR):
            raise NoPermitido(EXPORTAR)

    def _filas_lista(self) -> list[dict[str, Any]]:
        with self.contexto.gestor_almacenes.candado:
            return self.contexto.gestor_almacenes.buscar_global(
                list(self.contexto.lista_compras.mostrar())
            )

    def exportar_lista_csv(self) -> tuple[str, int]:
        self._verificar_permiso()
        filas = self._filas_lista()
        salida = io.StringIO(newline="")
        escritor = csv.writer(salida)
        escritor.writerow(["producto", "marca", "precio_final", "almacen"])
        for fila in filas:
            escritor.writerow(
                [
                    fila["nombre"],
                    fila["producto"].marca,
                    f"{fila['precio']:.2f}",
                    fila["almacen"].nombre,
                ]
            )
        return salida.getvalue(), len(filas)

    def exportar_carrito_csv(self) -> tuple[str, int]:
        self._verificar_permiso()
        resumen = self.carrito.resumen()
        salida = io.StringIO(newline="")
        escritor = csv.writer(salida)
        escritor.writerow(["producto", "marca", "precio_final"])
        for producto in resumen["productos"]:
            escritor.writerow(
                [
                    producto.nombre,
                    producto.marca,
                    f"{producto.obtener_precio_final():.2f}",
                ]
            )
        escritor.writerow([])
        escritor.writerow(["subtotal", f"{resumen['subtotal']:.2f}"])
        escritor.writerow(["descuento", resumen["descuento"]])
        escritor.writerow(["total", f"{resumen['total']:.2f}"])
        return salida.getvalue(), len(resumen["productos"])

    def exportar_lista(self, ruta: str) -> dict[str, Any]:
        try:
            contenido, filas = self.exportar_lista_csv()
        except NoPermitido:
            return {"ok": False, "filas": 0}
        return self._escribir(ruta, contenido, filas, "Lista exportada")

    def exportar_carrito(self, ruta: str) -> dict[str, Any]:
        try:
            contenido, filas = self.exportar_carrito_csv()
        except NoPermitido:
            return {"ok": False, "filas": 0}
        return self._escribir(ruta, contenido, filas, "Carrito exportado")

    def _escribir(self, ruta: str, contenido: str, filas: int, mensaje: str) -> dict[str, Any]:
        try:
            with open(ruta, "w", newline="", encoding="utf-8") as archivo:
                archivo.write(contenido)
        except OSError as error:
            self.contexto.registrar("ERROR", "No se pudo exportar", str(error))
            return {"ok": False, "filas": 0}
        self.contexto.registrar("CLIENTE", mensaje, f"{filas} filas -> {ruta}")
        return {"ok": True, "filas": filas}

    @staticmethod
    def nombre_archivo(prefix: str) -> str:
        return f"{prefix}.csv"


__all__ = ["ControladorExportacion"]
