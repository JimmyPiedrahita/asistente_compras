"""Persistencia MongoDB de la aplicación.

Todo vive en una única base de datos con colecciones claras:

- ``usuarios``: clientes, administradores de almacén y administrador de la app.
- ``almacenes``: almacenes creados por el administrador de la aplicación.
- ``productos``: catálogo, siempre asociado a un almacén.
- ``cupones``: cupones por almacén.
- ``compras``: comprobantes inmutables de compras completadas.

No se usan bases por almacén, proyecciones ni Change Streams.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from core.errors import Conflicto, NoEncontrado, ServicioNoDisponible
from core.logging import obtener_logger
from models.almacenes import Almacen
from models.cupones import Cupon, validar_porcentaje
from models.permisos import ADMINISTRADOR_ALMACEN, ADMINISTRADOR_APP, CLIENTE
from models.productos import Producto, validar_precio
from models.seguridad import (
    Usuario,
    es_email_valido,
    hashear_password,
)
from models.texto import normalizar_texto

from .cliente import ClienteMongo

logger = obtener_logger("asistente_compras.mongodb")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(valor: Any) -> str | None:
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, str):
        return valor
    return None


class RepositorioMongo:
    def __init__(
        self,
        uri: str,
        *,
        base_datos: str = "asistente_compras",
        timeout_ms: int = 5000,
        cliente: ClienteMongo | None = None,
    ) -> None:
        self._cliente = cliente or ClienteMongo(uri, timeout_ms)
        self._propio = cliente is None
        base = self._cliente.base(base_datos)
        self.usuarios: Collection = base["usuarios"]
        self.almacenes: Collection = base["almacenes"]
        self.productos: Collection = base["productos"]
        self.cupones: Collection = base["cupones"]
        self.compras: Collection = base["compras"]

    # Inicialización ----------------------------------------------------
    def inicializar(
        self,
        *,
        admin_email: str,
        admin_password: str,
        admin_nombre: str,
    ) -> None:
        try:
            self.usuarios.create_index("email_normalizado", unique=True)
            self.usuarios.create_index([("rol", ASCENDING), ("almacen_id", ASCENDING)])
            self.almacenes.create_index("nombre_normalizado", unique=True)
            self.productos.create_index(
                [("almacen_id", ASCENDING), ("tipo_normalizado", ASCENDING)]
            )
            self.productos.create_index([("tipo_normalizado", ASCENDING), ("precio", ASCENDING)])
            self.productos.create_index("presentacion_normalizada")
            self.cupones.create_index("codigo_normalizado", unique=True)
            self.cupones.create_index("almacen_id")
            self.compras.create_index(
                [("cliente_id", ASCENDING), ("clave_idempotencia", ASCENDING)],
                unique=True,
            )
            self.compras.create_index([("items.almacen_id", ASCENDING), ("fecha", ASCENDING)])
        except PyMongoError as error:  # pragma: no cover - depende de MongoDB
            raise ServicioNoDisponible("No se pudo inicializar MongoDB") from error

        if self.usuarios.count_documents({"rol": ADMINISTRADOR_APP}) == 0:
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

    # Usuarios ----------------------------------------------------------
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
            raise ServicioNoDisponible("No se pudo crear el usuario") from error
        return self._usuario(documento)

    def buscar_usuario_por_email(self, email: str) -> Usuario | None:
        email_norm = str(email or "").strip().lower()
        if not email_norm:
            return None
        try:
            documento = self.usuarios.find_one({"email_normalizado": email_norm})
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo consultar el usuario") from error
        return self._usuario(documento) if documento else None

    def obtener_usuario(self, usuario_id: str) -> Usuario | None:
        try:
            documento = self.usuarios.find_one({"_id": str(usuario_id)})
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo consultar el usuario") from error
        return self._usuario(documento) if documento else None

    def listar_administradores_almacen(self) -> list[Usuario]:
        try:
            documentos = list(self.usuarios.find({"rol": ADMINISTRADOR_ALMACEN}).sort("nombre", 1))
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudieron listar los administradores") from error
        return [self._usuario(documento) for documento in documentos]

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
            raise ServicioNoDisponible("No se pudieron actualizar las credenciales") from error
        if documento is None:
            raise NoEncontrado("Administrador de almacén no encontrado")
        return self._usuario(documento)

    # Almacenes ---------------------------------------------------------
    def crear_almacen(self, nombre: str) -> Almacen:
        nombre_limpio = " ".join(str(nombre or "").split())
        if not nombre_limpio:
            raise Conflicto("El nombre del almacén es obligatorio")
        documento = {
            "_id": uuid.uuid4().hex,
            "nombre": nombre_limpio,
            "nombre_normalizado": normalizar_texto(nombre_limpio),
            "creado_en": _ahora(),
        }
        try:
            self.almacenes.insert_one(documento)
        except DuplicateKeyError as error:
            raise Conflicto("Ya existe un almacén con ese nombre") from error
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo crear el almacén") from error
        return self._almacen(documento)

    def listar_almacenes(self) -> list[Almacen]:
        try:
            documentos = list(self.almacenes.find({}).sort("nombre", 1))
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudieron listar los almacenes") from error
        return [self._almacen(documento) for documento in documentos]

    def obtener_almacen(self, almacen_id: str) -> Almacen | None:
        try:
            documento = self.almacenes.find_one({"_id": str(almacen_id)})
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo consultar el almacén") from error
        return self._almacen(documento) if documento else None

    def contar_productos(self, almacen_id: str | None = None) -> int:
        filtro = {"almacen_id": str(almacen_id)} if almacen_id else {}
        try:
            return int(self.productos.count_documents(filtro))
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo contar el catálogo") from error

    # Productos ---------------------------------------------------------
    def crear_producto(
        self,
        *,
        almacen_id: str,
        tipo_producto: str,
        nombre: str,
        precio: Any,
        presentacion: str,
        marca_variedad: str | None = None,
    ) -> Producto:
        producto = Producto.crear(
            producto_id=uuid.uuid4().hex,
            almacen_id=almacen_id,
            tipo_producto=tipo_producto,
            nombre=nombre,
            precio=precio,
            presentacion=presentacion,
            marca_variedad=marca_variedad,
        )
        self._validar_presentacion(producto)
        documento = self._producto_documento(producto)
        try:
            self.productos.insert_one(documento)
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo guardar el producto") from error
        return producto

    def insertar_productos_validados(self, productos: Iterable[Producto]) -> int:
        documentos = [self._producto_documento(producto) for producto in productos]
        if not documentos:
            return 0
        try:
            self.productos.insert_many(documentos, ordered=True)
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo importar el catálogo") from error
        return len(documentos)

    def actualizar_producto(
        self,
        producto_id: str,
        almacen_id: str,
        cambios: dict[str, Any],
    ) -> Producto:
        actual = self.obtener_producto(producto_id)
        if actual is None or actual.almacen_id != str(almacen_id):
            raise NoEncontrado("Producto no encontrado")
        datos = {
            "tipo_producto": cambios.get("tipo_producto", actual.tipo_producto),
            "nombre": cambios.get("nombre", actual.nombre),
            "marca_variedad": cambios.get("marca_variedad", actual.marca_variedad),
            "precio": cambios.get("precio", actual.precio),
            "presentacion": cambios.get("presentacion", actual.presentacion),
        }
        actualizado = Producto.crear(
            producto_id=actual.producto_id,
            almacen_id=actual.almacen_id,
            **datos,
        )
        actualizado.creado_en = actual.creado_en
        self._validar_presentacion(actualizado, excluir_id=producto_id)
        documento = self._producto_documento(actualizado)
        documento.pop("_id", None)
        documento["creado_en"] = actual.creado_en or _ahora()
        documento["actualizado_en"] = _ahora()
        try:
            resultado = self.productos.update_one({"_id": producto_id}, {"$set": documento})
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo actualizar el producto") from error
        if resultado.matched_count != 1:
            raise NoEncontrado("Producto no encontrado")
        return actualizado

    def eliminar_producto(self, producto_id: str, almacen_id: str) -> None:
        try:
            resultado = self.productos.delete_one(
                {"_id": str(producto_id), "almacen_id": str(almacen_id)}
            )
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo eliminar el producto") from error
        if resultado.deleted_count != 1:
            raise NoEncontrado("Producto no encontrado")

    def obtener_producto(self, producto_id: str) -> Producto | None:
        try:
            documento = self.productos.find_one({"_id": str(producto_id)})
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo consultar el producto") from error
        return self._producto(documento) if documento else None

    def listar_productos(
        self,
        almacen_id: str,
        *,
        limite: int = 100,
        desplazamiento: int = 0,
    ) -> tuple[list[Producto], int]:
        filtro = {"almacen_id": str(almacen_id)}
        try:
            total = int(self.productos.count_documents(filtro))
            documentos = (
                self.productos.find(filtro)
                .sort([("tipo_normalizado", 1), ("nombre_normalizado", 1), ("_id", 1)])
                .skip(max(0, int(desplazamiento)))
                .limit(max(1, int(limite)))
            )
            return [self._producto(documento) for documento in documentos], total
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo listar el catálogo") from error

    def listar_todos_productos(self, almacen_id: str) -> list[Producto]:
        try:
            documentos = self.productos.find({"almacen_id": str(almacen_id)}).sort(
                [("nombre_normalizado", 1), ("_id", 1)]
            )
            return [self._producto(documento) for documento in documentos]
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo listar el catálogo") from error

    def presentaciones_del_tipo(
        self, tipo_normalizado: str, *, excluir_id: str | None = None
    ) -> set[str]:
        filtro: dict[str, Any] = {"tipo_normalizado": normalizar_texto(tipo_normalizado)}
        if excluir_id:
            filtro["_id"] = {"$ne": str(excluir_id)}
        try:
            valores = self.productos.distinct("presentacion_normalizada", filtro)
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo validar la presentación") from error
        return {str(valor) for valor in valores if str(valor).strip()}

    def buscar_por_tipos(self, tipos: Iterable[str]) -> list[tuple[Producto, Almacen]]:
        normalizados = sorted({normalizar_texto(tipo) for tipo in tipos if normalizar_texto(tipo)})
        if not normalizados:
            return []
        try:
            almacenes = {str(doc["_id"]): self._almacen(doc) for doc in self.almacenes.find({})}
            documentos = self.productos.find({"tipo_normalizado": {"$in": normalizados}})
            resultado: list[tuple[Producto, Almacen]] = []
            for documento in documentos:
                almacen = almacenes.get(str(documento.get("almacen_id")))
                if almacen is None:
                    continue
                resultado.append((self._producto(documento), almacen))
            return resultado
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo consultar el catálogo") from error

    # Cupones -----------------------------------------------------------
    def crear_cupon(self, *, codigo: str, almacen_id: str, porcentaje: Any) -> Cupon:
        codigo_limpio = " ".join(str(codigo or "").split()).upper()
        if not codigo_limpio:
            raise Conflicto("El código del cupón es obligatorio")
        try:
            porcentaje_validado = validar_porcentaje(porcentaje)
        except ValueError as error:
            raise Conflicto(str(error)) from error
        documento = {
            "_id": uuid.uuid4().hex,
            "codigo": codigo_limpio,
            "codigo_normalizado": normalizar_texto(codigo_limpio),
            "almacen_id": str(almacen_id),
            "porcentaje": porcentaje_validado,
            "creado_en": _ahora(),
        }
        try:
            self.cupones.insert_one(documento)
        except DuplicateKeyError as error:
            raise Conflicto("Ya existe un cupón con ese código") from error
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo crear el cupón") from error
        return self._cupon(documento)

    def listar_cupones(self, almacen_id: str) -> list[Cupon]:
        try:
            documentos = self.cupones.find({"almacen_id": str(almacen_id)}).sort("creado_en", -1)
            return [self._cupon(documento) for documento in documentos]
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudieron listar los cupones") from error

    def obtener_cupon_por_codigo(self, codigo: str) -> Cupon | None:
        try:
            documento = self.cupones.find_one({"codigo_normalizado": normalizar_texto(codigo)})
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo consultar el cupón") from error
        return self._cupon(documento) if documento else None

    def eliminar_cupon(self, cupon_id: str, almacen_id: str) -> None:
        try:
            resultado = self.cupones.delete_one(
                {"_id": str(cupon_id), "almacen_id": str(almacen_id)}
            )
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo eliminar el cupón") from error
        if resultado.deleted_count != 1:
            raise NoEncontrado("Cupón no encontrado")

    # Compras -----------------------------------------------------------
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
            if existente is None:  # pragma: no cover - condición de carrera extrema
                raise Conflicto("No se pudo registrar la compra") from None
            return existente, False
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudo registrar la compra") from error

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
            raise ServicioNoDisponible("No se pudo consultar la compra") from error

    def listar_compras_por_almacen(self, almacen_id: str) -> list[dict[str, Any]]:
        try:
            documentos = self.compras.find({"items.almacen_id": str(almacen_id)}).sort("fecha", -1)
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudieron consultar las compras") from error

        resultado: list[dict[str, Any]] = []
        for compra in documentos:
            items = [
                item
                for item in compra.get("items", [])
                if str(item.get("almacen_id")) == str(almacen_id)
            ]
            if not items:
                continue
            desglose = next(
                (
                    parte
                    for parte in compra.get("por_almacen", [])
                    if str(parte.get("almacen_id")) == str(almacen_id)
                ),
                {},
            )
            entrega = compra.get("datos_entrega", {})
            resultado.append(
                {
                    "compra_id": str(compra.get("_id")),
                    "fecha": _iso(compra.get("fecha")),
                    "cliente_nombre": compra.get("cliente_nombre", ""),
                    "telefono": entrega.get("telefono", ""),
                    "direccion": entrega.get("direccion", ""),
                    "ciudad": entrega.get("ciudad", ""),
                    "items": [
                        {
                            "producto_id": item.get("producto_id"),
                            "nombre": item.get("nombre"),
                            "marca_variedad": item.get("marca_variedad", ""),
                            "presentacion": item.get("presentacion"),
                            "precio_unitario": item.get("precio_unitario"),
                            "cantidad": item.get("cantidad"),
                            "importe": item.get("importe"),
                        }
                        for item in items
                    ],
                    "subtotal": desglose.get("subtotal", 0),
                    "cupon_codigo": desglose.get("cupon_codigo"),
                    "cupon_porcentaje": desglose.get("cupon_porcentaje"),
                    "descuento": desglose.get("descuento", 0),
                    "total": desglose.get("total", 0),
                }
            )
        return resultado

    def estadisticas_almacen(self, almacen_id: str) -> list[dict[str, Any]]:
        productos = self.listar_todos_productos(almacen_id)
        unidades = {producto.producto_id: 0 for producto in productos}
        try:
            compras = self.compras.find(
                {"items.almacen_id": str(almacen_id)},
                {"items": 1},
            )
            for compra in compras:
                for item in compra.get("items", []):
                    if str(item.get("almacen_id")) != str(almacen_id):
                        continue
                    producto_id = str(item.get("producto_id"))
                    if producto_id in unidades:
                        unidades[producto_id] += int(item.get("cantidad", 0))
        except PyMongoError as error:  # pragma: no cover
            raise ServicioNoDisponible("No se pudieron calcular las estadísticas") from error

        return [
            {
                "producto_id": producto.producto_id,
                "nombre": producto.nombre,
                "marca_variedad": producto.marca_variedad,
                "presentacion": producto.presentacion,
                "unidades_vendidas": unidades.get(producto.producto_id, 0),
            }
            for producto in productos
        ]

    # Conversión --------------------------------------------------------
    @staticmethod
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

    @staticmethod
    def _almacen(documento: dict[str, Any]) -> Almacen:
        return Almacen(
            almacen_id=str(documento.get("_id", "")),
            nombre=str(documento.get("nombre", "")),
            creado_en=documento.get("creado_en"),
        )

    @staticmethod
    def _producto(documento: dict[str, Any]) -> Producto:
        return Producto(
            producto_id=str(documento.get("_id", "")),
            almacen_id=str(documento.get("almacen_id", "")),
            tipo_producto=str(documento.get("tipo_producto", "")),
            nombre=str(documento.get("nombre", "")),
            marca_variedad=str(documento.get("marca_variedad", "")),
            precio=validar_precio(documento.get("precio")),
            presentacion=str(documento.get("presentacion", "")),
            creado_en=documento.get("creado_en"),
            actualizado_en=documento.get("actualizado_en"),
        )

    @staticmethod
    def _cupon(documento: dict[str, Any]) -> Cupon:
        return Cupon(
            cupon_id=str(documento.get("_id", "")),
            codigo=str(documento.get("codigo", "")),
            almacen_id=str(documento.get("almacen_id", "")),
            porcentaje=float(documento.get("porcentaje", 0)),
            creado_en=documento.get("creado_en"),
        )

    @staticmethod
    def _producto_documento(producto: Producto) -> dict[str, Any]:
        return {
            "_id": producto.producto_id,
            "almacen_id": producto.almacen_id,
            "tipo_producto": producto.tipo_producto,
            "tipo_normalizado": producto.tipo_normalizado,
            "nombre": producto.nombre,
            "nombre_normalizado": producto.nombre_normalizado,
            "marca_variedad": producto.marca_variedad,
            "marca_normalizada": normalizar_texto(producto.marca_variedad),
            "precio": producto.precio,
            "presentacion": producto.presentacion,
            "presentacion_normalizada": producto.presentacion_normalizada,
            "creado_en": producto.creado_en or _ahora(),
            "actualizado_en": producto.actualizado_en or _ahora(),
        }

    def _validar_presentacion(self, producto: Producto, *, excluir_id: str | None = None) -> None:
        existentes = self.presentaciones_del_tipo(producto.tipo_normalizado, excluir_id=excluir_id)
        if existentes and producto.presentacion_normalizada not in existentes:
            presentacion = sorted(existentes)[0]
            raise Conflicto(
                "La presentación debe ser la misma para todos los productos del tipo "
                f"'{producto.tipo_producto}'. Presentación estándar: {presentacion}"
            )

    # Ciclo de vida -----------------------------------------------------
    def ping(self) -> None:
        self._cliente.ping()

    def close(self) -> None:
        if self._propio:
            self._cliente.close()


__all__ = ["RepositorioMongo"]
