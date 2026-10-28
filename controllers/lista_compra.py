"""Caso de uso de lista de compras."""

from __future__ import annotations

from core.results import Resultado
from models.permisos import CREAR_LISTA, ELIMINAR_PRODUCTO
from models.texto import normalizar_texto

from .contexto import ContextoSesion


class ControladorListaCompra:
    def __init__(self, contexto: ContextoSesion) -> None:
        self.contexto = contexto
        self._normalizados = {
            normalizar_texto(nombre) for nombre in contexto.lista_compras.mostrar()
        }

    def agregar(self, nombre: str) -> Resultado:
        nombre = (nombre or "").strip()
        if not nombre:
            return Resultado.VACIO
        if not self.contexto.autorizar(CREAR_LISTA):
            return Resultado.DENEGADO

        clave = normalizar_texto(nombre)
        if clave in self._normalizados:
            self.contexto.registrar("CLIENTE", "Producto duplicado en la lista", nombre)
            return Resultado.DUPLICADO

        self.contexto.lista_compras.agregar_al_final(nombre)
        self._normalizados.add(clave)
        self.contexto.registrar("CLIENTE", "Producto agregado a la lista", nombre)
        return Resultado.OK

    def eliminar(self, nombre: str) -> Resultado:
        nombre = (nombre or "").strip()
        if not nombre:
            return Resultado.VACIO
        if not self.contexto.autorizar(ELIMINAR_PRODUCTO):
            return Resultado.DENEGADO

        clave = normalizar_texto(nombre)
        for existente in list(self.contexto.lista_compras.mostrar()):
            if normalizar_texto(existente) == clave:
                self.contexto.lista_compras.eliminar(existente)
                self._normalizados.discard(clave)
                self.contexto.registrar("CLIENTE", "Producto eliminado de la lista", existente)
                return Resultado.OK
        return Resultado.NO_ENCONTRADO

    def obtener(self) -> list[str]:
        return list(self.contexto.lista_compras.mostrar())


__all__ = ["ControladorListaCompra"]
