"""Genera ``openapi.yaml`` a partir de FastAPI sin conectarse a MongoDB.

Uso:
    python scripts/exportar_openapi.py
    python scripts/exportar_openapi.py --salida openapi.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import yaml  # noqa: E402

from core.config import Settings  # noqa: E402
from infrastructure.mongodb import RepositorioNulo  # noqa: E402
from views.api.app import create_app  # noqa: E402


def generar(salida: Path) -> None:
    settings = Settings.de_pruebas()
    app = create_app(settings, repository_factory=lambda _: RepositorioNulo())
    esquema = app.openapi()
    esquema = {
        "openapi": esquema["openapi"],
        "info": esquema["info"],
        "servers": [{"url": "http://localhost:8000", "description": "Servidor local"}],
        **{clave: valor for clave, valor in esquema.items() if clave not in {"openapi", "info"}},
    }
    salida.write_text(
        yaml.safe_dump(esquema, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--salida",
        type=Path,
        default=RAIZ / "openapi.yaml",
        help="Ruta del archivo de salida",
    )
    args = parser.parse_args()
    generar(args.salida)
    print(f"OpenAPI generado en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
