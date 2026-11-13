"""Endpoints de catálogo de roles y administración de usuarios."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from controllers.compras import ControladorCompras
from core.errors import NoEncontrado, NoPermitido, SolicitudInvalida
from models.almacenes import GestorAlmacenes
from models.permisos import (
    ADMIN,
    GESTIONAR_USUARIOS,
    PERMISOS,
    PROVEEDOR,
)

from ..dependencies import obtener_controlador, obtener_gestor, obtener_seguridad
from ..schemas import (
    CatalogoRolesRespuesta,
    ProveedorSolicitud,
    RolRespuesta,
    UsuarioActualizacion,
    UsuarioRespuesta,
)

router = APIRouter(tags=["Seguridad"])


def _exigir(controlador: ControladorCompras, permiso: str) -> None:
    if not controlador.sesion.tiene_permiso(permiso):
        raise NoPermitido(PERMISOS.get(permiso, permiso), rol=controlador.obtener_rol())


@router.get("/roles", response_model=CatalogoRolesRespuesta)
def listar_roles(seguridad=Depends(obtener_seguridad)):
    """Catálogo público: qué puede hacer cada rol y qué significa cada permiso."""
    return {
        "roles": [rol.json() for rol in seguridad.listar_roles()],
        "permisos": [
            {"codigo": codigo, "descripcion": descripcion}
            for codigo, descripcion in PERMISOS.items()
        ],
    }


@router.get("/roles/{rol}", response_model=RolRespuesta)
def obtener_rol(rol: str, seguridad=Depends(obtener_seguridad)):
    encontrado = seguridad.obtener_rol(rol)
    if encontrado is None:
        raise NoEncontrado(f"Rol no encontrado: {rol}")
    return encontrado.json()


@router.get("/sessions/{token}/users", response_model=list[UsuarioRespuesta])
def listar_usuarios(
    controlador: ControladorCompras = Depends(obtener_controlador),
    seguridad=Depends(obtener_seguridad),
):
    _exigir(controlador, GESTIONAR_USUARIOS)
    return [usuario.json() for usuario in seguridad.listar_usuarios()]


@router.get("/sessions/{token}/users/{usuario_id}", response_model=UsuarioRespuesta)
def obtener_usuario(
    usuario_id: str,
    controlador: ControladorCompras = Depends(obtener_controlador),
    seguridad=Depends(obtener_seguridad),
):
    _exigir(controlador, GESTIONAR_USUARIOS)
    usuario = seguridad.obtener_usuario(usuario_id)
    if usuario is None:
        raise NoEncontrado(f"Usuario no encontrado: {usuario_id}")
    return usuario.json()


@router.post(
    "/sessions/{token}/users/providers",
    status_code=status.HTTP_201_CREATED,
    response_model=UsuarioRespuesta,
)
def crear_proveedor(
    datos: ProveedorSolicitud,
    controlador: ControladorCompras = Depends(obtener_controlador),
    seguridad=Depends(obtener_seguridad),
    gestor: GestorAlmacenes = Depends(obtener_gestor),
):
    _exigir(controlador, GESTIONAR_USUARIOS)
    if gestor.obtener_almacen(datos.almacen_id) is None:
        raise NoEncontrado(f"Almacén no encontrado: {datos.almacen_id}")
    usuario = seguridad.crear_usuario(datos.nombre, PROVEEDOR, datos.almacen_id)
    return usuario.json()


@router.patch("/sessions/{token}/users/{usuario_id}", response_model=UsuarioRespuesta)
def actualizar_usuario(
    usuario_id: str,
    datos: UsuarioActualizacion,
    controlador: ControladorCompras = Depends(obtener_controlador),
    seguridad=Depends(obtener_seguridad),
    gestor: GestorAlmacenes = Depends(obtener_gestor),
):
    _exigir(controlador, GESTIONAR_USUARIOS)
    actual = seguridad.obtener_usuario(usuario_id)
    if actual is None:
        raise NoEncontrado(f"Usuario no encontrado: {usuario_id}")

    cambios = datos.model_dump(exclude_unset=True)
    nuevo_rol = cambios.get("rol", actual.rol)
    nuevo_almacen = cambios.get("almacen_id", actual.almacen_id)
    if nuevo_rol == ADMIN:
        raise SolicitudInvalida(
            "El rol ADMIN se inicia con la clave administrativa, no con un usuario persistido"
        )
    if nuevo_rol == PROVEEDOR and nuevo_almacen is None:
        raise SolicitudInvalida("Un proveedor debe tener un almacén asignado")
    if (
        "almacen_id" in cambios
        and cambios["almacen_id"] is not None
        and gestor.obtener_almacen(cambios["almacen_id"]) is None
    ):
        raise NoEncontrado(f"Almacén no encontrado: {cambios['almacen_id']}")

    kwargs: dict[str, object] = {}
    if "rol" in cambios:
        kwargs["rol"] = cambios["rol"]
    if "almacen_id" in cambios:
        kwargs["almacen_id"] = cambios["almacen_id"]
    if "activo" in cambios:
        kwargs["activo"] = cambios["activo"]

    usuario = seguridad.actualizar_usuario(usuario_id, **kwargs)
    if usuario is None:
        raise NoEncontrado(f"Usuario no encontrado: {usuario_id}")
    return usuario.json()


__all__ = ["router"]
