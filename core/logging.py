"""Configuración central de logging."""

from __future__ import annotations

import logging

FORMATO = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
FECHA = "%H:%M:%S"

_configurado = False


def configurar_logging(nivel: str = "INFO") -> None:
    global _configurado
    nivel_num = getattr(logging, str(nivel).upper(), logging.INFO)
    if not _configurado:
        logging.basicConfig(level=nivel_num, format=FORMATO, datefmt=FECHA)
        _configurado = True
    logging.getLogger("asistente_compras").setLevel(nivel_num)


def obtener_logger(nombre: str = "asistente_compras") -> logging.Logger:
    return logging.getLogger(nombre)


logger = obtener_logger()


__all__ = ["configurar_logging", "logger", "obtener_logger"]
