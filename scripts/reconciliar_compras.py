"""Reconstrucción manual de las proyecciones ``compras_almacen``.

Uso:
    python scripts/reconciliar_compras.py

Recorre todas las compras globales y vuelve a proyectar la parte de cada
almacén. También elimina proyecciones que ya no corresponden a ninguna compra
global.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.config import Settings  # noqa: E402
from core.logging import configurar_logging, obtener_logger  # noqa: E402
from infrastructure.mongodb.contexto import construir_contexto  # noqa: E402

logger = obtener_logger("asistente_compras.reconciliar_compras")


def main() -> int:
    settings = Settings.from_env()
    configurar_logging(settings.log_level)
    contexto = construir_contexto(settings)
    try:
        contexto.proyector.reconciliar_todo()
        logger.info("Compras proyectadas reconciliadas")
    finally:
        contexto.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
