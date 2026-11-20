"""Endpoints del administrador de almacén."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status

from controllers.administracion import ControladorAdminAlmacen
from controllers.compras import ControladorComprasAlmacen
from controllers.sesiones import Sesion

from ..dependencies import (
    obtener_admin_almacen,
    obtener_compras_almacen,
    requerir_admin_almacen,
)
from ..schemas import (
    CsvSolicitud,
    CuponCrearSolicitud,
    CuponRespuesta,
    ImportacionRespuesta,
    ProductoActualizacion,
    ProductoPublico,
    ProductoSolicitud,
)

router = APIRouter(tags=["Administrador de almacén"])


# Productos -------------------------------------------------------------
@router.get("/admin-almacen/productos", response_model=list[ProductoPublico])
def listar_productos(
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> list[dict]:
    return admin.listar_productos(sesion)


@router.post(
    "/admin-almacen/productos",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductoPublico,
)
def crear_producto(
    datos: ProductoSolicitud,
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> dict:
    return admin.crear_producto(sesion, datos.model_dump())


@router.patch("/admin-almacen/productos/{producto_id}", response_model=ProductoPublico)
def actualizar_producto(
    producto_id: str,
    datos: ProductoActualizacion,
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> dict:
    return admin.actualizar_producto(sesion, producto_id, datos.model_dump(exclude_unset=True))


@router.delete(
    "/admin-almacen/productos/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_producto(
    producto_id: str,
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> None:
    admin.eliminar_producto(sesion, producto_id)


@router.post(
    "/admin-almacen/productos/{producto_id}/imagen",
    response_model=ProductoPublico,
)
async def subir_imagen_producto(
    producto_id: str,
    archivo: UploadFile = File(description="Imagen JPEG, PNG o WebP de hasta 2 MB."),
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> dict:
    contenido = await archivo.read(admin.max_imagen_bytes + 1)
    return admin.subir_imagen_producto(sesion, producto_id, contenido)


@router.delete(
    "/admin-almacen/productos/{producto_id}/imagen",
    response_model=ProductoPublico,
)
def eliminar_imagen_producto(
    producto_id: str,
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> dict:
    return admin.eliminar_imagen_producto(sesion, producto_id)


@router.post(
    "/admin-almacen/productos/importar",
    response_model=ImportacionRespuesta,
)
def importar_csv(
    datos: CsvSolicitud,
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> dict:
    return admin.importar_csv(sesion, datos.contenido)


# Cupones ---------------------------------------------------------------
@router.get("/admin-almacen/cupones", response_model=list[CuponRespuesta])
def listar_cupones(
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> list[dict]:
    return admin.listar_cupones(sesion)


@router.post(
    "/admin-almacen/cupones",
    status_code=status.HTTP_201_CREATED,
    response_model=CuponRespuesta,
)
def crear_cupon(
    datos: CuponCrearSolicitud,
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> dict:
    return admin.crear_cupon(sesion, datos.codigo, datos.porcentaje)


@router.delete(
    "/admin-almacen/cupones/{cupon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_cupon(
    cupon_id: str,
    sesion: Sesion = Depends(requerir_admin_almacen),
    admin: ControladorAdminAlmacen = Depends(obtener_admin_almacen),
) -> None:
    admin.eliminar_cupon(sesion, cupon_id)


# Compras y estadísticas ------------------------------------------------
@router.get("/admin-almacen/compras")
def listar_compras(
    sesion: Sesion = Depends(requerir_admin_almacen),
    compras: ControladorComprasAlmacen = Depends(obtener_compras_almacen),
) -> list[dict]:
    return compras.compras_del_almacen()


@router.get("/admin-almacen/estadisticas")
def estadisticas(
    sesion: Sesion = Depends(requerir_admin_almacen),
    compras: ControladorComprasAlmacen = Depends(obtener_compras_almacen),
) -> dict:
    return compras.estadisticas_del_almacen()


__all__ = ["router"]
