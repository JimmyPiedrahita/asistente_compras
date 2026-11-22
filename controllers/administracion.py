"""Funciones del administrador de la aplicación y del administrador de almacén."""

from __future__ import annotations

import csv
import io
import re
import uuid
from typing import Any
from urllib.parse import urlparse

from core.errors import NoEncontrado, NoPermitido, ServicioNoDisponible, SolicitudInvalida
from core.logging import obtener_logger
from infrastructure.imagenes import ServicioImagenesProducto
from infrastructure.mongodb.almacen import RepositorioAlmacen
from infrastructure.mongodb.global_db import RepositorioAlmacenes, RepositorioUsuarios
from infrastructure.mongodb.provisioning import ServicioAprovisionamiento
from infrastructure.mongodb.validacion import ServicioValidacion
from models.permisos import ADMINISTRADOR_ALMACEN
from models.productos import Producto

from .sesiones import Sesion

logger = obtener_logger("asistente_compras.administracion")

_CABECERAS_OBLIGATORIAS = {"tipo_producto", "nombre", "precio", "presentacion"}
_CABECERAS_PERMITIDAS = _CABECERAS_OBLIGATORIAS | {"marca_variedad", "imagen_url"}
_PRECIO_VALIDO = re.compile(r"^\d+(?:\.\d+)?$")


class ControladorAdminApp:
    """Administrador de la aplicación: almacenes y sus administradores."""

    def __init__(
        self,
        almacenes: RepositorioAlmacenes,
        usuarios: RepositorioUsuarios,
        aprovisionamiento: ServicioAprovisionamiento,
    ) -> None:
        self.almacenes = almacenes
        self.usuarios = usuarios
        self.aprovisionamiento = aprovisionamiento

    def crear_almacen(self, nombre: str) -> dict[str, Any]:
        almacen = self.aprovisionamiento.crear_almacen(nombre)
        return {**almacen.publico(), "productos": 0}

    def listar_almacenes(self) -> list[dict[str, Any]]:
        return [
            {
                **almacen.publico(),
                "productos": self.almacenes.contar_productos(almacen.almacen_id),
            }
            for almacen in self.almacenes.listar()
        ]

    def crear_admin_almacen(
        self,
        *,
        nombre: str,
        email: str,
        password: str,
        almacen_id: str,
    ) -> dict[str, Any]:
        almacen = self.almacenes.obtener(almacen_id)
        if almacen is None:
            raise NoEncontrado("Almacén no encontrado")
        usuario = self.usuarios.crear_usuario(
            nombre=nombre,
            email=email,
            password=password,
            rol=ADMINISTRADOR_ALMACEN,
            almacen_id=almacen.almacen_id,
        )
        return {**usuario.publico(), "almacen_nombre": almacen.nombre}

    def listar_admins_almacen(self) -> list[dict[str, Any]]:
        almacenes = {a.almacen_id: a.nombre for a in self.almacenes.listar()}
        return [
            {
                **usuario.publico(),
                "almacen_nombre": almacenes.get(usuario.almacen_id or "", ""),
            }
            for usuario in self.usuarios.listar_administradores_almacen()
        ]

    def actualizar_credenciales(
        self,
        usuario_id: str,
        *,
        email: str | None,
        password: str | None,
    ) -> dict[str, Any]:
        if email is None and password is None:
            raise SolicitudInvalida("Indica el correo o la contraseña que deseas actualizar")
        usuario = self.usuarios.actualizar_credenciales(usuario_id, email=email, password=password)
        return usuario.publico()


