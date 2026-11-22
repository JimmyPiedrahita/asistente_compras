"""Reconstrucción manual de ``productos_global`` y ``cupones_global``.

Uso:
    python scripts/reconciliar_catalogo.py
    python scripts/reconciliar_catalogo.py --almacen-id <almacen_id>

Sin argumentos reconcilia todos los almacenes activos. Es seguro ejecutarlo
varias veces: los documentos se actualizan por ``upsert`` y los obsoletos se
eliminan.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.config import Settings  # noqa: E402
from core.errors import NoEncontrado  # noqa: E402
from core.logging import configurar_logging, obtener_logger  # noqa: E402
from infrastructure.mongodb.contexto import construir_contexto  # noqa: E402

logger = obtener_logger("asistente_compras.reconciliar_catalogo")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--almacen-id",
        default="",
        help="Reconciliar solo este almacén",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    configurar_logging(settings.log_level)
    contexto = construir_contexto(settings)
    try:
        if args.almacen_id:
            almacen = contexto.repo_almacenes.obtener(args.almacen_id)
            if almacen is None or not almacen.db_name:
                raise NoEncontrado("Almacén no encontrado o sin base de datos")
            contexto.sincronizador.reconciliar_almacen(almacen)
            logger.info("Catálogo reconciliado para %s", almacen.nombre)
        else:
            contexto.sincronizador.reconciliar_todo()
            logger.info("Catálogo reconciliado para todos los almacenes")
    finally:
        contexto.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
