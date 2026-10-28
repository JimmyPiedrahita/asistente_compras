"""Resultado tipado de los casos de uso.

Hereda de ``str`` para mantener compatibilidad con la API anterior, que
comparaba los resultados con cadenas como ``"ok"`` o ``"denegado"``.
Además, ``bool(Resultado.OK)`` es ``True`` y cualquier otro resultado es
``False``, lo que conserva el comportamiento de los métodos que antes
devolvían ``bool``.
"""

from __future__ import annotations

from enum import Enum


class Resultado(str, Enum):
    OK = "ok"
    VACIO = "vacio"
    DENEGADO = "denegado"
    DUPLICADO = "duplicado"
    NO_ENCONTRADO = "no_encontrado"
    INVALIDO = "invalido"
    CONFLICTO = "conflicto"
    ERROR = "error"

    def __bool__(self) -> bool:
        return self is Resultado.OK

    def __str__(self) -> str:
        return self.value
