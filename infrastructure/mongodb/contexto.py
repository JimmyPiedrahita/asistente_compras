"""Construcción del contexto de persistencia compartido por API y listener."""

from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings
from core.logging import obtener_logger

from .conexiones import ConexionesMongo
from .directorio import DirectorioAlmacenes
from .global_db import (
    RepositorioAlmacenes,
    RepositorioCatalogoGlobal,
    RepositorioComprasGlobal,
    RepositorioEstadoCompras,
    RepositorioReplicaCatalogo,
    RepositorioUsuarios,
    RepositorioValidacion,
)
from .provisioning import ServicioAprovisionamiento
from .replicacion import ProyectorCompras, SincronizadorCatalogo
from .uri import FabricaURIs
from .validacion import ServicioValidacion

logger = obtener_logger("asistente_compras.mongodb.contexto")


@dataclass
class ContextoAplicacion:
    settings: Settings
    fabrica: FabricaURIs
    conexiones: ConexionesMongo
    repo_usuarios: RepositorioUsuarios
    repo_almacenes: RepositorioAlmacenes
    repo_catalogo: RepositorioCatalogoGlobal
    repo_compras: RepositorioComprasGlobal
    repo_validacion: RepositorioValidacion
    repo_replica: RepositorioReplicaCatalogo
    repo_estado_compras: RepositorioEstadoCompras
    validador: ServicioValidacion
    directorio: DirectorioAlmacenes
    aprovisionamiento: ServicioAprovisionamiento
    sincronizador: SincronizadorCatalogo
    proyector: ProyectorCompras

    def cerrar(self) -> None:
        self.conexiones.cerrar()


def construir_contexto(settings: Settings) -> ContextoAplicacion:
    fabrica = FabricaURIs(settings)
    conexiones = ConexionesMongo(settings.mongodb_timeout_ms)
    global_db = settings.mongodb_global_db

    base_auth = conexiones.base(fabrica.uri_auth(), global_db)
    base_admin = conexiones.base(fabrica.uri_admin_app(), global_db)
    base_cliente = conexiones.base(fabrica.uri_cliente(), global_db)
    base_validador = conexiones.base(fabrica.uri_validador(), global_db)
    base_catalogo = conexiones.base(fabrica.uri_catalogo(), global_db)
    base_compras = conexiones.base(fabrica.uri_compras(), global_db)

    repo_usuarios = RepositorioUsuarios(base_auth)
    repo_almacenes = RepositorioAlmacenes(base_admin)
    repo_catalogo = RepositorioCatalogoGlobal(base_cliente)
    repo_compras = RepositorioComprasGlobal(base_cliente)
    repo_validacion = RepositorioValidacion(base_validador)
    repo_replica = RepositorioReplicaCatalogo(base_catalogo)
    repo_estado_compras = RepositorioEstadoCompras(base_compras)

    repo_usuarios.inicializar()
    repo_almacenes.inicializar()
    repo_compras.inicializar()
    repo_usuarios.asegurar_admin(
        admin_email=settings.admin_email,
        admin_password=settings.admin_password,
        admin_nombre=settings.admin_nombre,
    )

    validador = ServicioValidacion(repo_validacion)
    directorio = DirectorioAlmacenes(repo_almacenes, fabrica, conexiones)
    aprovisionamiento = ServicioAprovisionamiento(settings, fabrica, conexiones, repo_almacenes)
    sincronizador = SincronizadorCatalogo(
        settings, fabrica, conexiones, repo_almacenes, repo_replica
    )
    proyector = ProyectorCompras(
        settings,
        fabrica,
        conexiones,
        repo_almacenes,
        repo_compras,
        repo_estado_compras,
    )

    logger.info(
        "Contexto MongoDB listo (global=%s, modo_pruebas=%s)",
        global_db,
        settings.modo_pruebas,
    )
    return ContextoAplicacion(
        settings=settings,
        fabrica=fabrica,
        conexiones=conexiones,
        repo_usuarios=repo_usuarios,
        repo_almacenes=repo_almacenes,
        repo_catalogo=repo_catalogo,
        repo_compras=repo_compras,
        repo_validacion=repo_validacion,
        repo_replica=repo_replica,
        repo_estado_compras=repo_estado_compras,
        validador=validador,
        directorio=directorio,
        aprovisionamiento=aprovisionamiento,
        sincronizador=sincronizador,
        proyector=proyector,
    )


__all__ = ["ContextoAplicacion", "construir_contexto"]
