"""Normalización de texto para comparaciones tolerantes."""

from __future__ import annotations


def normalizar_texto(texto: object) -> str:
    """Devuelve texto en minúsculas, sin espacios sobrantes ni BOM."""
    limpio = str(texto or "").replace("\ufeff", "")
    return " ".join(limpio.strip().casefold().split())


__all__ = ["normalizar_texto"]
