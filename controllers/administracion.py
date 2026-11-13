"""Funciones del administrador de la aplicación y del administrador de almacén."""

from __future__ import annotations

import csv
import io
import re
import uuid
from typing import Any

from core.errors import NoEncontrado, SolicitudInvalida
from infrastructure.mongodb.repositorio import RepositorioMongo
from models.permisos import ADMINISTRADOR_ALMACEN
from models.productos import Producto

from .sesiones import Sesion

_CABECERAS_OBLIGATORIAS = {"tipo_producto", "nombre", "precio", "presentacion"}
_CABECERAS_PERMITIDAS = _CABECERAS_OBLIGATORIAS | {"marca_variedad"}
_PRECIO_VALIDO = re.compile(r"^\d+(?:\.\d+)?$")


class ControladorAdministracion:
    def __init__(self, repositorio: RepositorioMongo, *, max_csv_bytes: int = 1_000_000) -> None:
        self.repo = repositorio
        self.max_csv_bytes = int(max_csv_bytes)

    # Administrador de la aplicación -----------------------------------
    def crear_almacen(self, nombre: str) -> dict[str, Any]:
        almacen = self.repo.crear_almacen(nombre)
        return {**almacen.publico(), "productos": 0}

    def listar_almacenes(self) -> list[dict[str, Any]]:
        return [
            {
                **almacen.publico(),
                "productos": self.repo.contar_productos(almacen.almacen_id),
            }
            for almacen in self.repo.listar_almacenes()
        ]

    def crear_admin_almacen(
        self,
        *,
        nombre: str,
        email: str,
        password: str,
        almacen_id: str,
    ) -> dict[str, Any]:
        almacen = self.repo.obtener_almacen(almacen_id)
        if almacen is None:
            raise NoEncontrado("Almacén no encontrado")
        usuario = self.repo.crear_usuario(
            nombre=nombre,
            email=email,
            password=password,
            rol=ADMINISTRADOR_ALMACEN,
            almacen_id=almacen.almacen_id,
        )
        return {**usuario.publico(), "almacen_nombre": almacen.nombre}

    def listar_admins_almacen(self) -> list[dict[str, Any]]:
        almacenes = {a.almacen_id: a.nombre for a in self.repo.listar_almacenes()}
        return [
            {
                **usuario.publico(),
                "almacen_nombre": almacenes.get(usuario.almacen_id or "", ""),
            }
            for usuario in self.repo.listar_administradores_almacen()
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
        usuario = self.repo.actualizar_credenciales(usuario_id, email=email, password=password)
        return usuario.publico()

    # Administrador de almacén: productos -------------------------------
    @staticmethod
    def _almacen_de(sesion: Sesion) -> str:
        if not sesion.almacen_id:
            raise NoEncontrado("La cuenta no tiene un almacén asignado")
        return sesion.almacen_id

    def listar_productos(self, sesion: Sesion) -> list[dict[str, Any]]:
        almacen_id = self._almacen_de(sesion)
        return [producto.publico() for producto in self.repo.listar_todos_productos(almacen_id)]

    def crear_producto(self, sesion: Sesion, datos: dict[str, Any]) -> dict[str, Any]:
        almacen_id = self._almacen_de(sesion)
        try:
            producto = self.repo.crear_producto(
                almacen_id=almacen_id,
                tipo_producto=str(datos.get("tipo_producto") or ""),
                nombre=str(datos.get("nombre") or ""),
                precio=datos.get("precio"),
                presentacion=str(datos.get("presentacion") or ""),
                marca_variedad=str(datos.get("marca_variedad") or ""),
            )
        except ValueError as error:
            raise SolicitudInvalida(str(error)) from error
        return producto.publico()

    def actualizar_producto(
        self, sesion: Sesion, producto_id: str, cambios: dict[str, Any]
    ) -> dict[str, Any]:
        almacen_id = self._almacen_de(sesion)
        try:
            producto = self.repo.actualizar_producto(producto_id, almacen_id, cambios)
        except ValueError as error:
            raise SolicitudInvalida(str(error)) from error
        return producto.publico()

    def eliminar_producto(self, sesion: Sesion, producto_id: str) -> None:
        almacen_id = self._almacen_de(sesion)
        self.repo.eliminar_producto(producto_id, almacen_id)

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

            tipo_norm = " ".join(tipo.casefold().split())
            if tipo_norm not in existentes:
                existentes[tipo_norm] = self.repo.presentaciones_del_tipo(tipo_norm)
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

    # Administrador de almacén: cupones --------------------------------
    def listar_cupones(self, sesion: Sesion) -> list[dict[str, Any]]:
        almacen_id = self._almacen_de(sesion)
        return [cupon.publico() for cupon in self.repo.listar_cupones(almacen_id)]

    def crear_cupon(self, sesion: Sesion, codigo: str, porcentaje: float) -> dict[str, Any]:
        almacen_id = self._almacen_de(sesion)
        cupon = self.repo.crear_cupon(codigo=codigo, almacen_id=almacen_id, porcentaje=porcentaje)
        return cupon.publico()

    def eliminar_cupon(self, sesion: Sesion, cupon_id: str) -> None:
        almacen_id = self._almacen_de(sesion)
        self.repo.eliminar_cupon(cupon_id, almacen_id)


__all__ = ["ControladorAdministracion"]
