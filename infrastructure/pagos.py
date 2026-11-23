"""Adaptadores de pasarelas de pago."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

logger = logging.getLogger(__name__)


class ConfiguracionPagosInvalida(Exception):
    """Configuración de la pasarela ausente o inconsistente."""


class ErrorPasarela(Exception):
    """Fallo al comunicarse con la pasarela de pagos."""


class ProveedorPagos:
    """Interfaz mínima usada por el checkout."""

    proveedor = "none"

    def crear_checkout(
        self,
        *,
        referencia: str,
        monto_cents: int,
        moneda: str,
        correo: str,
        nombre: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def verificar_evento(self, evento: dict[str, Any]) -> bool:
        raise NotImplementedError

    def consultar_transaccion(self, transaccion_id: str) -> dict[str, Any] | None:
        """Consulta el estado actual de una transacción en la pasarela."""
        return None


def cop_a_centavos(valor: float) -> int:
    centavos = (Decimal(str(valor)) * Decimal("100")).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    return int(centavos)


class ProveedorPagosDeshabilitado(ProveedorPagos):
    """Proveedor seguro cuando no hay credenciales configuradas.

    No genera checkouts y rechaza cualquier evento: si no hay una pasarela
    configurada es preferible fallar a aceptar pagos sin validar.
    """

    proveedor = "none"

    def crear_checkout(
        self,
        *,
        referencia: str,
        monto_cents: int,
        moneda: str,
        correo: str,
        nombre: str,
    ) -> dict[str, Any]:
        raise ConfiguracionPagosInvalida(
            "La pasarela de pagos no está configurada. "
            "Define WOMPI_PUBLIC_KEY, WOMPI_INTEGRITY_SECRET y WOMPI_EVENTS_SECRET."
        )

    def verificar_evento(self, evento: dict[str, Any]) -> bool:
        return False


class ProveedorPagosPrueba(ProveedorPagos):
    """Proveedor determinista para ejecutar pruebas sin una pasarela externa."""

    proveedor = "sandbox"

    def crear_checkout(
        self,
        *,
        referencia: str,
        monto_cents: int,
        moneda: str,
        correo: str,
        nombre: str,
    ) -> dict[str, Any]:
        return {
            "proveedor": "sandbox",
            "referencia_externa": referencia,
            "checkout_url": None,
            "monto": monto_cents,
            "moneda": moneda,
            "estado": "PENDING",
        }

    def verificar_evento(self, evento: dict[str, Any]) -> bool:
        return (
            evento.get("environment") == "test"
            and isinstance(evento.get("data"), dict)
            and isinstance(evento["data"].get("transaction"), dict)
        )


class AdaptadorWompi(ProveedorPagos):
    """Genera checkouts hospedados y valida eventos de Wompi Colombia."""

    proveedor = "wompi"

    def __init__(
        self,
        *,
        public_key: str,
        integrity_secret: str,
        events_secret: str,
        redirect_url: str,
        private_key: str = "",
        sandbox: bool = True,
    ) -> None:
        if not public_key or not integrity_secret or not events_secret:
            raise ConfiguracionPagosInvalida(
                "WOMPI_PUBLIC_KEY, WOMPI_INTEGRITY_SECRET y WOMPI_EVENTS_SECRET son obligatorias"
            )
        if not redirect_url:
            raise ConfiguracionPagosInvalida("WOMPI_REDIRECT_URL es obligatoria")

        prefijos = {
            "pública": (
                "pub_test_" if sandbox else "pub_prod_",
                public_key,
            ),
            "de integridad": (
                "test_integrity_" if sandbox else "prod_integrity_",
                integrity_secret,
            ),
            "de eventos": (
                "test_events_" if sandbox else "prod_events_",
                events_secret,
            ),
        }
        if private_key:
            prefijos["privada"] = (
                "prv_test_" if sandbox else "prv_prod_",
                private_key,
            )
        for nombre, (prefijo, valor) in prefijos.items():
            if not str(valor).startswith(prefijo):
                entorno = "sandbox" if sandbox else "producción"
                raise ConfiguracionPagosInvalida(
                    f"La llave {nombre} de Wompi no corresponde al entorno {entorno}; "
                    f"debe empezar por {prefijo}"
                )

        self.public_key = public_key
        self.private_key = private_key
        self.integrity_secret = integrity_secret
        self.events_secret = events_secret
        self.redirect_url = redirect_url
        self.sandbox = sandbox
        self.entorno = "test" if sandbox else "prod"
        self.api_base = (
            "https://sandbox.wompi.co/v1" if sandbox else "https://production.wompi.co/v1"
        )

    def crear_checkout(
        self,
        *,
        referencia: str,
        monto_cents: int,
        moneda: str,
        correo: str,
        nombre: str,
    ) -> dict[str, Any]:
        if monto_cents < 1:
            raise ConfiguracionPagosInvalida("El monto del pago debe ser positivo")
        integridad = hashlib.sha256(
            f"{referencia}{monto_cents}{moneda}{self.integrity_secret}".encode()
        ).hexdigest()

        parametros = {
            "public-key": self.public_key,
            "currency": moneda,
            "amount-in-cents": monto_cents,
            "reference": referencia,
            "signature:integrity": integridad,
        }
        redirect = self.redirect_url.replace("{reference}", quote(referencia)).strip()
        host = (urlsplit(redirect).hostname or "").lower()
        if host not in {"localhost", "127.0.0.1", "::1"}:
            parametros["redirect-url"] = redirect
        else:
            logger.warning(
                "Se omite WOMPI_REDIRECT_URL local porque Wompi no acepta "
                "redirecciones hacia localhost; usa una URL pública HTTPS para recibir el retorno"
            )
        if correo:
            parametros["customer-data:email"] = correo
        if nombre:
            parametros["customer-data:full-name"] = nombre

        return {
            "proveedor": "wompi",
            "referencia_externa": referencia,
            "checkout_url": f"https://checkout.wompi.co/p/?{urlencode(parametros)}",
            "monto": monto_cents,
            "moneda": moneda,
            "estado": "PENDING",
        }

    def verificar_evento(self, evento: dict[str, Any]) -> bool:
        if evento.get("environment") != self.entorno:
            return False
        firma = evento.get("signature")
        if not isinstance(firma, dict):
            return False
        propiedades = firma.get("properties")
        timestamp = evento.get("timestamp")
        checksum = firma.get("checksum")
        if not isinstance(propiedades, list) or timestamp is None or not isinstance(checksum, str):
            return False

        partes: list[str] = []
        for propiedad in propiedades:
            # Las propiedades de la firma apuntan a campos dentro de ``data``.
            valor: Any = evento.get("data") or {}
            for segmento in str(propiedad).split("."):
                if not isinstance(valor, dict):
                    valor = None
                    break
                valor = valor.get(segmento)
            partes.append("" if valor is None else str(valor))

        cadena = "".join(partes) + str(timestamp) + self.events_secret
        calculado = hashlib.sha256(cadena.encode()).hexdigest()
        return hmac.compare_digest(calculado, checksum.strip().lower())

    def consultar_transaccion(self, transaccion_id: str) -> dict[str, Any] | None:
        if not self.private_key or not transaccion_id:
            return None
        url = f"{self.api_base}/transactions/{quote(str(transaccion_id))}"
        peticion = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.private_key}",
            },
        )
        try:
            with urllib.request.urlopen(peticion, timeout=10) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            raise ErrorPasarela(f"No se pudo consultar la transacción en Wompi: {error}") from error
        if isinstance(datos, dict) and isinstance(datos.get("data"), dict):
            return datos["data"]
        return datos if isinstance(datos, dict) else None


def construir_proveedor(settings: Any) -> ProveedorPagos:
    proveedor = str(getattr(settings, "payments_provider", "") or "").strip().lower()
    if proveedor == "fake":
        if not getattr(settings, "modo_pruebas", False):
            raise ConfiguracionPagosInvalida(
                "PAYMENTS_PROVIDER=fake solo se permite en modo de pruebas"
            )
        return ProveedorPagosPrueba()
    if proveedor == "wompi":
        return AdaptadorWompi(
            public_key=settings.wompi_public_key,
            integrity_secret=settings.wompi_integrity_secret,
            events_secret=settings.wompi_events_secret,
            redirect_url=settings.wompi_redirect_url,
            private_key=getattr(settings, "wompi_private_key", ""),
            sandbox=bool(settings.payments_sandbox),
        )
    if proveedor not in {"", "auto"}:
        raise ConfiguracionPagosInvalida("PAYMENTS_PROVIDER debe ser 'wompi' o 'fake'")
    if settings.wompi_public_key:
        return AdaptadorWompi(
            public_key=settings.wompi_public_key,
            integrity_secret=settings.wompi_integrity_secret,
            events_secret=settings.wompi_events_secret,
            redirect_url=settings.wompi_redirect_url,
            private_key=getattr(settings, "wompi_private_key", ""),
            sandbox=bool(settings.payments_sandbox),
        )
    logger.warning(
        "Pagos deshabilitados: define WOMPI_PUBLIC_KEY, WOMPI_INTEGRITY_SECRET y "
        "WOMPI_EVENTS_SECRET para habilitar Wompi"
    )
    return ProveedorPagosDeshabilitado()


__all__ = [
    "AdaptadorWompi",
    "ConfiguracionPagosInvalida",
    "ErrorPasarela",
    "ProveedorPagos",
    "ProveedorPagosDeshabilitado",
    "ProveedorPagosPrueba",
    "construir_proveedor",
    "cop_a_centavos",
]
