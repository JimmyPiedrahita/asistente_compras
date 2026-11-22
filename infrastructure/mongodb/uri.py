"""Fábrica de URIs de MongoDB por rol y por almacén.

Las URIs y contraseñas se construyen exclusivamente en el backend. Nunca se
serializan, registran ni envían al frontend.

En ``modo_pruebas`` todas las conexiones reutilizan ``MONGODB_URI``; los
repositorios siguen usando nombres de base distintos para que el aislamiento
lógico se pueda probar sin crear usuarios nativos.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import unicodedata
import uuid
from urllib.parse import quote_plus

from core.config import Settings
from models.almacenes import Almacen

_NOMBRE_BASE_VALIDO = re.compile(r"^[A-Za-z0-9_-]{1,63}$")
_USUARIO_VALIDO = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def _slug(nombre: str, *, maximo: int = 32) -> str:
    normalizado = unicodedata.normalize("NFKD", str(nombre or ""))
    ascii_texto = normalizado.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_texto.casefold()).strip("_")
    return slug[:maximo].strip("_") or "almacen"


class FabricaURIs:
    """Construye URIs por rol y deriva credenciales de almacén."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # Nombres y credenciales -------------------------------------------
    def nombre_base_almacen(self, nombre: str, almacen_id: str | None = None) -> str:
        sufijo = (almacen_id or uuid.uuid4().hex)[:6]
        base = f"{self.settings.mongodb_almacen_prefix}{_slug(nombre)}_{sufijo}"
        if not _NOMBRE_BASE_VALIDO.match(base):
            raise ValueError("El nombre de la base del almacén no es válido")
        return base

    def usuario_almacen(self, db_name: str) -> str:
        usuario = f"{db_name}_app"
        if not _USUARIO_VALIDO.match(usuario):
            raise ValueError("El usuario MongoDB del almacén no es válido")
        return usuario

    def password_almacen(self, almacen_id: str) -> str:
        secreto = self.settings.mongodb_warehouse_secret
        if not secreto:
            raise ValueError("Falta MONGODB_WAREHOUSE_SECRET para derivar la contraseña")
        digest = hmac.new(
            secreto.encode("utf-8"),
            str(almacen_id).encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    # URIs --------------------------------------------------------------
    def _uri(self, usuario: str, password: str, base_datos: str) -> str:
        if self.settings.modo_pruebas:
            return self.settings.mongodb_uri
        if not usuario or not password:
            raise ValueError("Faltan credenciales para construir la URI de MongoDB")
        if not _USUARIO_VALIDO.match(usuario):
            raise ValueError("El usuario MongoDB no es válido")
        host = self.settings.mongodb_host
        auth_source = quote_plus(self.settings.mongodb_auth_source)
        replica = quote_plus(self.settings.mongodb_replica_set)
        return (
            f"mongodb://{quote_plus(usuario)}:{quote_plus(password)}@{host}/"
            f"{base_datos}?authSource={auth_source}&replicaSet={replica}"
        )

    def uri_cliente(self) -> str:
        return self._uri(
            self.settings.mongo_cliente_user,
            self.settings.mongo_cliente_password,
            self.settings.mongodb_global_db,
        )

    def uri_admin_app(self) -> str:
        return self._uri(
            self.settings.mongo_admin_app_user,
            self.settings.mongo_admin_app_password,
            self.settings.mongodb_global_db,
        )

    def uri_auth(self) -> str:
        return self._uri(
            self.settings.mongo_auth_user,
            self.settings.mongo_auth_password,
            self.settings.mongodb_global_db,
        )

    def uri_validador(self) -> str:
        return self._uri(
            self.settings.mongo_validador_user,
            self.settings.mongo_validador_password,
            self.settings.mongodb_global_db,
        )

    def uri_catalogo(self, base_datos: str | None = None) -> str:
        return self._uri(
            self.settings.mongo_catalogo_user,
            self.settings.mongo_catalogo_password,
            base_datos or self.settings.mongodb_global_db,
        )

    def uri_compras(self, base_datos: str | None = None) -> str:
        return self._uri(
            self.settings.mongo_compras_user,
            self.settings.mongo_compras_password,
            base_datos or self.settings.mongodb_global_db,
        )

    def uri_provisioner(self) -> str:
        return self._uri(
            self.settings.mongo_provisioner_user,
            self.settings.mongo_provisioner_password,
            "admin",
        )

    def uri_almacen(self, almacen: Almacen) -> str:
        db_name = almacen.db_name or self.nombre_base_almacen(almacen.nombre, almacen.almacen_id)
        usuario = almacen.mongo_user or self.usuario_almacen(db_name)
        return self._uri(usuario, self.password_almacen(almacen.almacen_id), db_name)

    # Utilidades --------------------------------------------------------
    def base_datos_almacen(self, almacen: Almacen) -> str:
        return almacen.db_name or self.nombre_base_almacen(almacen.nombre, almacen.almacen_id)

    def __repr__(self) -> str:  # pragma: no cover - evita filtrar secretos
        return f"FabricaURIs(host={self.settings.mongodb_host!r})"


__all__ = ["FabricaURIs"]
