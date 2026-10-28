"""Punto de entrada único para el servidor HTTP."""

from .app import create_app

app = create_app()
