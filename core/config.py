"""Configuración de la aplicación leída desde variables de entorno.

La aplicación usa una única base de datos MongoDB. Los almacenes, productos,
usuarios, cupones y compras son documentos dentro de esa base; no hay bases
por almacén ni proyecciones antiguas.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email

from .errors import ConfiguracionInvalida

_NOMBRE_BASE_VALIDO = re.compile(r"^[A-Za-z0-9_-]+$")


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


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de la aplicación."""

    mongodb_uri: str
    mongodb_db: str = "asistente_compras"
    admin_email: str = ""
    admin_password: str = ""
    admin_nombre: str = "Administrador de la aplicación"
    mongodb_timeout_ms: int = 5000
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://localhost:5173")
    session_ttl_seconds: int = 3600
    max_sessions: int = 1000
    max_csv_bytes: int = 1_000_000
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if not self.mongodb_uri or not self.mongodb_uri.strip():
            raise ConfiguracionInvalida("MONGODB_URI es obligatoria")
        if not _NOMBRE_BASE_VALIDO.match(self.mongodb_db):
            raise ConfiguracionInvalida(
                "MONGODB_DB solo admite letras, números, guion y guion bajo"
            )
        if not self.admin_email or not _email_valido(self.admin_email):
            raise ConfiguracionInvalida("ADMIN_EMAIL es obligatoria y debe ser un correo válido")
        if not self.admin_password or len(self.admin_password) < 8:
            raise ConfiguracionInvalida("ADMIN_PASSWORD debe tener al menos 8 caracteres")
        if self.mongodb_timeout_ms < 100:
            raise ConfiguracionInvalida("MONGODB_TIMEOUT_MS debe ser al menos 100")
        if self.session_ttl_seconds < 1:
            raise ConfiguracionInvalida("SESSION_TTL_SECONDS debe ser positivo")
        if self.max_sessions < 1:
            raise ConfiguracionInvalida("MAX_SESSIONS debe ser positivo")
        if self.max_csv_bytes < 1:
            raise ConfiguracionInvalida("MAX_CSV_BYTES debe ser positivo")

    @classmethod
    def from_env(
        cls,
        entorno: Mapping[str, str] | None = None,
        *,
        mongo_uri: str | None = None,
    ) -> Settings:
        env = dict(os.environ if entorno is None else entorno)

        uri = mongo_uri or env.get("MONGODB_URI", "").strip()
        if not uri:
            raise ConfiguracionInvalida("MONGODB_URI es obligatoria para iniciar la API")

        admin_email = env.get("ADMIN_EMAIL", "").strip().lower()
        admin_password = env.get("ADMIN_PASSWORD", "").strip()
        if not admin_email:
            raise ConfiguracionInvalida(
                "ADMIN_EMAIL es obligatoria para crear la cuenta inicial del administrador"
            )
        if not admin_password:
            raise ConfiguracionInvalida(
                "ADMIN_PASSWORD es obligatoria para crear la cuenta inicial del administrador"
            )

        base_datos = env.get("MONGODB_DB", "asistente_compras").strip() or "asistente_compras"
        origenes = tuple(
            origen.strip()
            for origen in env.get(
                "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
            ).split(",")
            if origen.strip()
        )

        return cls(
            mongodb_uri=uri,
            mongodb_db=base_datos,
            admin_email=admin_email,
            admin_password=admin_password,
            admin_nombre=env.get("ADMIN_NOMBRE", "Administrador de la aplicación").strip()
            or "Administrador de la aplicación",
            mongodb_timeout_ms=_leer_int(env, "MONGODB_TIMEOUT_MS", 5000, minimo=100),
            cors_origins=origenes,
            session_ttl_seconds=_leer_int(env, "SESSION_TTL_SECONDS", 3600),
            max_sessions=_leer_int(env, "MAX_SESSIONS", 1000),
            max_csv_bytes=_leer_int(env, "MAX_CSV_BYTES", 1_000_000),
            log_level=env.get("LOG_LEVEL", "INFO").strip() or "INFO",
        )

    @classmethod
    def de_pruebas(
        cls,
        *,
        mongodb_uri: str = "mongodb://pruebas",
        admin_email: str = "admin@example.com",
        admin_password: str = "admin12345",
        **cambios: object,
    ) -> Settings:
        datos: dict[str, object] = {
            "mongodb_uri": mongodb_uri,
            "admin_email": admin_email,
            "admin_password": admin_password,
            "cors_origins": (),
            "log_level": "CRITICAL",
        }
        datos.update(cambios)
        return cls(**datos)  # type: ignore[arg-type]


__all__ = ["Settings"]
