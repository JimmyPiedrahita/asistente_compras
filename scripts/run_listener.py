"""Arranque del listener de catálogo y del proyector de compras.

Uso:
    python scripts/run_listener.py

El proceso mantiene dos tareas en segundo plano:

- ``SincronizadorCatalogo``: replica productos y cupones de cada almacén en la
  base global.
- ``ProyectorCompras``: proyecta la parte de cada almacén de las compras
  globales en ``compras_almacen``.

Al arrancar se ejecuta una reconciliación completa para no depender del
historial de cambios de MongoDB.
"""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path
from types import FrameType

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.config import Settings  # noqa: E402
from core.logging import configurar_logging, obtener_logger  # noqa: E402
from infrastructure.mongodb.contexto import construir_contexto  # noqa: E402

logger = obtener_logger("asistente_compras.listener")

_detener = False


def _senal(signum: int, _frame: FrameType | None) -> None:
    global _detener
    _detener = True
    logger.info("Señal %s recibida; deteniendo el listener", signum)


def main() -> int:
    settings = Settings.from_env()
    configurar_logging(settings.log_level)
    logger.info(
        "Iniciando listener (global=%s, réplica=%s)",
        settings.mongodb_global_db,
        settings.mongodb_replica_set,
    )

    contexto = construir_contexto(settings)
    signal.signal(signal.SIGINT, _senal)
    signal.signal(signal.SIGTERM, _senal)
    try:
        logger.info("Reconciliación inicial de catálogo y compras")
        contexto.sincronizador.reconciliar_todo()
        contexto.proyector.reconciliar_todo()
        contexto.sincronizador.iniciar()
        contexto.proyector.iniciar()
        while not _detener:
            time.sleep(1)
    finally:
        contexto.sincronizador.detener()
        contexto.proyector.detener()
        contexto.cerrar()
        logger.info("Listener detenido")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
