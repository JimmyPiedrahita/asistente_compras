"""Usuarios, contraseñas y validaciones de identidad."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from email_validator import EmailNotValidError, validate_email

_ITERACIONES = 210_000


def es_email_valido(email: str) -> bool:
    try:
        validate_email(str(email or "").strip(), check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def hashear_password(password: str) -> str:
    """Hash PBKDF2-HMAC-SHA256 con salt aleatorio."""
    if not password:
        raise ValueError("La contraseña no puede estar vacía")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERACIONES
    ).hex()
    return f"pbkdf2_sha256${_ITERACIONES}${salt}${digest}"


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        algoritmo, iteraciones, salt, digest = str(password_hash).split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        calculado = hashlib.pbkdf2_hmac(
            "sha256",
            str(password).encode("utf-8"),
            salt.encode("utf-8"),
            int(iteraciones),
        ).hex()
        return hmac.compare_digest(calculado, digest)
    except (ValueError, TypeError):
        return False


@dataclass
class Usuario:
    usuario_id: str
    nombre: str
    email: str
    password_hash: str
    rol: str
    almacen_id: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    autoriza_datos: bool = False
    activo: bool = True
    creado_en: datetime | None = field(default_factory=lambda: datetime.now(timezone.utc))

    def publico(self) -> dict[str, Any]:
        return {
            "usuario_id": self.usuario_id,
            "nombre": self.nombre,
            "email": self.email,
            "rol": self.rol,
            "almacen_id": self.almacen_id,
            "telefono": self.telefono,
            "direccion": self.direccion,
            "ciudad": self.ciudad,
            "activo": self.activo,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }


__all__ = [
    "Usuario",
    "es_email_valido",
    "hashear_password",
    "verificar_password",
]
