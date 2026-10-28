"""Patrón Observer reutilizable.

El carrito notifica a sus observadores en cada cambio. En la API el observador
es una implementación nula; en las pruebas y en una futura interfaz gráfica
puede ser un objeto que registre o muestre los cambios.
"""

from __future__ import annotations

from typing import Any, Protocol


class Observador(Protocol):
    def actualizar(self, sujeto: Any, mensaje: str) -> None: ...

    def notificar_denegado(self, permiso: str) -> None: ...


class ObservadorNulo:
    """Observador sin efectos, útil para la API y los casos sin interfaz."""

    def actualizar(self, sujeto: Any, mensaje: str) -> None:
        return None

    def notificar_denegado(self, permiso: str) -> None:
        return None


class SujetoObservable:
    """Mantiene observadores y los notifica cuando cambia el estado."""

    def __init__(self) -> None:
        self._observadores: list[Observador] = []

    def agregar_observador(self, observador: Observador) -> None:
        if observador not in self._observadores:
            self._observadores.append(observador)

    def remover_observador(self, observador: Observador) -> None:
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar_observadores(self, mensaje: str = "") -> None:
        for observador in list(self._observadores):
            observador.actualizar(self, mensaje)


__all__ = ["Observador", "ObservadorNulo", "SujetoObservable"]
