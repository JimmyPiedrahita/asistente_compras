"""Reconstruye manualmente la base integrada ``comparador``.

Uso:
    python scripts/reconciliar_comparador.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.config import Settings  # noqa: E402
from core.logging import configurar_logging  # noqa: E402
from infrastructure.mongodb import SincronizadorComparador  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    configurar_logging(settings.log_level)
    sincronizador = SincronizadorComparador(
        settings.mongodb_uri,
        settings.almacenes,
        comparador_db=settings.mongodb_comparador_db,
        timeout_ms=settings.mongodb_timeout_ms,
    )
    try:
        resultado = sincronizador.reconciliar()
    finally:
        sincronizador.close()

    print(
        "Comparador reconstruido: "
        f"{resultado['reconciliados']} documentos procesados, "
        f"{resultado['documentos']} disponibles."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
