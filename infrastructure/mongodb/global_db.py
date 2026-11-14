"""Repositorios de la base global ``global_asistente_compras``.

Cada clase recibe una ``Database`` ya construida con la conexión de su rol.
Así el aislamiento de MongoDB se respeta también en el código: el repositorio
de usuarios no puede tocar catálogo y el catálogo de cliente no puede escribir
compras de administración.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from core.errors import Conflicto, NoEncontrado
from core.logging import obtener_logger
from models.almacenes import Almacen
from models.cupones import Cupon
from models.permisos import ADMINISTRADOR_ALMACEN, ADMINISTRADOR_APP, CLIENTE
from models.productos import Producto, validar_precio
from models.seguridad import Usuario, es_email_valido, hashear_password
from models.texto import normalizar_texto

from .errores import traducir_error

logger = obtener_logger("asistente_compras.mongodb.global")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(valor: Any) -> str | None:
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, str):
        return valor
    return None


def _usuario(documento: dict[str, Any]) -> Usuario:
    return Usuario(
        usuario_id=str(documento.get("_id", "")),
        nombre=str(documento.get("nombre", "")),
        email=str(documento.get("email", "")),
        password_hash=str(documento.get("password_hash", "")),
        rol=str(documento.get("rol", "")),
        almacen_id=documento.get("almacen_id"),
        telefono=documento.get("telefono"),
        direccion=documento.get("direccion"),
        ciudad=documento.get("ciudad"),
        autoriza_datos=bool(documento.get("autoriza_datos", False)),
        activo=bool(documento.get("activo", True)),
        creado_en=documento.get("creado_en"),
    )


def _almacen(documento: dict[str, Any]) -> Almacen:
    return Almacen(
        almacen_id=str(documento.get("_id", "")),
        nombre=str(documento.get("nombre", "")),
        creado_en=documento.get("creado_en"),
        db_name=str(documento.get("db_name", "")),
        mongo_user=str(documento.get("mongo_user", "")),
        estado=str(documento.get("estado", "activo")),
    )


def _producto(documento: dict[str, Any]) -> Producto:
    return Producto(
        producto_id=str(documento.get("producto_id") or documento.get("_id", "")),
        almacen_id=str(documento.get("almacen_id", "")),
        tipo_producto=str(documento.get("tipo_producto", "")),
        nombre=str(documento.get("nombre", "")),
        marca_variedad=str(documento.get("marca_variedad", "")),
        precio=validar_precio(documento.get("precio")),
        presentacion=str(documento.get("presentacion", "")),
        creado_en=documento.get("creado_en"),
        actualizado_en=documento.get("actualizado_en"),
    )


def _cupon(documento: dict[str, Any]) -> Cupon:
    return Cupon(
        cupon_id=str(documento.get("cupon_id") or documento.get("_id", "")),
        codigo=str(documento.get("codigo", "")),
        almacen_id=str(documento.get("almacen_id", "")),
        porcentaje=float(documento.get("porcentaje", 0)),
        creado_en=documento.get("creado_en"),
    )


class RepositorioUsuarios:
    """Usuarios de la aplicación. Conexión ``auth_service``."""

    def __init__(self, base: Database) -> None:
        self.usuarios: Collection = base["usuarios"]

    def inicializar(self) -> None:
        try:
            self.usuarios.create_index("email_normalizado", unique=True, name="email_unico")
            self.usuarios.create_index(
                [("rol", ASCENDING), ("almacen_id", ASCENDING)], name="rol_almacen"
            )
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise traducir_error(
                error, "No se pudo inicializar la colección de usuarios"
            ) from error

    def asegurar_admin(
        self,
        *,
        admin_email: str,
        admin_password: str,
        admin_nombre: str,
    ) -> None:
        if self.usuarios.count_documents({"rol": ADMINISTRADOR_APP}) > 0:
            return
        try:
            self.crear_usuario(
                nombre=admin_nombre,
                email=admin_email,
                password=admin_password,
                rol=ADMINISTRADOR_APP,
            )
            logger.info("Cuenta inicial del administrador de la aplicación creada")
        except Conflicto:
            logger.warning(
                "No se creó la cuenta inicial: el correo %s ya está registrado",
                admin_email,
            )

    def crear_usuario(
        self,
        *,
        nombre: str,
        email: str,
        password: str,
        rol: str,
        almacen_id: str | None = None,
        telefono: str | None = None,
        direccion: str | None = None,
        ciudad: str | None = None,
        autoriza_datos: bool = False,
    ) -> Usuario:
        nombre_limpio = " ".join(str(nombre or "").split())
        if not nombre_limpio:
            raise Conflicto("El nombre es obligatorio")
        email_norm = str(email or "").strip().lower()
        if not es_email_valido(email_norm):
            raise Conflicto("El correo electrónico no es válido")
        if not password or len(str(password)) < 6:
            raise Conflicto("La contraseña debe tener al menos 6 caracteres")
        if rol not in {CLIENTE, ADMINISTRADOR_ALMACEN, ADMINISTRADOR_APP}:
            raise Conflicto("Rol desconocido")
        if rol == CLIENTE and not autoriza_datos:
            raise Conflicto("Debes autorizar el tratamiento de tus datos personales")

        documento = {
            "_id": uuid.uuid4().hex,
            "nombre": nombre_limpio,
            "email": email_norm,
            "email_normalizado": email_norm,
            "password_hash": hashear_password(password),
            "rol": rol,
            "almacen_id": almacen_id,
            "telefono": (telefono or "").strip() or None,
            "direccion": (direccion or "").strip() or None,
            "ciudad": (ciudad or "").strip() or None,
            "autoriza_datos": bool(autoriza_datos),
            "activo": True,
            "creado_en": _ahora(),
        }
        try:
            self.usuarios.insert_one(documento)
        except DuplicateKeyError as error:
            raise Conflicto("Ya existe una cuenta con ese correo electrónico") from error
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo crear el usuario") from error
        return _usuario(documento)

    def buscar_usuario_por_email(self, email: str) -> Usuario | None:
        email_norm = str(email or "").strip().lower()
        if not email_norm:
            return None
        try:
            documento = self.usuarios.find_one({"email_normalizado": email_norm})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el usuario") from error
        return _usuario(documento) if documento else None

    def obtener_usuario(self, usuario_id: str) -> Usuario | None:
        try:
            documento = self.usuarios.find_one({"_id": str(usuario_id)})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el usuario") from error
        return _usuario(documento) if documento else None

    def listar_administradores_almacen(self) -> list[Usuario]:
        try:
            documentos = list(self.usuarios.find({"rol": ADMINISTRADOR_ALMACEN}).sort("nombre", 1))
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron listar los administradores") from error
        return [_usuario(documento) for documento in documentos]

    def actualizar_credenciales(
        self,
        usuario_id: str,
        *,
        email: str | None = None,
        password: str | None = None,
    ) -> Usuario:
        cambios: dict[str, Any] = {}
        if email is not None:
            email_norm = str(email).strip().lower()
            if not es_email_valido(email_norm):
                raise Conflicto("El correo electrónico no es válido")
            cambios["email"] = email_norm
            cambios["email_normalizado"] = email_norm
        if password is not None:
            if len(str(password)) < 6:
                raise Conflicto("La contraseña debe tener al menos 6 caracteres")
            cambios["password_hash"] = hashear_password(password)
        if not cambios:
            usuario = self.obtener_usuario(usuario_id)
            if usuario is None:
                raise NoEncontrado("Administrador no encontrado")
            return usuario
        try:
            documento = self.usuarios.find_one_and_update(
                {"_id": str(usuario_id), "rol": ADMINISTRADOR_ALMACEN},
                {"$set": cambios},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as error:
            raise Conflicto("Ya existe una cuenta con ese correo electrónico") from error
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron actualizar las credenciales") from error
        if documento is None:
            raise NoEncontrado("Administrador de almacén no encontrado")
        return _usuario(documento)


class RepositorioAlmacenes:
    """Metadata de almacenes y conteo global de productos. Conexión ``admin_app``."""

    def __init__(self, base: Database) -> None:
        self.almacenes: Collection = base["almacenes"]
        self.productos_global: Collection = base["productos_global"]

    def inicializar(self) -> None:
        try:
            self.almacenes.create_index("nombre_normalizado", unique=True, name="nombre_unico")
            self.almacenes.create_index("db_name", unique=True, name="db_unica")
            self.almacenes.create_index("mongo_user", unique=True, name="usuario_unico")
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(
                error, "No se pudo inicializar la colección de almacenes"
            ) from error

    def existe_nombre(self, nombre: str) -> bool:
        try:
            return (
                self.almacenes.count_documents(
                    {"nombre_normalizado": normalizar_texto(nombre)}, limit=1
                )
                > 0
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo validar el nombre del almacén") from error

    def crear(self, almacen: Almacen) -> Almacen:
        try:
            self.almacenes.insert_one(almacen.metadata())
        except DuplicateKeyError as error:
            raise Conflicto("Ya existe un almacén con ese nombre") from error
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo crear el almacén") from error
        return almacen

    def actualizar_estado(self, almacen_id: str, estado: str) -> None:
        try:
            self.almacenes.update_one({"_id": str(almacen_id)}, {"$set": {"estado": estado}})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo actualizar el estado del almacén") from error

    def listar(self) -> list[Almacen]:
        try:
            documentos = list(self.almacenes.find({}).sort("nombre", 1))
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron listar los almacenes") from error
        return [_almacen(documento) for documento in documentos]

    def obtener(self, almacen_id: str) -> Almacen | None:
        try:
            documento = self.almacenes.find_one({"_id": str(almacen_id)})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el almacén") from error
        return _almacen(documento) if documento else None

    def contar_productos(self, almacen_id: str | None = None) -> int:
        filtro = {"almacen_id": str(almacen_id)} if almacen_id else {}
        try:
            return int(self.productos_global.count_documents(filtro))
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo contar el catálogo") from error


class RepositorioCatalogoGlobal:
    """Catálogo de solo lectura para clientes. Conexión ``cliente_app``."""

    def __init__(self, base: Database) -> None:
        self.productos: Collection = base["productos_global"]
        self.cupones: Collection = base["cupones_global"]
        self.almacenes: Collection = base["almacenes"]

    def contar_productos(self) -> int:
        try:
            return int(self.productos.count_documents({}))
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo contar el catálogo") from error

    def obtener_producto(self, producto_id: str) -> Producto | None:
        try:
            documento = self.productos.find_one({"producto_id": str(producto_id)})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el producto") from error
        return _producto(documento) if documento else None

    def obtener_almacen(self, almacen_id: str) -> Almacen | None:
        try:
            documento = self.almacenes.find_one({"_id": str(almacen_id)})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el almacén") from error
        return _almacen(documento) if documento else None

    def obtener_cupon_por_codigo(self, codigo: str) -> Cupon | None:
        try:
            documento = self.cupones.find_one({"codigo_normalizado": normalizar_texto(codigo)})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el cupón") from error
        return _cupon(documento) if documento else None

    def buscar_por_tipos(self, tipos: Iterable[str]) -> list[tuple[Producto, Almacen]]:
        normalizados = sorted({normalizar_texto(tipo) for tipo in tipos if normalizar_texto(tipo)})
        if not normalizados:
            return []
        try:
            almacenes = {
                str(documento["_id"]): _almacen(documento) for documento in self.almacenes.find({})
            }
            documentos = self.productos.find({"tipo_normalizado": {"$in": normalizados}})
            resultado: list[tuple[Producto, Almacen]] = []
            for documento in documentos:
                almacen = almacenes.get(str(documento.get("almacen_id")))
                if almacen is None:
                    continue
                resultado.append((_producto(documento), almacen))
            return resultado
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar el catálogo") from error


class RepositorioComprasGlobal:
    """Compras globales del cliente. Conexión ``cliente_app``."""

    def __init__(self, base: Database) -> None:
        self.compras: Collection = base["compras"]

    def inicializar(self) -> None:
        try:
            self.compras.create_index(
                [("cliente_id", ASCENDING), ("clave_idempotencia", ASCENDING)],
                unique=True,
                name="idempotencia",
            )
            self.compras.create_index(
                [("items.almacen_id", ASCENDING), ("fecha", ASCENDING)],
                name="almacen_fecha",
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo inicializar la colección de compras") from error

    def crear_compra(
        self,
        documento: dict[str, Any],
        *,
        cliente_id: str,
        clave_idempotencia: str,
    ) -> tuple[dict[str, Any], bool]:
        datos = dict(documento)
        datos["cliente_id"] = str(cliente_id)
        datos["clave_idempotencia"] = str(clave_idempotencia)
        datos["fecha"] = _ahora()
        try:
            self.compras.insert_one(datos)
            return datos, True
        except DuplicateKeyError:
            existente = self.compras.find_one(
                {
                    "cliente_id": str(cliente_id),
                    "clave_idempotencia": str(clave_idempotencia),
                }
            )
            if existente is None:  # pragma: no cover - carrera extrema
                raise Conflicto("No se pudo registrar la compra") from None
            return existente, False
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo registrar la compra") from error

    def obtener_compra_por_clave(
        self, cliente_id: str, clave_idempotencia: str
    ) -> dict[str, Any] | None:
        try:
            return self.compras.find_one(
                {
                    "cliente_id": str(cliente_id),
                    "clave_idempotencia": str(clave_idempotencia),
                }
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar la compra") from error

    def listar_compras(self) -> list[dict[str, Any]]:
        try:
            return list(self.compras.find({}))
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron listar las compras") from error

    def obtener_compra(self, compra_id: str) -> dict[str, Any] | None:
        try:
            return self.compras.find_one({"_id": str(compra_id)})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo consultar la compra") from error


class RepositorioValidacion:
    """Validaciones globales de solo lectura. Conexión ``validador_catalogo``."""

    def __init__(self, base: Database) -> None:
        self.productos: Collection = base["productos_global"]
        self.cupones: Collection = base["cupones_global"]

    def presentaciones_del_tipo(
        self, tipo_normalizado: str, *, excluir_id: str | None = None
    ) -> set[str]:
        filtro: dict[str, Any] = {"tipo_normalizado": normalizar_texto(tipo_normalizado)}
        if excluir_id:
            filtro["producto_id"] = {"$ne": str(excluir_id)}
        try:
            valores = self.productos.distinct("presentacion_normalizada", filtro)
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo validar la presentación") from error
        return {str(valor) for valor in valores if str(valor).strip()}

    def existe_cupon(self, codigo_normalizado: str) -> bool:
        try:
            return (
                self.cupones.count_documents(
                    {"codigo_normalizado": normalizar_texto(codigo_normalizado)}, limit=1
                )
                > 0
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo validar el cupón") from error


class RepositorioReplicaCatalogo:
    """Escritura de la réplica global. Conexión ``replicador_catalogo``."""

    def __init__(self, base: Database) -> None:
        self.productos: Collection = base["productos_global"]
        self.cupones: Collection = base["cupones_global"]
        self.estado: Collection = base["sync_state_catalogo"]
        self.almacenes: Collection = base["almacenes"]

    def listar_almacenes(self) -> list[Almacen]:
        try:
            documentos = list(self.almacenes.find({}).sort("nombre", 1))
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron listar los almacenes") from error
        return [_almacen(documento) for documento in documentos]

    def upsert_producto(self, almacen: Almacen, documento: dict[str, Any]) -> None:
        producto_id = str(documento.get("_id") or documento.get("producto_id"))
        global_id = f"{almacen.almacen_id}:{producto_id}"
        datos = {
            "_id": global_id,
            "producto_id": producto_id,
            "almacen_id": almacen.almacen_id,
            "almacen_nombre": almacen.nombre,
            "tipo_producto": documento.get("tipo_producto", ""),
            "tipo_normalizado": documento.get("tipo_normalizado", ""),
            "nombre": documento.get("nombre", ""),
            "nombre_normalizado": documento.get("nombre_normalizado", ""),
            "marca_variedad": documento.get("marca_variedad", ""),
            "marca_normalizada": documento.get("marca_normalizada", ""),
            "precio": documento.get("precio"),
            "presentacion": documento.get("presentacion", ""),
            "presentacion_normalizada": documento.get("presentacion_normalizada", ""),
            "creado_en": documento.get("creado_en"),
            "actualizado_en": documento.get("actualizado_en"),
            "sincronizado_en": _ahora(),
        }
        try:
            self.productos.replace_one({"_id": global_id}, datos, upsert=True)
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo replicar el producto") from error

    def eliminar_producto(self, almacen_id: str, producto_id: str) -> None:
        try:
            self.productos.delete_one({"_id": f"{almacen_id}:{producto_id}"})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo eliminar el producto replicado") from error

    def upsert_cupon(self, almacen: Almacen, documento: dict[str, Any]) -> None:
        cupon_id = str(documento.get("_id") or documento.get("cupon_id"))
        global_id = f"{almacen.almacen_id}:{cupon_id}"
        datos = {
            "_id": global_id,
            "cupon_id": cupon_id,
            "almacen_id": almacen.almacen_id,
            "almacen_nombre": almacen.nombre,
            "codigo": documento.get("codigo", ""),
            "codigo_normalizado": documento.get("codigo_normalizado", ""),
            "porcentaje": documento.get("porcentaje"),
            "creado_en": documento.get("creado_en"),
            "sincronizado_en": _ahora(),
        }
        try:
            self.cupones.replace_one({"_id": global_id}, datos, upsert=True)
        except DuplicateKeyError as error:
            logger.warning(
                "Cupón %s del almacén %s no replicado: código duplicado en la base global",
                datos["codigo"],
                almacen.almacen_id,
            )
            raise Conflicto("Ya existe un cupón con ese código en la aplicación") from error
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo replicar el cupón") from error

    def eliminar_cupon(self, almacen_id: str, cupon_id: str) -> None:
        try:
            self.cupones.delete_one({"_id": f"{almacen_id}:{cupon_id}"})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo eliminar el cupón replicado") from error

    def eliminar_productos_obsoletos(self, almacen_id: str, vigentes: set[str]) -> int:
        filtro: dict[str, Any] = {"almacen_id": str(almacen_id)}
        if vigentes:
            filtro["producto_id"] = {"$nin": sorted(vigentes)}
        try:
            return int(self.productos.delete_many(filtro).deleted_count)
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron limpiar productos obsoletos") from error

    def eliminar_cupones_obsoletos(self, almacen_id: str, vigentes: set[str]) -> int:
        filtro: dict[str, Any] = {"almacen_id": str(almacen_id)}
        if vigentes:
            filtro["cupon_id"] = {"$nin": sorted(vigentes)}
        try:
            return int(self.cupones.delete_many(filtro).deleted_count)
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudieron limpiar cupones obsoletos") from error

    def guardar_token(
        self,
        almacen_id: str,
        coleccion: str,
        token: Any,
        *,
        estado: str = "activo",
    ) -> None:
        try:
            self.estado.update_one(
                {"_id": str(almacen_id)},
                {
                    "$set": {
                        "estado": estado,
                        f"resume_tokens.{coleccion}": token,
                        "ultima_sincronizacion": _ahora(),
                        "actualizado_en": _ahora(),
                    }
                },
                upsert=True,
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo guardar el estado de replicación") from error

    def leer_tokens(self, almacen_id: str) -> dict[str, Any]:
        try:
            documento = self.estado.find_one({"_id": str(almacen_id)})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo leer el estado de replicación") from error
        if not documento:
            return {}
        tokens = documento.get("resume_tokens") or {}
        return {str(coleccion): token for coleccion, token in tokens.items() if token is not None}

    def reiniciar_tokens(self, almacen_id: str, *, estado: str = "reconciliado") -> None:
        try:
            self.estado.update_one(
                {"_id": str(almacen_id)},
                {
                    "$unset": {"resume_tokens": ""},
                    "$set": {
                        "estado": estado,
                        "ultima_sincronizacion": _ahora(),
                        "actualizado_en": _ahora(),
                    },
                },
                upsert=True,
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo reiniciar el estado de replicación") from error

    def marcar_estado(self, almacen_id: str, estado: str, evento: str = "") -> None:
        try:
            self.estado.update_one(
                {"_id": str(almacen_id)},
                {
                    "$set": {
                        "estado": estado,
                        "ultimo_evento": evento,
                        "actualizado_en": _ahora(),
                    }
                },
                upsert=True,
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo marcar el estado de replicación") from error


class RepositorioEstadoCompras:
    """Estado del proyector de compras. Conexión ``proyector_compras``."""

    def __init__(self, base: Database) -> None:
        self.estado: Collection = base["sync_state_compras"]

    def guardar_token(self, token: Any, *, estado: str = "activo") -> None:
        try:
            self.estado.update_one(
                {"_id": "global"},
                {
                    "$set": {
                        "estado": estado,
                        "resume_token": token,
                        "ultima_sincronizacion": _ahora(),
                        "actualizado_en": _ahora(),
                    }
                },
                upsert=True,
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo guardar el estado del proyector") from error

    def leer_token(self) -> Any | None:
        try:
            documento = self.estado.find_one({"_id": "global"})
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo leer el estado del proyector") from error
        return documento.get("resume_token") if documento else None

    def marcar_estado(self, estado: str, evento: str = "") -> None:
        try:
            self.estado.update_one(
                {"_id": "global"},
                {
                    "$set": {
                        "estado": estado,
                        "ultimo_evento": evento,
                        "actualizado_en": _ahora(),
                    }
                },
                upsert=True,
            )
        except PyMongoError as error:  # pragma: no cover
            raise traducir_error(error, "No se pudo marcar el estado del proyector") from error


__all__ = [
    "RepositorioAlmacenes",
    "RepositorioCatalogoGlobal",
    "RepositorioComprasGlobal",
    "RepositorioEstadoCompras",
    "RepositorioReplicaCatalogo",
    "RepositorioUsuarios",
    "RepositorioValidacion",
    "_iso",
]
