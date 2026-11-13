"""Persistencia MongoDB de la aplicación."""

from .cliente import ClienteMongo
from .repositorio import RepositorioMongo

__all__ = ["ClienteMongo", "RepositorioMongo"]
