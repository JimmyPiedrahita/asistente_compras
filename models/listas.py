"""Estructuras de datos implementadas a mano.

``ListaSimple`` se usa para los inventarios y ``ListaDoblementeEnlazada`` para
la lista de compras y el carrito. Ambas mantienen un contador para que
``len()`` sea O(1).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


class NodoSimple:
    __slots__ = ("dato", "siguiente")

    def __init__(self, dato: Any) -> None:
        self.dato = dato
        self.siguiente: NodoSimple | None = None


class ListaSimple:
    """Lista simplemente enlazada con acceso por índice."""

    def __init__(self) -> None:
        self.cabeza: NodoSimple | None = None
        self.cola: NodoSimple | None = None
        self._tamano = 0

    def esta_vacia(self) -> bool:
        return self.cabeza is None

    def agregar(self, dato: Any) -> None:
        nuevo_nodo = NodoSimple(dato)
        if self.cabeza is None:
            self.cabeza = nuevo_nodo
            self.cola = nuevo_nodo
        elif self.cola is not None:
            self.cola.siguiente = nuevo_nodo
            self.cola = nuevo_nodo
        self._tamano += 1

    def obtener(self, indice: int) -> Any:
        indice = self._normalizar_indice(indice)
        actual = self.cabeza
        posicion = 0
        while actual is not None:
            if posicion == indice:
                return actual.dato
            actual = actual.siguiente
            posicion += 1
        raise IndexError(f"Índice fuera de rango: {indice}")

    def reemplazar(self, indice: int, dato: Any) -> bool:
        try:
            indice = self._normalizar_indice(indice)
        except IndexError:
            return False
        actual = self.cabeza
        posicion = 0
        while actual is not None:
            if posicion == indice:
                actual.dato = dato
                return True
            actual = actual.siguiente
            posicion += 1
        return False

    def mostrar(self) -> Iterator[Any]:
        actual = self.cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente

    def limpiar(self) -> None:
        self.cabeza = None
        self.cola = None
        self._tamano = 0

    def _normalizar_indice(self, indice: int) -> int:
        try:
            posicion = int(indice)
        except (TypeError, ValueError) as error:
            raise IndexError(f"Índice inválido: {indice}") from error
        if posicion < 0:
            posicion += self._tamano
        if posicion < 0 or posicion >= self._tamano:
            raise IndexError(f"Índice fuera de rango: {indice}")
        return posicion

    def __iter__(self) -> Iterator[Any]:
        return self.mostrar()

    def __len__(self) -> int:
        return self._tamano


class Nodo:
    __slots__ = ("anterior", "dato", "siguiente")

    def __init__(self, dato: Any) -> None:
        self.dato = dato
        self.siguiente: Nodo | None = None
        self.anterior: Nodo | None = None


class ListaDoblementeEnlazada:
    """Lista doblemente enlazada: lista de compras y carrito."""

    def __init__(self) -> None:
        self.cabeza: Nodo | None = None
        self.cola: Nodo | None = None
        self._tamano = 0

    def esta_vacia(self) -> bool:
        return self.cabeza is None

    def agregar_al_final(self, dato: Any) -> None:
        nuevo_nodo = Nodo(dato)
        if self.cabeza is None or self.cola is None:
            self.cabeza = self.cola = nuevo_nodo
        else:
            self.cola.siguiente = nuevo_nodo
            nuevo_nodo.anterior = self.cola
            self.cola = nuevo_nodo
        self._tamano += 1

    def agregar_al_inicio(self, dato: Any) -> None:
        nuevo_nodo = Nodo(dato)
        if self.cabeza is None or self.cola is None:
            self.cabeza = self.cola = nuevo_nodo
        else:
            nuevo_nodo.siguiente = self.cabeza
            self.cabeza.anterior = nuevo_nodo
            self.cabeza = nuevo_nodo
        self._tamano += 1

    def eliminar(self, dato: Any) -> bool:
        actual = self.cabeza
        while actual is not None:
            if actual.dato == dato:
                self._desenlazar(actual)
                return True
            actual = actual.siguiente
        return False

    def eliminar_en(self, indice: int) -> Any:
        posicion = self._normalizar_indice(indice)
        actual = self.cabeza
        for _ in range(posicion):
            if actual is None:
                break
            actual = actual.siguiente
        if actual is None:
            raise IndexError(f"Índice fuera de rango: {indice}")
        dato = actual.dato
        self._desenlazar(actual)
        return dato

    def obtener(self, indice: int) -> Any:
        posicion = self._normalizar_indice(indice)
        actual = self.cabeza
        for _ in range(posicion):
            if actual is None:
                break
            actual = actual.siguiente
        if actual is None:
            raise IndexError(f"Índice fuera de rango: {indice}")
        return actual.dato

    def mostrar(self) -> Iterator[Any]:
        actual = self.cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente

    def limpiar(self) -> None:
        self.cabeza = None
        self.cola = None
        self._tamano = 0

    def _desenlazar(self, nodo: Nodo) -> None:
        if nodo.anterior is not None:
            nodo.anterior.siguiente = nodo.siguiente
        else:
            self.cabeza = nodo.siguiente
        if nodo.siguiente is not None:
            nodo.siguiente.anterior = nodo.anterior
        else:
            self.cola = nodo.anterior
        self._tamano -= 1

    def _normalizar_indice(self, indice: int) -> int:
        try:
            posicion = int(indice)
        except (TypeError, ValueError) as error:
            raise IndexError(f"Índice inválido: {indice}") from error
        if posicion < 0:
            posicion += self._tamano
        if posicion < 0 or posicion >= self._tamano:
            raise IndexError(f"Índice fuera de rango: {indice}")
        return posicion

    def __iter__(self) -> Iterator[Any]:
        return self.mostrar()

    def __len__(self) -> int:
        return self._tamano


__all__ = [
    "ListaDoblementeEnlazada",
    "ListaSimple",
    "Nodo",
    "NodoSimple",
]
