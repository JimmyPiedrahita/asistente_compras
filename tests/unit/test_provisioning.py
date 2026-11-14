"""Pruebas unitarias del aprovisionamiento de almacenes."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pymongo.errors import OperationFailure

from core.config import Settings
from core.errors import Conflicto, ServicioNoDisponible
from infrastructure.mongodb.provisioning import ServicioAprovisionamiento
from infrastructure.mongodb.uri import FabricaURIs
from models.almacenes import Almacen

SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"


def _settings(*, modo_pruebas: bool = False) -> Settings:
    return Settings(
        modo_pruebas=modo_pruebas,
        mongodb_uri="mongodb://localhost:27017" if modo_pruebas else "",
        mongodb_host="mongodb:27017",
        mongodb_replica_set="rs0",
        mongodb_auth_source="admin",
        mongodb_global_db="global_asistente_compras",
        mongodb_almacen_prefix="almacen_",
        mongodb_warehouse_secret=SECRETO,
        mongo_cliente_password="cliente-pass",
        mongo_admin_app_password="admin-app-pass",
        mongo_auth_password="auth-pass",
        mongo_validador_password="validador-pass",
        mongo_catalogo_password="catalogo-pass",
        mongo_compras_password="compras-pass",
        mongo_provisioner_password="provisioner-pass",
        admin_email="admin@example.com",
        admin_password="clave-segura",
    )


class _ColeccionFake:
    def __init__(self) -> None:
        self.indices: list[tuple[tuple, dict]] = []

    def create_index(self, *args: object, **kwargs: object) -> None:
        self.indices.append((args, kwargs))


class _BaseFake:
    def __init__(self) -> None:
        self.commands: list[tuple[str, tuple, dict]] = []
        self.colecciones: dict[str, _ColeccionFake] = {}
        self.errores: dict[str, OperationFailure] = {}

    def __getitem__(self, nombre: str) -> _ColeccionFake:
        return self.colecciones.setdefault(nombre, _ColeccionFake())

    def command(self, nombre: str, *args: object, **kwargs: object) -> None:
        self.commands.append((nombre, args, kwargs))
        if nombre in self.errores:
            raise self.errores[nombre]


class _ClienteFake:
    def __init__(self) -> None:
        self.bases: dict[str, _BaseFake] = {}

    def base(self, nombre: str) -> _BaseFake:
        return self.bases.setdefault(nombre, _BaseFake())


class _ConexionesFake:
    def __init__(self, cliente: _ClienteFake | None = None) -> None:
        self.cliente_fake = cliente or _ClienteFake()
        self.uris: list[str] = []

    def cliente(self, uri: str) -> _ClienteFake:
        self.uris.append(uri)
        return self.cliente_fake


class _RepoAlmacenesFake:
    def __init__(self) -> None:
        self.creados: list[Almacen] = []
        self.estados: list[tuple[str, str]] = []
        self._nombres: set[str] = set()

    def existe_nombre(self, nombre: str) -> bool:
        return nombre.casefold() in self._nombres

    def crear(self, almacen: Almacen) -> Almacen:
        self.creados.append(almacen)
        self._nombres.add(almacen.nombre.casefold())
        return almacen

    def actualizar_estado(self, almacen_id: str, estado: str) -> None:
        self.estados.append((almacen_id, estado))


def _servicio(
    *,
    settings: Settings | None = None,
    conexiones: _ConexionesFake | None = None,
    repo: _RepoAlmacenesFake | None = None,
) -> tuple[ServicioAprovisionamiento, _RepoAlmacenesFake, _ConexionesFake]:
    settings = settings or _settings()
    conexiones = conexiones or _ConexionesFake()
    repo = repo or _RepoAlmacenesFake()
    servicio = ServicioAprovisionamiento(
        settings,
        FabricaURIs(settings),
        conexiones,  # type: ignore[arg-type]
        repo,  # type: ignore[arg-type]
    )
    return servicio, repo, conexiones


class PruebasAprovisionamiento(unittest.TestCase):
    def test_crear_almacen_en_modo_pruebas(self) -> None:
        servicio, repo, conexiones = _servicio(settings=_settings(modo_pruebas=True))
        with patch.object(servicio, "_crear_indices") as indices:
            almacen = servicio.crear_almacen("  Almacén   Central ")

        self.assertEqual(almacen.nombre, "Almacén Central")
        self.assertEqual(almacen.estado, "activo")
        self.assertTrue(almacen.db_name.startswith("almacen_almacen_central_"))
        self.assertTrue(almacen.mongo_user.endswith("_app"))
        self.assertEqual(repo.creados, [almacen])
        self.assertEqual(repo.estados, [(almacen.almacen_id, "activo")])
        indices.assert_called_once_with(almacen)
        # En modo de pruebas no se abre la conexión del provisioner.
        self.assertEqual(conexiones.uris, [])

    def test_nombre_vacio_o_duplicado(self) -> None:
        servicio, repo, _ = _servicio(settings=_settings(modo_pruebas=True))
        with patch.object(servicio, "_crear_indices"):
            with self.assertRaises(Conflicto):
                servicio.crear_almacen("   ")
            servicio.crear_almacen("Central")
            with self.assertRaises(Conflicto):
                servicio.crear_almacen("central")
        self.assertEqual(len(repo.creados), 1)

    def test_error_marca_el_almacen_en_estado_error(self) -> None:
        servicio, repo, _ = _servicio(settings=_settings(modo_pruebas=True))
        with (
            patch.object(servicio, "_provisionar", side_effect=RuntimeError("fallo")),
            self.assertRaises(RuntimeError),
        ):
            servicio.crear_almacen("Central")

        almacen_id = repo.creados[0].almacen_id
        self.assertEqual(repo.estados, [(almacen_id, "error")])

    def test_provisiona_rol_usuario_y_privilegios(self) -> None:
        conexiones = _ConexionesFake()
        servicio, _, _ = _servicio(conexiones=conexiones)
        almacen = Almacen(
            almacen_id="a1",
            nombre="Central",
            db_name="almacen_central_a1",
            mongo_user="almacen_central_a1_app",
        )

        servicio._provisionar(almacen)

        base_almacen = conexiones.cliente_fake.bases[almacen.db_name]
        admin = conexiones.cliente_fake.bases["admin"]
        self.assertEqual([comando[0] for comando in base_almacen.commands], ["createRole"])
        self.assertEqual(
            [comando[0] for comando in admin.commands],
            ["createUser", "grantPrivilegesToRole", "grantPrivilegesToRole"],
        )

        _, args, kwargs = base_almacen.commands[0]
        self.assertEqual(args, ("rol_almacen",))
        privilegios = kwargs["privileges"]
        self.assertEqual(
            {privilegio["resource"]["collection"] for privilegio in privilegios},
            {"productos", "cupones", "compras_almacen"},
        )

        _, args, kwargs = admin.commands[0]
        self.assertEqual(args, (almacen.mongo_user,))
        self.assertIn("pwd", kwargs)
        self.assertEqual(
            kwargs["roles"],
            [{"role": "rol_almacen", "db": almacen.db_name}],
        )

        # Los privilegios del listener incluyen changeStream y la proyección.
        _, args, kwargs = admin.commands[1]
        self.assertEqual(args, ("rol_catalogo",))
        acciones = {
            accion for privilegio in kwargs["privileges"] for accion in privilegio["actions"]
        }
        self.assertEqual(acciones, {"find", "changeStream"})

        _, args, kwargs = admin.commands[2]
        self.assertEqual(args, ("rol_proyector",))
        self.assertEqual(kwargs["privileges"][0]["resource"]["collection"], "compras_almacen")

    def test_provisionamiento_idempotente(self) -> None:
        conexiones = _ConexionesFake()
        servicio, _, _ = _servicio(conexiones=conexiones)
        almacen = Almacen(
            almacen_id="a1",
            nombre="Central",
            db_name="almacen_central_a1",
            mongo_user="almacen_central_a1_app",
        )
        base_almacen = conexiones.cliente_fake.base(almacen.db_name)
        admin = conexiones.cliente_fake.base("admin")
        base_almacen.errores["createRole"] = OperationFailure("existe", code=51002)
        admin.errores["createUser"] = OperationFailure("existe", code=51002)
        admin.errores["grantPrivilegesToRole"] = OperationFailure("existe", code=51002)

        servicio._provisionar(almacen)

        self.assertEqual(
            [comando[0] for comando in base_almacen.commands],
            ["createRole", "updateRole"],
        )
        self.assertEqual(
            [comando[0] for comando in admin.commands],
            [
                "createUser",
                "updateUser",
                "grantPrivilegesToRole",
                "grantPrivilegesToRole",
            ],
        )

    def test_crear_indices_de_la_base_del_almacen(self) -> None:
        conexiones = _ConexionesFake()
        servicio, _, _ = _servicio(conexiones=conexiones)
        almacen = Almacen(
            almacen_id="a1",
            nombre="Central",
            db_name="almacen_central_a1",
            mongo_user="almacen_central_a1_app",
        )

        servicio._crear_indices(almacen)

        base = conexiones.cliente_fake.bases[almacen.db_name]
        self.assertEqual(len(base["productos"].indices), 3)
        self.assertEqual(len(base["cupones"].indices), 2)
        self.assertEqual(len(base["compras_almacen"].indices), 2)
        # El índice del cupón es único dentro del almacén.
        _, kwargs = base["cupones"].indices[0]
        self.assertTrue(kwargs.get("unique"))

    def test_error_de_conexion_al_crear_indices(self) -> None:
        class _ConexionesRojas(_ConexionesFake):
            def cliente(self, uri: str) -> _ClienteFake:
                raise OperationFailure("sin conexión")

        servicio, _, _ = _servicio(conexiones=_ConexionesRojas())
        almacen = Almacen(
            almacen_id="a1",
            nombre="Central",
            db_name="almacen_central_a1",
            mongo_user="almacen_central_a1_app",
        )
        with self.assertRaises(ServicioNoDisponible):
            servicio._crear_indices(almacen)


if __name__ == "__main__":
    unittest.main()
