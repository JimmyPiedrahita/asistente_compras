"""Configuración de la aplicación leída desde variables de entorno."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

from .errors import ConfiguracionInvalida

_PREFIJO_VALIDO = re.compile(r"^[A-Za-z0-9_-]+$")
_NOMBRE_BASE_VALIDO = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class AlmacenConfig:
    """Identidad lógica y base de datos de un almacén."""

    id: int
    nombre: str
    base_datos: str


def crear_almacenes(prefijo: str = "warehouse") -> tuple[AlmacenConfig, ...]:
    return tuple(
        AlmacenConfig(
            id=id_almacen,
            nombre=f"Almacen {id_almacen}",
            base_datos=f"{prefijo}_{id_almacen}",
        )
        for id_almacen in (1, 2, 3)
    )


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


def _parsear_almacenes(entorno: Mapping[str, str], prefijo: str) -> tuple[AlmacenConfig, ...]:
    crudo = (entorno.get("WAREHOUSES") or "").strip()
    if not crudo:
        return crear_almacenes(prefijo)

    almacenes: list[AlmacenConfig] = []
    for parte in crudo.split(","):
        parte = parte.strip()
        if not parte:
            continue
        if ":" in parte:
            id_crudo, nombre = parte.split(":", 1)
            nombre = nombre.strip()
        else:
            id_crudo, nombre = parte, ""
        try:
            id_almacen = int(id_crudo.strip())
        except ValueError as error:
            raise ConfiguracionInvalida(
                "WAREHOUSES debe usar el formato 1:Nombre,2:Nombre"
            ) from error
        if id_almacen < 1:
            raise ConfiguracionInvalida("Los ids de WAREHOUSES deben ser positivos")
        almacenes.append(
            AlmacenConfig(
                id=id_almacen,
                nombre=nombre or f"Almacen {id_almacen}",
                base_datos=f"{prefijo}_{id_almacen}",
            )
        )

    if not almacenes:
        raise ConfiguracionInvalida("WAREHOUSES no contiene almacenes válidos")
    if len({almacen.id for almacen in almacenes}) != len(almacenes):
        raise ConfiguracionInvalida("WAREHOUSES contiene ids duplicados")
    return tuple(almacenes)


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de la aplicación."""

    mongodb_uri: str
    admin_clave: str
    mongodb_db_prefix: str = "warehouse"
    mongodb_comparador_db: str = "comparador"
    mongodb_timeout_ms: int = 5000
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    session_ttl_seconds: int = 3600
    max_sessions: int = 1000
    max_csv_bytes: int = 1_000_000
    log_level: str = "INFO"
    almacenes: tuple[AlmacenConfig, ...] | None = None

    def __post_init__(self) -> None:
        if not self.mongodb_uri or not self.mongodb_uri.strip():
            raise ConfiguracionInvalida("MONGODB_URI es obligatoria")
        if not self.admin_clave or len(self.admin_clave) < 8:
            raise ConfiguracionInvalida("ADMIN_CLAVE debe tener al menos 8 caracteres")
        if not _PREFIJO_VALIDO.match(self.mongodb_db_prefix):
            raise ConfiguracionInvalida(
                "MONGODB_DB_PREFIX solo admite letras, números, guion y guion bajo"
            )
        if not _NOMBRE_BASE_VALIDO.match(self.mongodb_comparador_db):
            raise ConfiguracionInvalida(
                "MONGODB_COMPARADOR_DB solo admite letras, números, guion y guion bajo"
            )
        if self.almacenes is None:
            object.__setattr__(self, "almacenes", crear_almacenes(self.mongodb_db_prefix))
        if not self.almacenes:
            raise ConfiguracionInvalida("Debe configurarse al menos un almacén")
        if any(almacen.base_datos == self.mongodb_comparador_db for almacen in self.almacenes):
            raise ConfiguracionInvalida(
                "MONGODB_COMPARADOR_DB no puede coincidir con la base de un almacén"
            )
        ids = [almacen.id for almacen in self.almacenes]
        if len(set(ids)) != len(ids):
            raise ConfiguracionInvalida("Los ids de almacén no pueden repetirse")
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

        admin_clave = env.get("ADMIN_CLAVE", "").strip()
        if not admin_clave:
            raise ConfiguracionInvalida(
                "ADMIN_CLAVE es obligatoria; no se admite una clave por defecto"
            )

        prefijo = env.get("MONGODB_DB_PREFIX", "warehouse").strip() or "warehouse"
        comparador = env.get("MONGODB_COMPARADOR_DB", "comparador").strip() or "comparador"
        origenes = tuple(
            origen.strip()
            for origen in env.get("CORS_ORIGINS", "http://localhost:3000").split(",")
            if origen.strip()
        )

        return cls(
            mongodb_uri=uri,
            admin_clave=admin_clave,
            mongodb_db_prefix=prefijo,
            mongodb_comparador_db=comparador,
            mongodb_timeout_ms=_leer_int(env, "MONGODB_TIMEOUT_MS", 5000, minimo=100),
            cors_origins=origenes,
            session_ttl_seconds=_leer_int(env, "SESSION_TTL_SECONDS", 3600),
            max_sessions=_leer_int(env, "MAX_SESSIONS", 1000),
            max_csv_bytes=_leer_int(env, "MAX_CSV_BYTES", 1_000_000),
            log_level=env.get("LOG_LEVEL", "INFO").strip() or "INFO",
            almacenes=_parsear_almacenes(env, prefijo),
        )

    @classmethod
    def de_pruebas(
        cls,
        *,
        mongodb_uri: str = "mongodb://pruebas",
        admin_clave: str = "admin123",
        **cambios: object,
    ) -> Settings:
        datos: dict[str, object] = {
            "mongodb_uri": mongodb_uri,
            "admin_clave": admin_clave,
            "cors_origins": (),
            "log_level": "CRITICAL",
        }
        datos.update(cambios)
        return cls(**datos)  # type: ignore[arg-type]


__all__ = ["AlmacenConfig", "Settings", "crear_almacenes"]
