"""Proceso del listener que mantiene ``comparador`` sincronizado.

Uso:
    python scripts/run_listener.py

Requiere MongoDB en modo replica set. El proceso se reinicia solo en Docker y
procesa los cambios de forma idempotente.
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.config import Settings  # noqa: E402
from core.logging import configurar_logging, obtener_logger  # noqa: E402
from infrastructure.mongodb import SincronizadorComparador  # noqa: E402


def main() -> int:
    try:
        settings = Settings.from_env()
    except RuntimeError as error:
        print(f"Configuración inválida: {error}", file=sys.stderr)
        return 2

    configurar_logging(settings.log_level)
    logger = obtener_logger("asistente_compras.listener")

    sincronizador = SincronizadorComparador(
        settings.mongodb_uri,
        settings.almacenes,
        comparador_db=settings.mongodb_comparador_db,
        timeout_ms=settings.mongodb_timeout_ms,
    )

    def detener(signum, _frame) -> None:
        logger.info("Señal %s recibida; deteniendo listener", signum)
        sincronizador.detener()

    signal.signal(signal.SIGTERM, detener)
    signal.signal(signal.SIGINT, detener)

    try:
        logger.info(
            "Listener iniciado: %s almacenes -> %s",
            len(settings.almacenes),
            settings.mongodb_comparador_db,
        )
        sincronizador.ejecutar()
    except RuntimeError as error:
        logger.error("No se pudo iniciar el listener: %s", error)
        return 3
    finally:
        sincronizador.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