class ControladorAdminAlmacen:
    """Administrador de almacén: productos, cupones, CSV, compras y estadísticas."""

    def __init__(
        self,
        repositorio: RepositorioAlmacen,
        validador: ServicioValidacion,
        *,
        max_csv_bytes: int = 1_000_000,
        imagenes: ServicioImagenesProducto | None = None,
    ) -> None:
        self.repo = repositorio
        self.validador = validador
        self.max_csv_bytes = int(max_csv_bytes)
        self.imagenes = imagenes

    def _almacen_de(self, sesion: Sesion) -> str:
        if not sesion.almacen_id:
            raise NoEncontrado("La cuenta no tiene un almacén asignado")
        if str(sesion.almacen_id) != self.repo.almacen_id:
            raise NoPermitido("no puedes operar sobre otro almacén", rol=sesion.rol)
        return self.repo.almacen_id

    @property
    def max_imagen_bytes(self) -> int:
        return self.imagenes.max_bytes if self.imagenes is not None else 2_000_000

    def _servicio_imagenes(self) -> ServicioImagenesProducto:
        if self.imagenes is None or not self.imagenes.configurado:
            raise ServicioNoDisponible("La carga de imágenes no está configurada en el servidor")
        return self.imagenes

    # Productos ---------------------------------------------------------
    def listar_productos(self, sesion: Sesion) -> list[dict[str, Any]]:
        self._almacen_de(sesion)
        return [producto.publico() for producto in self.repo.listar_todos_productos()]

    def crear_producto(self, sesion: Sesion, datos: dict[str, Any]) -> dict[str, Any]:
        almacen_id = self._almacen_de(sesion)
        try:
            producto = Producto.crear(
                producto_id=uuid.uuid4().hex,
                almacen_id=almacen_id,
                tipo_producto=str(datos.get("tipo_producto") or ""),
                nombre=str(datos.get("nombre") or ""),
                precio=datos.get("precio"),
                presentacion=str(datos.get("presentacion") or ""),
                marca_variedad=str(datos.get("marca_variedad") or ""),
            )
        except ValueError as error:
            raise SolicitudInvalida(str(error)) from error
        locales = self.repo.presentaciones_del_tipo(producto.tipo_normalizado)
        self.validador.validar_presentacion(producto, locales=locales)
        self.repo.insertar_producto(producto)
        return producto.publico()

    def actualizar_producto(
        self, sesion: Sesion, producto_id: str, cambios: dict[str, Any]
    ) -> dict[str, Any]:
        almacen_id = self._almacen_de(sesion)
        actual = self.repo.obtener_producto(producto_id)
        if actual is None:
            raise NoEncontrado("Producto no encontrado")
        datos = {
            "tipo_producto": cambios.get("tipo_producto", actual.tipo_producto),
            "nombre": cambios.get("nombre", actual.nombre),
            "marca_variedad": cambios.get("marca_variedad", actual.marca_variedad),
            "precio": cambios.get("precio", actual.precio),
            "presentacion": cambios.get("presentacion", actual.presentacion),
        }
        try:
            actualizado = Producto.crear(
                producto_id=actual.producto_id,
                almacen_id=almacen_id,
                **datos,
            )
        except ValueError as error:
            raise SolicitudInvalida(str(error)) from error
        actualizado.creado_en = actual.creado_en
        actualizado.imagen_url = actual.imagen_url
        actualizado.imagen_public_id = actual.imagen_public_id
        locales = self.repo.presentaciones_del_tipo(actualizado.tipo_normalizado)
        self.validador.validar_presentacion(actualizado, locales=locales, excluir_id=producto_id)
        self.repo.guardar_producto(actualizado)
        return actualizado.publico()

    def subir_imagen_producto(
        self,
        sesion: Sesion,
        producto_id: str,
        contenido: bytes,
    ) -> dict[str, Any]:
        almacen_id = self._almacen_de(sesion)
        producto = self.repo.obtener_producto(producto_id)
        if producto is None:
            raise NoEncontrado("Producto no encontrado")
        servicio = self._servicio_imagenes()

        nueva = servicio.subir(
            almacen_id=almacen_id,
            producto_id=producto.producto_id,
            contenido=contenido,
        )
        anterior = producto.imagen_public_id
        producto.imagen_url = nueva["imagen_url"]
        producto.imagen_public_id = nueva["imagen_public_id"]
        try:
            self.repo.guardar_producto(producto)
        except Exception:
            # Si MongoDB no guarda la referencia, se retira el activo nuevo
            # para no dejar huérfanos en Cloudinary.
            try:
                servicio.eliminar(nueva["imagen_public_id"])
            except Exception:  # pragma: no cover - limpieza defensiva
                logger.warning("No se pudo limpiar la imagen nueva en Cloudinary")
            raise
        if anterior and anterior != producto.imagen_public_id:
            try:
                servicio.eliminar(anterior)
            except Exception:  # pragma: no cover - el producto ya quedó actualizado
                logger.warning("No se pudo eliminar la imagen anterior %s", anterior)
        return producto.publico()

    def eliminar_imagen_producto(self, sesion: Sesion, producto_id: str) -> dict[str, Any]:
        self._almacen_de(sesion)
        producto = self.repo.obtener_producto(producto_id)
        if producto is None:
            raise NoEncontrado("Producto no encontrado")
        if not producto.imagen_public_id:
            producto.imagen_url = ""
            producto.imagen_public_id = ""
            self.repo.guardar_producto(producto)
            return producto.publico()

        public_id = producto.imagen_public_id
        producto.imagen_url = ""
        producto.imagen_public_id = ""
        self.repo.guardar_producto(producto)
        try:
            self._servicio_imagenes().eliminar(public_id)
        except Exception:
            logger.warning("No se pudo eliminar la imagen %s de Cloudinary", public_id)
        return producto.publico()

    def eliminar_producto(self, sesion: Sesion, producto_id: str) -> None:
        self._almacen_de(sesion)
        producto = self.repo.obtener_producto(producto_id)
        if producto is None:
            raise NoEncontrado("Producto no encontrado")
        self.repo.eliminar_producto(producto_id)
        if producto.imagen_public_id:
            try:
                self._servicio_imagenes().eliminar(producto.imagen_public_id)
            except Exception:
                logger.warning(
                    "No se pudo eliminar la imagen %s del producto eliminado",
                    producto.imagen_public_id,
                )

    def importar_csv(self, sesion: Sesion, contenido: str) -> dict[str, Any]:
        almacen_id = self._almacen_de(sesion)
        if not isinstance(contenido, str) or not contenido.strip():
            raise SolicitudInvalida("El archivo CSV está vacío")
        if len(contenido.encode("utf-8")) > self.max_csv_bytes:
            raise SolicitudInvalida(
                f"El archivo supera el tamaño máximo de {self.max_csv_bytes} bytes"
            )

        texto = contenido.lstrip("\ufeff")
        try:
            filas = list(csv.reader(io.StringIO(texto)))
        except csv.Error as error:
            raise SolicitudInvalida(f"No se pudo leer el archivo CSV: {error}") from error
        filas = [fila for fila in filas if any(campo.strip() for campo in fila)]
        if not filas:
            raise SolicitudInvalida("El archivo CSV está vacío")

        cabeceras = [campo.strip().lower() for campo in filas[0]]
        if len(set(cabeceras)) != len(cabeceras):
            raise SolicitudInvalida("El archivo CSV tiene columnas repetidas")
        if "almacen" in cabeceras:
            raise SolicitudInvalida(
                "El archivo no debe incluir una columna 'almacen': "
                "el almacén se asigna automáticamente"
            )
        faltantes = _CABECERAS_OBLIGATORIAS - set(cabeceras)
        if faltantes:
            raise SolicitudInvalida(
                "Faltan encabezados obligatorios: " + ", ".join(sorted(faltantes))
            )
        sobrantes = set(cabeceras) - _CABECERAS_PERMITIDAS
        if sobrantes:
            raise SolicitudInvalida("Columnas no permitidas: " + ", ".join(sorted(sobrantes)))
        indices = {cabecera: posicion for posicion, cabecera in enumerate(cabeceras)}

        def campo(fila_actual: list[str], nombre: str) -> str:
            posicion = indices.get(nombre)
            if posicion is None or posicion >= len(fila_actual):
                return ""
            return fila_actual[posicion].strip()

        errores: list[dict[str, Any]] = []
        productos: list[Producto] = []
        presentaciones: dict[str, str] = {}
        existentes: dict[str, set[str]] = {}

        for numero, fila in enumerate(filas[1:], start=2):
            if len(fila) != len(cabeceras):
                errores.append({"fila": numero, "mensaje": "La fila no tiene todas las columnas"})
                continue

            tipo = campo(fila, "tipo_producto")
            nombre = campo(fila, "nombre")
            marca = campo(fila, "marca_variedad")
            precio_crudo = campo(fila, "precio")
            presentacion = campo(fila, "presentacion")
            imagen_url = campo(fila, "imagen_url")

            if not tipo:
                errores.append({"fila": numero, "mensaje": "tipo_producto es obligatorio"})
                continue
            if not nombre:
                errores.append({"fila": numero, "mensaje": "nombre es obligatorio"})
                continue
            if not presentacion:
                errores.append({"fila": numero, "mensaje": "presentacion es obligatoria"})
                continue
            if not _PRECIO_VALIDO.match(precio_crudo):
                errores.append(
                    {
                        "fila": numero,
                        "mensaje": (
                            "precio debe ser mayor que cero, sin símbolos de moneda "
                            "ni separadores de miles, usando punto para decimales"
                        ),
                    }
                )
                continue
            if imagen_url:
                url = urlparse(imagen_url)
                if url.scheme not in {"http", "https"} or not url.netloc:
                    errores.append(
                        {
                            "fila": numero,
                            "mensaje": "imagen_url debe ser una URL HTTP o HTTPS válida",
                        }
                    )
                    continue

            tipo_norm = " ".join(tipo.casefold().split())
            if tipo_norm not in existentes:
                existentes[tipo_norm] = self.validador.presentaciones_del_tipo(
                    tipo_norm, locales=self.repo.presentaciones_del_tipo(tipo_norm)
                )
            presentacion_norm = " ".join(presentacion.casefold().split())
            estandar_existente = sorted(existentes[tipo_norm]) if existentes[tipo_norm] else []
            if estandar_existente and presentacion_norm not in estandar_existente:
                errores.append(
                    {
                        "fila": numero,
                        "mensaje": (
                            "presentacion no coincide con la presentación estándar del tipo "
                            f"'{tipo}': {estandar_existente[0]}"
                        ),
                    }
                )
                continue
            if tipo_norm in presentaciones and presentaciones[tipo_norm] != presentacion_norm:
                errores.append(
                    {
                        "fila": numero,
                        "mensaje": (
                            "todas las filas del mismo tipo_producto deben usar "
                            "la misma presentación"
                        ),
                    }
                )
                continue
            presentaciones.setdefault(tipo_norm, presentacion_norm)

            try:
                producto = Producto.crear(
                    producto_id=uuid.uuid4().hex,
                    almacen_id=almacen_id,
                    tipo_producto=tipo,
                    nombre=nombre,
                    precio=precio_crudo,
                    presentacion=presentacion,
                    marca_variedad=marca,
                )
            except ValueError as error:
                errores.append({"fila": numero, "mensaje": str(error)})
                continue
            producto.imagen_url = imagen_url
            productos.append(producto)

        if errores:
            raise SolicitudInvalida(
                "El archivo contiene errores. No se importó ningún producto.",
                detalles={"errores": errores, "importados": 0},
            )
        if not productos:
            raise SolicitudInvalida("El archivo no contiene productos válidos para importar")

        importados = self.repo.insertar_productos_validados(productos)
        return {"importados": importados, "errores": []}

    # Cupones -----------------------------------------------------------
    def listar_cupones(self, sesion: Sesion) -> list[dict[str, Any]]:
        self._almacen_de(sesion)
        return [cupon.publico() for cupon in self.repo.listar_cupones()]

    def crear_cupon(self, sesion: Sesion, codigo: str, porcentaje: float) -> dict[str, Any]:
        self._almacen_de(sesion)
        self.validador.validar_cupon_unico(codigo)
        cupon = self.repo.crear_cupon(codigo=codigo, porcentaje=porcentaje)
        return cupon.publico()

    def eliminar_cupon(self, sesion: Sesion, cupon_id: str) -> None:
        self._almacen_de(sesion)
        self.repo.eliminar_cupon(cupon_id)


# Compatibilidad con importaciones antiguas.
ControladorAdministracion = ControladorAdminApp

__all__ = [
    "ControladorAdminAlmacen",
    "ControladorAdminApp",
    "ControladorAdministracion",
]
