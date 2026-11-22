"""Verificación de los roles nativos de MongoDB.

Crea dos almacenes temporales, ejecuta operaciones permitidas y prohibidas con
cada usuario de servicio y elimina los datos de prueba al terminar.

Uso:
    python scripts/verificar_rbac.py
    python scripts/verificar_rbac.py --conservar

Requiere el modo Docker (replica set con autenticación). En modo de pruebas no
hay usuarios nativos y el script termina con un mensaje explicativo.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote_plus

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from pymongo import MongoClient  # noqa: E402
from pymongo.database import Database  # noqa: E402
from pymongo.errors import OperationFailure  # noqa: E402

from core.config import Settings  # noqa: E402
from core.logging import configurar_logging, obtener_logger  # noqa: E402
from infrastructure.mongodb.contexto import ContextoAplicacion, construir_contexto  # noqa: E402
from models.almacenes import Almacen  # noqa: E402

logger = obtener_logger("asistente_compras.verificar_rbac")

_CODIGOS_DENEGADO = {13, 18, 8000}


class Verificador:
    def __init__(self) -> None:
        self.fallos: list[str] = []

    def permitido(self, descripcion: str, operacion: Callable[[], object]) -> None:
        try:
            operacion()
            print(f"  OK   permitido  {descripcion}")
        except OperationFailure as error:
            self.fallos.append(descripcion)
            print(f"  FALLO {descripcion}: se denegó ({error.code} {error})")
        except Exception as error:  # pragma: no cover - diagnóstico
            self.fallos.append(descripcion)
            print(f"  FALLO {descripcion}: {type(error).__name__}: {error}")

    def denegado(self, descripcion: str, operacion: Callable[[], object]) -> None:
        try:
            operacion()
            self.fallos.append(descripcion)
            print(f"  FALLO {descripcion}: se permitió una operación prohibida")
        except OperationFailure as error:
            if error.code in _CODIGOS_DENEGADO:
                print(f"  OK   denegado   {descripcion}")
            else:
                self.fallos.append(descripcion)
                print(f"  FALLO {descripcion}: error inesperado ({error.code} {error})")
        except Exception as error:  # pragma: no cover - diagnóstico
            self.fallos.append(descripcion)
            print(f"  FALLO {descripcion}: {type(error).__name__}: {error}")


def _change_stream(base: Database, coleccion: str) -> None:
    with base[coleccion].watch(max_await_time_ms=100) as stream:
        stream.try_next()


def _uri_root_con_credenciales(settings: Settings, usuario: str, password: str) -> str:
    return (
        f"mongodb://{quote_plus(usuario)}:{quote_plus(password)}@"
        f"{settings.mongodb_host}/?authSource={settings.mongodb_auth_source}"
        f"&replicaSet={settings.mongodb_replica_set}"
    )


def _cliente(uri: str) -> MongoClient:
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def _probar_servicios(
    verificador: Verificador,
    contexto: ContextoAplicacion,
    almacen_a: Almacen,
    almacen_b: Almacen,
) -> None:
    fabrica = contexto.fabrica
    global_db = contexto.settings.mongodb_global_db
    sufijo = uuid.uuid4().hex[:8]

    # Cliente ----------------------------------------------------------
    print("\n[cliente_app]")
    cliente = _cliente(fabrica.uri_cliente())
    base_cliente = cliente[global_db]
    verificador.permitido(
        "leer productos_global", lambda: base_cliente["productos_global"].find_one({})
    )
    verificador.permitido(
        "leer cupones_global", lambda: base_cliente["cupones_global"].find_one({})
    )
    verificador.permitido("leer almacenes", lambda: base_cliente["almacenes"].find_one({}))
    verificador.permitido(
        "insertar compra",
        lambda: base_cliente["compras"].insert_one(
            {
                "_id": f"rbac-{sufijo}",
                "rbac_prueba": True,
                "cliente_id": f"rbac-{sufijo}",
                "clave_idempotencia": f"rbac-{sufijo}",
            }
        ),
    )
    verificador.denegado("leer usuarios", lambda: base_cliente["usuarios"].find_one({}))
    verificador.denegado(
        "escribir productos_global",
        lambda: base_cliente["productos_global"].insert_one({"_id": f"rbac-{sufijo}"}),
    )
    verificador.denegado(
        "escribir almacenes",
        lambda: base_cliente["almacenes"].insert_one({"_id": f"rbac-{sufijo}"}),
    )
    cliente.close()

    # Administrador de la app -----------------------------------------
    print("\n[admin_app]")
    admin_app = _cliente(fabrica.uri_admin_app())
    base_admin = admin_app[global_db]
    verificador.permitido("leer almacenes", lambda: base_admin["almacenes"].find_one({}))
    verificador.permitido(
        "crear almacén temporal",
        lambda: base_admin["almacenes"].insert_one(
            {
                "_id": f"rbac-{sufijo}",
                "rbac_prueba": True,
                "nombre": f"RBAC {sufijo}",
                "nombre_normalizado": f"rbac {sufijo}",
                "db_name": f"rbac_{sufijo}",
                "mongo_user": f"rbac_{sufijo}_app",
                "estado": "activo",
            }
        ),
    )
    verificador.permitido(
        "leer productos_global", lambda: base_admin["productos_global"].find_one({})
    )
    verificador.denegado("leer usuarios", lambda: base_admin["usuarios"].find_one({}))
    verificador.denegado(
        "escribir productos_global",
        lambda: base_admin["productos_global"].insert_one({"_id": f"rbac-{sufijo}"}),
    )
    verificador.denegado("leer compras", lambda: base_admin["compras"].find_one({}))
    admin_app.close()

    # Autenticación ----------------------------------------------------
    print("\n[auth_service]")
    auth = _cliente(fabrica.uri_auth())
    base_auth = auth[global_db]
    verificador.permitido("leer usuarios", lambda: base_auth["usuarios"].find_one({}))
    verificador.permitido(
        "crear usuario temporal",
        lambda: base_auth["usuarios"].insert_one(
            {
                "_id": f"rbac-{sufijo}",
                "rbac_prueba": True,
                "nombre": "RBAC",
                "email": f"rbac-{sufijo}@example.com",
                "email_normalizado": f"rbac-{sufijo}@example.com",
                "password_hash": "x",
                "rol": "CLIENTE",
                "activo": True,
            }
        ),
    )
    verificador.denegado(
        "leer productos_global", lambda: base_auth["productos_global"].find_one({})
    )
    verificador.denegado("leer compras", lambda: base_auth["compras"].find_one({}))
    auth.close()

    # Validador --------------------------------------------------------
    print("\n[validador_catalogo]")
    validador = _cliente(fabrica.uri_validador())
    base_validador = validador[global_db]
    verificador.permitido(
        "leer productos_global", lambda: base_validador["productos_global"].find_one({})
    )
    verificador.permitido(
        "leer cupones_global", lambda: base_validador["cupones_global"].find_one({})
    )
    verificador.denegado(
        "escribir productos_global",
        lambda: base_validador["productos_global"].insert_one({"_id": f"rbac-{sufijo}"}),
    )
    verificador.denegado("leer usuarios", lambda: base_validador["usuarios"].find_one({}))
    validador.close()

    # Replicador de catálogo ------------------------------------------
    print("\n[replicador_catalogo]")
    catalogo = _cliente(fabrica.uri_catalogo())
    base_catalogo = catalogo[global_db]
    verificador.permitido(
        "escribir productos_global",
        lambda: base_catalogo["productos_global"].insert_one(
            {
                "_id": f"rbac-{sufijo}",
                "rbac_prueba": True,
                "producto_id": f"rbac-{sufijo}",
                "almacen_id": f"rbac-{sufijo}",
            }
        ),
    )
    verificador.permitido(
        "escribir sync_state_catalogo",
        lambda: base_catalogo["sync_state_catalogo"].update_one(
            {"_id": f"rbac-{sufijo}"},
            {"$set": {"rbac_prueba": True, "estado": "prueba"}},
            upsert=True,
        ),
    )
    verificador.permitido("leer almacenes", lambda: base_catalogo["almacenes"].find_one({}))
    verificador.denegado("leer usuarios", lambda: base_catalogo["usuarios"].find_one({}))
    verificador.denegado(
        "escribir compras",
        lambda: base_catalogo["compras"].insert_one({"_id": f"rbac-{sufijo}"}),
    )
    base_almacen_a = catalogo[almacen_a.db_name]
    verificador.permitido(
        "leer productos del almacén",
        lambda: base_almacen_a["productos"].find_one({}),
    )
    verificador.permitido(
        "abrir change stream de productos del almacén",
        lambda: _change_stream(base_almacen_a, "productos"),
    )
    verificador.denegado(
        "escribir productos del almacén",
        lambda: base_almacen_a["productos"].insert_one({"_id": f"rbac-{sufijo}"}),
    )
    verificador.denegado(
        "leer compras_almacen",
        lambda: base_almacen_a["compras_almacen"].find_one({}),
    )
    catalogo.close()

    # Proyector de compras --------------------------------------------
    print("\n[proyector_compras]")
    proyector = _cliente(fabrica.uri_compras())
    base_proyector = proyector[global_db]
    verificador.permitido("leer compras", lambda: base_proyector["compras"].find_one({}))
    verificador.permitido(
        "abrir change stream de compras",
        lambda: _change_stream(base_proyector, "compras"),
    )
    verificador.permitido(
        "escribir sync_state_compras",
        lambda: base_proyector["sync_state_compras"].update_one(
            {"_id": "global"},
            {"$set": {"rbac_prueba": True, "estado": "prueba"}},
            upsert=True,
        ),
    )
    verificador.denegado("leer usuarios", lambda: base_proyector["usuarios"].find_one({}))
    verificador.denegado(
        "escribir productos_global",
        lambda: base_proyector["productos_global"].insert_one({"_id": f"rbac-{sufijo}"}),
    )
    base_proyector_a = proyector[almacen_a.db_name]
    verificador.permitido(
        "escribir compras_almacen del almacén",
        lambda: base_proyector_a["compras_almacen"].insert_one(
            {"_id": f"rbac-{sufijo}", "rbac_prueba": True}
        ),
    )
    verificador.denegado(
        "leer productos del almacén",
        lambda: base_proyector_a["productos"].find_one({}),
    )
    proyector.close()

    # Usuario del almacén A -------------------------------------------
    print(f"\n[{almacen_a.mongo_user}]")
    almacen_cliente = _cliente(fabrica.uri_almacen(almacen_a))
    base_a = almacen_cliente[almacen_a.db_name]
    verificador.permitido(
        "escribir productos propios",
        lambda: base_a["productos"].insert_one(
            {
                "_id": f"rbac-{sufijo}",
                "almacen_id": almacen_a.almacen_id,
                "tipo_normalizado": "rbac",
                "nombre_normalizado": "rbac",
                "presentacion_normalizada": "rbac",
                "precio": 1,
            }
        ),
    )
    verificador.permitido(
        "actualizar productos propios",
        lambda: base_a["productos"].update_one({"_id": f"rbac-{sufijo}"}, {"$set": {"precio": 2}}),
    )
    verificador.permitido(
        "escribir cupones propios",
        lambda: base_a["cupones"].insert_one(
            {
                "_id": f"rbac-{sufijo}",
                "almacen_id": almacen_a.almacen_id,
                "codigo_normalizado": f"rbac-{sufijo}",
            }
        ),
    )
    verificador.permitido("leer compras_almacen", lambda: base_a["compras_almacen"].find_one({}))
    verificador.denegado(
        "escribir compras_almacen",
        lambda: base_a["compras_almacen"].insert_one({"_id": f"rbac-{sufijo}"}),
    )
    verificador.denegado(
        "leer el almacén B",
        lambda: almacen_cliente[almacen_b.db_name]["productos"].find_one({}),
    )
    verificador.denegado(
        "leer usuarios globales", lambda: almacen_cliente[global_db]["usuarios"].find_one({})
    )
    verificador.permitido(
        "eliminar productos propios",
        lambda: base_a["productos"].delete_one({"_id": f"rbac-{sufijo}"}),
    )
    verificador.permitido(
        "eliminar cupones propios",
        lambda: base_a["cupones"].delete_one({"_id": f"rbac-{sufijo}"}),
    )
    almacen_cliente.close()


def _limpiar(
    settings: Settings,
    almacenes: list[Almacen],
    root_user: str,
    root_password: str,
) -> None:
    root = MongoClient(
        _uri_root_con_credenciales(settings, root_user, root_password),
        serverSelectionTimeoutMS=5000,
    )
    try:
        base_global = root[settings.mongodb_global_db]
        for coleccion in ("compras", "almacenes", "usuarios", "productos_global"):
            base_global[coleccion].delete_many({"rbac_prueba": True})
        base_global["sync_state_catalogo"].delete_many({"rbac_prueba": True})
        base_global["sync_state_compras"].delete_many({"rbac_prueba": True})

        admin = root["admin"]
        for almacen in almacenes:
            try:
                root[almacen.db_name].command("dropDatabase")
            except OperationFailure as error:  # pragma: no cover - limpieza defensiva
                logger.warning("No se pudo borrar la base %s: %s", almacen.db_name, error)
            try:
                admin.command("dropUser", almacen.mongo_user)
            except OperationFailure as error:  # pragma: no cover
                logger.warning("No se pudo borrar el usuario %s: %s", almacen.mongo_user, error)
            base_global["almacenes"].delete_one({"_id": almacen.almacen_id})
    finally:
        root.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--conservar",
        action="store_true",
        help="No eliminar los almacenes temporales al terminar",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    configurar_logging(settings.log_level)
    if settings.modo_pruebas:
        print(
            "El modo de pruebas usa una única conexión y no crea usuarios nativos. "
            "Ejecuta este script con el docker-compose y las credenciales de servicio."
        )
        return 2

    import os

    root_user = os.getenv("MONGO_ROOT_USER", "root")
    root_password = os.getenv("MONGO_ROOT_PASSWORD", "")
    if not root_password:
        print("Falta MONGO_ROOT_PASSWORD para crear y limpiar los datos de prueba.")
        return 2

    contexto = construir_contexto(settings)
    almacenes: list[Almacen] = []
    verificador = Verificador()
    try:
        sufijo = uuid.uuid4().hex[:6]
        almacen_a = contexto.aprovisionamiento.crear_almacen(f"RBAC temporal A {sufijo}")
        almacenes.append(almacen_a)
        almacen_b = contexto.aprovisionamiento.crear_almacen(f"RBAC temporal B {sufijo}")
        almacenes.append(almacen_b)
        print(f"Almacenes temporales: {almacen_a.db_name}, {almacen_b.db_name}")

        _probar_servicios(verificador, contexto, almacen_a, almacen_b)
    finally:
        if args.conservar:
            print("Se conservan los almacenes temporales (--conservar).")
        else:
            _limpiar(settings, almacenes, root_user, root_password)
        contexto.cerrar()

    print()
    if verificador.fallos:
        print(f"RBAC con {len(verificador.fallos)} fallo(s):")
        for fallo in verificador.fallos:
            print(f"  - {fallo}")
        return 1
    print(
        "RBAC correcto: todas las operaciones permitidas y prohibidas "
        "se comportaron como se esperaba."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
