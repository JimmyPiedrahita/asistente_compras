"""Carga idempotente del CSV de ejemplo en MongoDB.

Uso:
    python scripts/seed_mongodb.py
    python -m scripts.seed_mongodb --archivo productos_ejemplo.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.config import Settings  # noqa: E402
from core.errors import ErrorAplicacion  # noqa: E402
from infrastructure.mongodb import MongoInventarioRepository  # noqa: E402
from models.productos import FabricaProductos  # noqa: E402
from models.texto import normalizar_texto  # noqa: E402


def _entero(valor: str, defecto: int = 1) -> int:
    return int(valor) if str(valor).strip() else defecto


def cargar(archivo: Path) -> tuple[int, int, int, list[str]]:
    settings = Settings.from_env()
    repositorio = MongoInventarioRepository(
        settings.mongodb_uri,
        settings.almacenes,
        comparador_db=settings.mongodb_comparador_db,
        timeout_ms=settings.mongodb_timeout_ms,
    )
    insertados = actualizados = rechazados = 0
    errores: list[str] = []
    try:
        with archivo.open(encoding="utf-8-sig", newline="") as handle:
            lector = csv.DictReader(handle)
            for numero, fila in enumerate(lector, start=2):
                try:
                    datos = {
                        normalizar_texto(clave): str(valor or "").strip()
                        for clave, valor in fila.items()
                        if clave is not None
                    }
                    id_almacen = _entero(datos.get("almacen", ""))
                    tipo = datos.get("tipo") or "normal"
                    extra = datos.get("extra") or ""
                    kwargs: dict[str, object] = {}
                    if normalizar_texto(tipo) == "fisico":
                        kwargs["costo_envio"] = float(extra) if extra else 5.0
                    elif normalizar_texto(tipo) == "suscripcion":
                        kwargs["meses"] = _entero(extra)

                    producto = FabricaProductos.crear_producto(
                        tipo,
                        datos.get("nombre", ""),
                        float(datos.get("precio", "")),
                        marca=datos.get("marca") or "Generica",
                        categoria=datos.get("categoria") or "General",
                        **kwargs,
                    )
                    resultado = repositorio.upsert_por_nombre_marca(id_almacen, producto)
                    if resultado == "insertado":
                        insertados += 1
                    else:
                        actualizados += 1
                except (ValueError, TypeError, KeyError, OverflowError, ErrorAplicacion) as error:
                    rechazados += 1
                    errores.append(f"Línea {numero}: {error}")
    finally:
        repositorio.close()

    return insertados, actualizados, rechazados, errores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archivo",
        type=Path,
        default=RAIZ / "productos_ejemplo.csv",
        help="CSV de productos (por defecto: productos_ejemplo.csv)",
    )
    args = parser.parse_args()
    if not args.archivo.exists():
        print(f"No existe el archivo: {args.archivo}", file=sys.stderr)
        return 2

    insertados, actualizados, rechazados, errores = cargar(args.archivo)
    print(
        f"Seed finalizado: {insertados} insertados, "
        f"{actualizados} actualizados, {rechazados} rechazados."
    )
    for error in errores:
        print(f"  - {error}", file=sys.stderr)
    return 0 if rechazados == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
