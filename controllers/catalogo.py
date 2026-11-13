"""Lista de compras y búsqueda comparativa entre almacenes."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from core.errors import SolicitudInvalida
from infrastructure.mongodb.repositorio import RepositorioMongo
from models.productos import Producto
from models.texto import normalizar_texto

from .sesiones import Sesion

MODOS = {"catalogo", "mejor_precio", "global"}


class ControladorCatalogo:
    def __init__(self, repositorio: RepositorioMongo) -> None:
        self.repo = repositorio

    # Lista de compras --------------------------------------------------
    def agregar_a_lista(self, sesion: Sesion, nombre: str) -> list[str]:
        limpio = " ".join(str(nombre or "").split())
        if not limpio:
            raise SolicitudInvalida("Escribe un producto para agregar a la lista")
        if any(normalizar_texto(item) == normalizar_texto(limpio) for item in sesion.lista):
            raise SolicitudInvalida("Ese producto ya está en tu lista de compras")
        sesion.lista.append(limpio)
        return list(sesion.lista)

    def quitar_de_lista(self, sesion: Sesion, nombre: str) -> list[str]:
        buscado = normalizar_texto(nombre)
        antes = len(sesion.lista)
        sesion.lista = [item for item in sesion.lista if normalizar_texto(item) != buscado]
        if len(sesion.lista) == antes:
            raise SolicitudInvalida("El producto no está en tu lista de compras")
        return list(sesion.lista)

    # Búsqueda ----------------------------------------------------------
    def buscar(self, sesion: Sesion, modo: str) -> dict[str, Any]:
        modo = str(modo or "catalogo").strip().lower()
        if modo not in MODOS:
            raise SolicitudInvalida("Modo de búsqueda inválido")
        if not sesion.lista:
            raise SolicitudInvalida("Tu lista de compras está vacía")

        hay_productos = self.repo.contar_productos() > 0
        candidatos = self.repo.buscar_por_tipos(sesion.lista)
        grupos: list[dict[str, Any]] = []
        encontrados = 0

        for termino in sesion.lista:
            normalizado = normalizar_texto(termino)
            del_termino = [
                (producto, almacen)
                for producto, almacen in candidatos
                if producto.tipo_normalizado == normalizado
            ]
            if modo == "mejor_precio":
                seleccion = self._mejor_por_almacen(del_termino)
            elif modo == "global":
                seleccion = self._mejor_global(del_termino)
            else:
                seleccion = sorted(
                    del_termino,
                    key=lambda fila: (
                        normalizar_texto(fila[1].nombre),
                        normalizar_texto(fila[0].nombre),
                        fila[0].precio,
                        fila[0].producto_id,
                    ),
                )
            encontrados += len(seleccion)
            grupos.append(
                {
                    "producto_buscado": termino,
                    "tipo_producto": normalizado,
                    "resultados": [
                        {
                            "almacen_id": almacen.almacen_id,
                            "almacen": almacen.nombre,
                            "producto": producto.publico(),
                        }
                        for producto, almacen in seleccion
                    ],
                    "sin_resultados": not seleccion,
                }
            )

        return {
            "modo": modo,
            "hay_productos": hay_productos,
            "grupos": grupos,
            "total_resultados": encontrados,
        }

    @staticmethod
    def _mejor_por_almacen(filas: list[tuple[Producto, Any]]) -> list[tuple[Producto, Any]]:
        por_almacen: dict[str, list[tuple[Producto, Any]]] = defaultdict(list)
        for producto, almacen in filas:
            por_almacen[almacen.almacen_id].append((producto, almacen))
        seleccion: list[tuple[Producto, Any]] = []
        for grupo in por_almacen.values():
            grupo.sort(
                key=lambda fila: (
                    fila[0].precio,
                    normalizar_texto(fila[0].nombre),
                    fila[0].producto_id,
                )
            )
            seleccion.append(grupo[0])
        seleccion.sort(key=lambda fila: normalizar_texto(fila[1].nombre))
        return seleccion

    @staticmethod
    def _mejor_global(filas: list[tuple[Producto, Any]]) -> list[tuple[Producto, Any]]:
        if not filas:
            return []
        ordenadas = sorted(
            filas,
            key=lambda fila: (
                fila[0].precio,
                normalizar_texto(fila[1].nombre),
                normalizar_texto(fila[0].nombre),
                fila[0].producto_id,
            ),
        )
        return [ordenadas[0]]


__all__ = ["ControladorCatalogo"]
