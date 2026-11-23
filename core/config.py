"""Configuración de la aplicación leída desde variables de entorno.

La aplicación usa una base global y una base por almacén. Las conexiones se
construyen a partir de credenciales de servicio independientes; la API nunca
expone estas credenciales.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email

from .errors import ConfiguracionInvalida

_NOMBRE_BASE_VALIDO = re.compile(r"^[A-Za-z0-9_-]+$")
_PREFIJO_VALIDO = re.compile(r"^[A-Za-z0-9_]+$")
_USUARIO_MONGO_VALIDO = re.compile(r"^[A-Za-z0-9_.-]+$")

_SECRETO_PRUEBAS = "pruebas-" + "x" * 40
_PASSWORD_PRUEBAS = "pruebas"


def _email_valido(email: str) -> bool:
    try:
        validate_email(str(email or "").strip(), check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def _leer_int(
    entorno: Mapping[str, str],
    clave: str,
    defecto: int,
    *,
    minimo: int = 1,
) -> int:
    valor = entorno.get(clave)
    if valor is None or str(valor).strip() == "":
        return defecto
    try:
        numero = int(str(valor).strip())
    except ValueError as error:
        raise ConfiguracionInvalida(f"{clave} debe ser un número entero") from error
    if numero < minimo:
        raise ConfiguracionInvalida(f"{clave} debe ser mayor o igual a {minimo}")
    return numero


def _texto(entorno: Mapping[str, str], clave: str, defecto: str = "") -> str:
    return str(entorno.get(clave, defecto) or "").strip()


def _bool(entorno: Mapping[str, str], clave: str) -> bool:
    return _texto(entorno, clave).lower() in {"1", "true", "si", "sí", "yes", "on"}


def _bool_estricto(entorno: Mapping[str, str], clave: str, defecto: bool) -> bool:
    valor = _texto(entorno, clave).lower()
    if not valor:
        return defecto
    if valor in {"1", "true", "si", "sí", "yes", "on"}:
        return True
    if valor in {"0", "false", "no", "off"}:
        return False
    raise ConfiguracionInvalida(f"{clave} debe ser true o false")


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de la aplicación."""

    # Modo de pruebas: un único URI para todas las conexiones. No se usa en
    # producción; permite ejecutar pruebas de integración sin crear usuarios
    # nativos de MongoDB.
    modo_pruebas: bool = False

    # URI único de pruebas/scripts. La API en producción no lo usa.
    mongodb_uri: str = ""
    mongodb_db: str = "asistente_compras"

    # Conexiones por rol.
    mongodb_host: str = "mongodb:27017"
    mongodb_replica_set: str = "rs0"
    mongodb_auth_source: str = "admin"
    mongodb_global_db: str = "global_asistente_compras"
    mongodb_almacen_prefix: str = "almacen_"
    mongodb_warehouse_secret: str = ""

    mongo_cliente_user: str = "cliente_app"
    mongo_cliente_password: str = ""
    mongo_admin_app_user: str = "admin_app"
    mongo_admin_app_password: str = ""
    mongo_auth_user: str = "auth_service"
    mongo_auth_password: str = ""
    mongo_validador_user: str = "validador_catalogo"
    mongo_validador_password: str = ""
    mongo_catalogo_user: str = "replicador_catalogo"
    mongo_catalogo_password: str = ""
    mongo_compras_user: str = "proyector_compras"
    mongo_compras_password: str = ""
    mongo_provisioner_user: str = "provisioner"
    mongo_provisioner_password: str = ""

    # Aplicación.
    admin_email: str = ""
    admin_password: str = ""
    admin_nombre: str = "Administrador de la aplicación"
    mongodb_timeout_ms: int = 5000
    listener_refresh_seconds: int = 15
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://localhost:5173")
    session_ttl_seconds: int = 3600
    max_sessions: int = 1000
    max_csv_bytes: int = 1_000_000
    max_product_image_bytes: int = 2_000_000
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder: str = "asistente-compras"
    payments_provider: str = ""
    payments_sandbox: bool = True
    wompi_public_key: str = ""
    wompi_private_key: str = ""
    wompi_integrity_secret: str = ""
    wompi_events_secret: str = ""
    wompi_redirect_url: str = "http://localhost:3000/pago/{reference}"
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if self.modo_pruebas:
            if not self.mongodb_uri or not self.mongodb_uri.strip():
                raise ConfiguracionInvalida("MONGODB_URI es obligatoria en modo de pruebas")
        else:
            if not self.mongodb_host or not self.mongodb_host.strip():
                raise ConfiguracionInvalida("MONGODB_HOST es obligatoria")
            if not self.mongodb_warehouse_secret or len(self.mongodb_warehouse_secret) < 32:
                raise ConfiguracionInvalida(
                    "MONGODB_WAREHOUSE_SECRET debe tener al menos 32 caracteres"
                )
            credenciales = (
                ("MONGO_CLIENTE", self.mongo_cliente_password),
                ("MONGO_ADMIN_APP", self.mongo_admin_app_password),
                ("MONGO_AUTH", self.mongo_auth_password),
                ("MONGO_VALIDADOR", self.mongo_validador_password),
                ("MONGO_CATALOGO", self.mongo_catalogo_password),
                ("MONGO_COMPRAS", self.mongo_compras_password),
                ("MONGO_PROVISIONER", self.mongo_provisioner_password),
            )
            faltantes = [nombre for nombre, valor in credenciales if not valor]
            if faltantes:
                raise ConfiguracionInvalida(
                    "Faltan contraseñas de servicio: " + ", ".join(faltantes)
                )

        if not _NOMBRE_BASE_VALIDO.match(self.mongodb_db):
            raise ConfiguracionInvalida(
                "MONGODB_DB solo admite letras, números, guion y guion bajo"
            )
        if not _NOMBRE_BASE_VALIDO.match(self.mongodb_global_db):
            raise ConfiguracionInvalida(
                "MONGODB_GLOBAL_DB solo admite letras, números, guion y guion bajo"
            )
        if not _PREFIJO_VALIDO.match(self.mongodb_almacen_prefix):
            raise ConfiguracionInvalida(
                "MONGODB_ALMACEN_PREFIX solo admite letras, números y guion bajo"
            )
        for nombre, usuario in (
            ("MONGO_CLIENTE_USER", self.mongo_cliente_user),
            ("MONGO_ADMIN_APP_USER", self.mongo_admin_app_user),
            ("MONGO_AUTH_USER", self.mongo_auth_user),
            ("MONGO_VALIDADOR_USER", self.mongo_validador_user),
            ("MONGO_CATALOGO_USER", self.mongo_catalogo_user),
            ("MONGO_COMPRAS_USER", self.mongo_compras_user),
            ("MONGO_PROVISIONER_USER", self.mongo_provisioner_user),
        ):
            if not _USUARIO_MONGO_VALIDO.match(usuario):
                raise ConfiguracionInvalida(f"{nombre} no es un usuario MongoDB válido")
        if not self.admin_email or not _email_valido(self.admin_email):
            raise ConfiguracionInvalida("ADMIN_EMAIL es obligatoria y debe ser un correo válido")
        if not self.admin_password or len(self.admin_password) < 8:
            raise ConfiguracionInvalida("ADMIN_PASSWORD debe tener al menos 8 caracteres")
        if self.mongodb_timeout_ms < 100:
            raise ConfiguracionInvalida("MONGODB_TIMEOUT_MS debe ser al menos 100")
        if self.listener_refresh_seconds < 1:
            raise ConfiguracionInvalida("LISTENER_REFRESH_SECONDS debe ser positivo")
        if self.session_ttl_seconds < 1:
            raise ConfiguracionInvalida("SESSION_TTL_SECONDS debe ser positivo")
        if self.max_sessions < 1:
            raise ConfiguracionInvalida("MAX_SESSIONS debe ser positivo")
        if self.max_csv_bytes < 1:
            raise ConfiguracionInvalida("MAX_CSV_BYTES debe ser positivo")
        if self.max_product_image_bytes < 1:
            raise ConfiguracionInvalida("MAX_PRODUCT_IMAGE_BYTES debe ser positivo")
        if not self.cloudinary_folder.strip():
            raise ConfiguracionInvalida("CLOUDINARY_FOLDER no puede estar vacío")
        credenciales_cloudinary = (
            self.cloudinary_cloud_name,
            self.cloudinary_api_key,
            self.cloudinary_api_secret,
        )
        if any(credenciales_cloudinary) and not all(credenciales_cloudinary):
            raise ConfiguracionInvalida(
                "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY y CLOUDINARY_API_SECRET "
                "deben configurarse juntas"
            )
        wompi_keys = (
            self.wompi_public_key,
            self.wompi_integrity_secret,
            self.wompi_events_secret,
        )
        if any(wompi_keys) and not all(wompi_keys):
            raise ConfiguracionInvalida(
                "WOMPI_PUBLIC_KEY, WOMPI_INTEGRITY_SECRET y WOMPI_EVENTS_SECRET "
                "deben configurarse juntas"
            )
        proveedor_pagos = str(self.payments_provider or "").strip().lower()
        if proveedor_pagos not in {"", "auto", "wompi", "fake"}:
            raise ConfiguracionInvalida("PAYMENTS_PROVIDER debe ser 'wompi' o 'fake'")
        if proveedor_pagos == "fake" and not self.modo_pruebas:
            raise ConfiguracionInvalida(
                "PAYMENTS_PROVIDER=fake solo se permite con MONGODB_MODO_PRUEBAS=true"
            )
        if proveedor_pagos == "wompi" and not all(wompi_keys):
            raise ConfiguracionInvalida("PAYMENTS_PROVIDER=wompi requiere las tres llaves WOMPI_*")
        if all(wompi_keys) and proveedor_pagos != "fake":
            self._validar_llaves_wompi()
        if all(wompi_keys) and not self.wompi_redirect_url.strip():
            raise ConfiguracionInvalida("WOMPI_REDIRECT_URL no puede estar vacía")

    def _validar_llaves_wompi(self) -> None:
        entorno = "sandbox" if self.payments_sandbox else "producción"
        prefijos = {
            "WOMPI_PUBLIC_KEY": ("pub_test_" if self.payments_sandbox else "pub_prod_"),
            "WOMPI_INTEGRITY_SECRET": (
                "test_integrity_" if self.payments_sandbox else "prod_integrity_"
            ),
            "WOMPI_EVENTS_SECRET": ("test_events_" if self.payments_sandbox else "prod_events_"),
        }
        if self.wompi_private_key:
            prefijos["WOMPI_PRIVATE_KEY"] = "prv_test_" if self.payments_sandbox else "prv_prod_"
        valores = {
            "WOMPI_PUBLIC_KEY": self.wompi_public_key,
            "WOMPI_PRIVATE_KEY": self.wompi_private_key,
            "WOMPI_INTEGRITY_SECRET": self.wompi_integrity_secret,
            "WOMPI_EVENTS_SECRET": self.wompi_events_secret,
        }
        for nombre, prefijo in prefijos.items():
            valor = valores[nombre]
            if valor and not valor.startswith(prefijo):
                raise ConfiguracionInvalida(
                    f"{nombre} no corresponde al entorno {entorno}; debe empezar por {prefijo}"
                )

    @property
    def cloudinary_configurado(self) -> bool:
        return bool(
            self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret
        )

    @classmethod
    def from_env(
        cls,
        entorno: Mapping[str, str] | None = None,
        *,
        mongo_uri: str | None = None,
    ) -> Settings:
        env = dict(os.environ if entorno is None else entorno)

        host = _texto(env, "MONGODB_HOST")
        uri = str(mongo_uri or _texto(env, "MONGODB_URI")).strip()
        modo_pruebas = _bool(env, "MONGODB_MODO_PRUEBAS")
        if not host and uri:
            # Compatibilidad con el modo de pruebas anterior: si solo hay
            # MONGODB_URI, se usa para todas las conexiones.
            modo_pruebas = True
        if not host and not uri:
            raise ConfiguracionInvalida("MONGODB_HOST es obligatoria para iniciar la API")

        admin_email = _texto(env, "ADMIN_EMAIL").lower()
        admin_password = _texto(env, "ADMIN_PASSWORD")
        if not admin_email:
            raise ConfiguracionInvalida(
                "ADMIN_EMAIL es obligatoria para crear la cuenta inicial del administrador"
            )
        if not admin_password:
            raise ConfiguracionInvalida(
                "ADMIN_PASSWORD es obligatoria para crear la cuenta inicial del administrador"
            )

        base_datos = _texto(env, "MONGODB_DB", "asistente_compras") or "asistente_compras"
        global_por_defecto = base_datos if modo_pruebas else "global_asistente_compras"
        global_db = _texto(env, "MONGODB_GLOBAL_DB", global_por_defecto) or global_por_defecto
        origenes = tuple(
            origen.strip()
            for origen in env.get(
                "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
            ).split(",")
            if origen.strip()
        )

        secreto = _texto(env, "MONGODB_WAREHOUSE_SECRET")
        if modo_pruebas and not secreto:
            secreto = _SECRETO_PRUEBAS

        def password(nombre: str) -> str:
            valor = _texto(env, nombre)
            if modo_pruebas and not valor:
                return _PASSWORD_PRUEBAS
            return valor

        return cls(
            modo_pruebas=modo_pruebas,
            mongodb_uri=uri,
            mongodb_db=base_datos,
            mongodb_host=host or "127.0.0.1:27017",
            mongodb_replica_set=_texto(env, "MONGODB_REPLICA_SET", "rs0") or "rs0",
            mongodb_auth_source=_texto(env, "MONGODB_AUTH_SOURCE", "admin") or "admin",
            mongodb_global_db=global_db,
            mongodb_almacen_prefix=_texto(env, "MONGODB_ALMACEN_PREFIX", "almacen_") or "almacen_",
            mongodb_warehouse_secret=secreto,
            mongo_cliente_user=_texto(env, "MONGO_CLIENTE_USER", "cliente_app") or "cliente_app",
            mongo_cliente_password=password("MONGO_CLIENTE_PASSWORD"),
            mongo_admin_app_user=_texto(env, "MONGO_ADMIN_APP_USER", "admin_app") or "admin_app",
            mongo_admin_app_password=password("MONGO_ADMIN_APP_PASSWORD"),
            mongo_auth_user=_texto(env, "MONGO_AUTH_USER", "auth_service") or "auth_service",
            mongo_auth_password=password("MONGO_AUTH_PASSWORD"),
            mongo_validador_user=_texto(env, "MONGO_VALIDADOR_USER", "validador_catalogo")
            or "validador_catalogo",
            mongo_validador_password=password("MONGO_VALIDADOR_PASSWORD"),
            mongo_catalogo_user=_texto(env, "MONGO_CATALOGO_USER", "replicador_catalogo")
            or "replicador_catalogo",
            mongo_catalogo_password=password("MONGO_CATALOGO_PASSWORD"),
            mongo_compras_user=_texto(env, "MONGO_COMPRAS_USER", "proyector_compras")
            or "proyector_compras",
            mongo_compras_password=password("MONGO_COMPRAS_PASSWORD"),
            mongo_provisioner_user=_texto(env, "MONGO_PROVISIONER_USER", "provisioner")
            or "provisioner",
            mongo_provisioner_password=password("MONGO_PROVISIONER_PASSWORD"),
            admin_email=admin_email,
            admin_password=admin_password,
            admin_nombre=_texto(env, "ADMIN_NOMBRE", "Administrador de la aplicación")
            or "Administrador de la aplicación",
            mongodb_timeout_ms=_leer_int(env, "MONGODB_TIMEOUT_MS", 5000, minimo=100),
            listener_refresh_seconds=_leer_int(env, "LISTENER_REFRESH_SECONDS", 15),
            cors_origins=origenes,
            session_ttl_seconds=_leer_int(env, "SESSION_TTL_SECONDS", 3600),
            max_sessions=_leer_int(env, "MAX_SESSIONS", 1000),
            max_csv_bytes=_leer_int(env, "MAX_CSV_BYTES", 1_000_000),
            max_product_image_bytes=_leer_int(env, "MAX_PRODUCT_IMAGE_BYTES", 2_000_000),
            cloudinary_cloud_name=_texto(env, "CLOUDINARY_CLOUD_NAME"),
            cloudinary_api_key=_texto(env, "CLOUDINARY_API_KEY"),
            cloudinary_api_secret=_texto(env, "CLOUDINARY_API_SECRET"),
            cloudinary_folder=_texto(env, "CLOUDINARY_FOLDER", "asistente-compras")
            or "asistente-compras",
            payments_provider=_texto(env, "PAYMENTS_PROVIDER").lower(),
            payments_sandbox=_bool_estricto(env, "PAYMENTS_SANDBOX", True),
            wompi_public_key=_texto(env, "WOMPI_PUBLIC_KEY"),
            wompi_private_key=_texto(env, "WOMPI_PRIVATE_KEY"),
            wompi_integrity_secret=_texto(env, "WOMPI_INTEGRITY_SECRET"),
            wompi_events_secret=_texto(env, "WOMPI_EVENTS_SECRET"),
            wompi_redirect_url=_texto(
                env,
                "WOMPI_REDIRECT_URL",
                "http://localhost:3000/pago/{reference}",
            ),
            log_level=_texto(env, "LOG_LEVEL", "INFO") or "INFO",
        )

    @classmethod
    def de_pruebas(
        cls,
        *,
        mongodb_uri: str = "mongodb://pruebas",
        mongodb_db: str = "asistente_compras",
        admin_email: str = "admin@example.com",
        admin_password: str = "admin12345",
        **cambios: object,
    ) -> Settings:
        datos: dict[str, object] = {
            "modo_pruebas": True,
            "mongodb_uri": mongodb_uri,
            "mongodb_db": mongodb_db,
            "mongodb_global_db": cambios.pop("mongodb_global_db", mongodb_db),
            "mongodb_warehouse_secret": _SECRETO_PRUEBAS,
            "mongo_cliente_password": _PASSWORD_PRUEBAS,
            "mongo_admin_app_password": _PASSWORD_PRUEBAS,
            "mongo_auth_password": _PASSWORD_PRUEBAS,
            "mongo_validador_password": _PASSWORD_PRUEBAS,
            "mongo_catalogo_password": _PASSWORD_PRUEBAS,
            "mongo_compras_password": _PASSWORD_PRUEBAS,
            "mongo_provisioner_password": _PASSWORD_PRUEBAS,
            "admin_email": admin_email,
            "admin_password": admin_password,
            "cors_origins": (),
            "log_level": "CRITICAL",
            "payments_provider": "fake",
        }
        datos.update(cambios)
        return cls(**datos)  # type: ignore[arg-type]


__all__ = ["Settings"]
