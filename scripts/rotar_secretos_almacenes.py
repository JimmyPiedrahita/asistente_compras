"""Rotación de las contraseñas HMAC de todos los almacenes.

Uso:
    MONGODB_WAREHOUSE_SECRET=<secreto-nuevo> \\
        python scripts/rotar_secretos_almacenes.py --anterior <secreto-anterior>

El script usa el usuario ``provisioner`` para actualizar la contraseña nativa de
cada almacén. No guarda ni imprime contraseñas. Al terminar, actualiza
``MONGODB_WAREHOUSE_SECRET`` en el entorno y reinicia la API y el listener.

Si algún almacén no tiene usuario nativo (por ejemplo, porque se creó en modo
de pruebas), se informa y se continúa.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from pymongo.errors import OperationFailure  # noqa: E402

from core.config import Settings  # noqa: E402
from core.logging import configurar_logging, obtener_logger  # noqa: E402
from infrastructure.mongodb.conexiones import ConexionesMongo  # noqa: E402
from infrastructure.mongodb.global_db import RepositorioAlmacenes  # noqa: E402
from infrastructure.mongodb.uri import FabricaURIs  # noqa: E402

logger = obtener_logger("asistente_compras.rotar_secretos")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--anterior",
        default="",
        help="Secreto anterior. Solo se usa para verificar que la rotación es intencional.",
    )
    parser.add_argument(
        "--nuevo",
        default="",
        help="Secreto nuevo. Si se omite, se usa MONGODB_WAREHOUSE_SECRET.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    configurar_logging(settings.log_level)
    if settings.modo_pruebas:
        print("La rotación solo aplica al modo con usuarios nativos de MongoDB.")
        return 2

    nuevo = str(args.nuevo or settings.mongodb_warehouse_secret).strip()
    anterior = str(args.anterior or "").strip()
    if len(nuevo) < 32:
        print("El secreto nuevo debe tener al menos 32 caracteres.")
        return 2
    if anterior and anterior == nuevo:
        print("El secreto anterior y el nuevo son iguales; no hay nada que rotar.")
        return 2

    settings_nuevo = dataclasses.replace(settings, mongodb_warehouse_secret=nuevo)
    fabrica = FabricaURIs(settings_nuevo)
    conexiones = ConexionesMongo(settings.mongodb_timeout_ms)
    try:
        base_admin = conexiones.base(fabrica.uri_admin_app(), settings.mongodb_global_db)
        repo_almacenes = RepositorioAlmacenes(base_admin)
        admin = conexiones.cliente(fabrica.uri_provisioner()).base("admin")

        almacenes = repo_almacenes.listar()
        if not almacenes:
            print("No hay almacenes para rotar.")
            return 0

        fallos: list[str] = []
        for almacen in almacenes:
            if not almacen.mongo_user:
                logger.warning("El almacén %s no tiene usuario nativo", almacen.almacen_id)
                continue
            password = fabrica.password_almacen(almacen.almacen_id)
            try:
                admin.command(
                    "updateUser",
                    almacen.mongo_user,
                    pwd=password,
                )
            except OperationFailure as error:
                logger.error("No se pudo actualizar %s: %s", almacen.mongo_user, error)
                fallos.append(almacen.nombre)
                continue
            try:
                conexiones.ping(fabrica.uri_almacen(almacen))
            except Exception as error:  # pragma: no cover - diagnóstico
                logger.error("La nueva contraseña no funciona para %s: %s", almacen.nombre, error)
                fallos.append(almacen.nombre)
                continue
            logger.info("Contraseña rotada para %s", almacen.nombre)

        if fallos:
            print("No se pudieron rotar: " + ", ".join(fallos))
            return 1
        print(
            f"Rotación completada para {len(almacenes)} almacén(es). "
            "Actualiza MONGODB_WAREHOUSE_SECRET y reinicia API y listener."
        )
        return 0
    finally:
        conexiones.cerrar()


if __name__ == "__main__":
    raise SystemExit(main())
