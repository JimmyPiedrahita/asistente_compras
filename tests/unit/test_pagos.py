"""Pruebas del adaptador de pagos."""

from __future__ import annotations

import hashlib

import pytest

from infrastructure.pagos import (
    AdaptadorWompi,
    ConfiguracionPagosInvalida,
    ProveedorPagosDeshabilitado,
    ProveedorPagosPrueba,
    construir_proveedor,
    cop_a_centavos,
)

EVENTOS_SECRETO = "test_events_secreto-de-pruebas"
INTEGRIDAD_SECRETO = "test_integrity_secreto-de-pruebas"


def _adaptador(**cambios: object) -> AdaptadorWompi:
    opciones = {
        "public_key": "pub_test_123",
        "integrity_secret": INTEGRIDAD_SECRETO,
        "events_secret": EVENTOS_SECRETO,
        "redirect_url": "http://localhost:3000/pago/{reference}",
    }
    opciones.update(cambios)
    return AdaptadorWompi(**opciones)


def _evento(*, checksum: str | None = None, timestamp: int = 1530291411) -> dict:
    propiedades = ["transaction.id", "transaction.status", "transaction.amount_in_cents"]
    valores = ["1234-1610641025-49201", "APPROVED", 925000]
    cadena = "".join(str(valor) for valor in valores) + str(timestamp) + EVENTOS_SECRETO
    return {
        "event": "transaction.updated",
        "data": {
            "transaction": {
                "id": valores[0],
                "status": valores[1],
                "amount_in_cents": valores[2],
                "reference": "compra-123",
                "currency": "COP",
            }
        },
        "environment": "test",
        "signature": {
            "properties": propiedades,
            "checksum": (checksum or hashlib.sha256(cadena.encode()).hexdigest()),
        },
        "timestamp": timestamp,
    }


def test_cop_a_centavos_suma_sin_perder_centavos() -> None:
    assert cop_a_centavos(9250) == 925000
    assert cop_a_centavos(19.95) == 1995


def test_wompi_crea_checkout_hosted_con_firma_e_integridad() -> None:
    adaptador = _adaptador()
    pago = adaptador.crear_checkout(
        referencia="compra-123",
        monto_cents=925000,
        moneda="COP",
        correo="cliente@example.com",
        nombre="Cliente Ejemplo",
    )
    assert pago["checkout_url"].startswith("https://checkout.wompi.co/p/?")
    assert "reference=compra-123" in pago["checkout_url"]
    assert "amount-in-cents=925000" in pago["checkout_url"]
    # Wompi exige los nombres con dos puntos; con otros nombres el checkout
    # se crea sin firma de integridad.
    assert "signature%3Aintegrity=" in pago["checkout_url"]
    assert "customer-data%3Aemail=" in pago["checkout_url"]
    assert "customer-data%3Afull-name=" in pago["checkout_url"]
    assert "redirect-url=" not in pago["checkout_url"]
    assert pago["estado"] == "PENDING"


def test_wompi_incluye_redireccion_publica() -> None:
    pago = _adaptador(redirect_url="https://demo.example.com/pago/{reference}").crear_checkout(
        referencia="compra-123",
        monto_cents=925000,
        moneda="COP",
        correo="",
        nombre="",
    )
    assert "redirect-url=https%3A%2F%2Fdemo.example.com%2Fpago%2Fcompra-123" in pago["checkout_url"]


def test_wompi_valida_la_firma_sobre_data() -> None:
    assert _adaptador().verificar_evento(_evento()) is True


def test_wompi_acepta_checksum_en_mayusculas() -> None:
    evento = _evento()
    evento["signature"]["checksum"] = evento["signature"]["checksum"].upper()
    assert _adaptador().verificar_evento(evento) is True


def test_wompi_rechaza_un_evento_manipulado() -> None:
    evento = _evento()
    evento["data"]["transaction"]["amount_in_cents"] = 1
    assert _adaptador().verificar_evento(evento) is False


def test_wompi_rechaza_eventos_de_otro_ambiente() -> None:
    evento = _evento()
    evento["environment"] = "prod"
    assert _adaptador().verificar_evento(evento) is False


def test_wompi_exige_llaves_del_entorno_configurado() -> None:
    with pytest.raises(ConfiguracionPagosInvalida):
        _adaptador(public_key="pub_prod_123")
    with pytest.raises(ConfiguracionPagosInvalida):
        _adaptador(integrity_secret="prod_integrity_123")
    with pytest.raises(ConfiguracionPagosInvalida):
        _adaptador(events_secret="prod_events_123")
    with pytest.raises(ConfiguracionPagosInvalida):
        _adaptador(public_key="pk_test_123")


class _SettingsFake:
    modo_pruebas = False
    payments_provider = ""
    wompi_public_key = ""
    wompi_private_key = ""
    wompi_integrity_secret = ""
    wompi_events_secret = ""
    wompi_redirect_url = "http://localhost:3000/pago/{reference}"
    payments_sandbox = True


def test_sin_llaves_la_pasarela_queda_deshabilitada() -> None:
    proveedor = construir_proveedor(_SettingsFake())
    assert isinstance(proveedor, ProveedorPagosDeshabilitado)


def test_proveedor_wompi_explicito_sin_llaves_falla() -> None:
    settings = _SettingsFake()
    settings.payments_provider = "wompi"
    with pytest.raises(ConfiguracionPagosInvalida):
        construir_proveedor(settings)


def test_proveedor_falso_solo_en_modo_de_pruebas() -> None:
    settings = _SettingsFake()
    settings.payments_provider = "fake"
    with pytest.raises(ConfiguracionPagosInvalida):
        construir_proveedor(settings)

    settings.modo_pruebas = True
    assert isinstance(construir_proveedor(settings), ProveedorPagosPrueba)
