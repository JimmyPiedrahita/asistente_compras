import os
import tempfile
from collections.abc import Iterator

from fastapi import APIRouter, Header

from .errores import ApiError, OperacionNoPermitida, SesionNoEncontrada
from .esquemas import (
    BusquedaSolicitud,
    CarritoProductoSolicitud,
    ClaveAdministrador,
    CsvSolicitud,
    DescuentoSolicitud,
    ListaProductoSolicitud,
    PrecioSolicitud,
    ProductoSolicitud,
    UsuarioSesion,
)


def producto_json(producto) -> dict:
    resultado = {
        "producto_id": producto.producto_id,
        "nombre": producto.nombre,
        "marca": producto.marca,
        "categoria": producto.categoria,
        "tipo": producto.tipo,
        "precio": producto.precio,
        "precio_final": producto.obtener_precio_final(),
    }
    if producto.tipo == "fisico":
        resultado["costo_envio"] = producto.costo_envio
    elif producto.tipo == "suscripcion":
        resultado["meses"] = producto.meses
    return resultado


def resultado_busqueda_json(resultado) -> list[dict]:
    filas = []
    if isinstance(resultado, dict):
        items: Iterator = (
            (almacen, producto)
            for almacen, productos in resultado.items()
            for producto in productos.mostrar()
        )
    else:
        items = (
            (fila["almacen"], fila["producto"])
            for fila in resultado
        )
    for almacen, producto in items:
        filas.append({
            "almacen_id": almacen.id_almacen,
            "almacen": almacen.nombre,
            "producto": producto_json(producto),
        })
    return filas


def crear_router(sesiones, persistencia) -> APIRouter:
    router = APIRouter()

    def sesion(token: str):
        encontrada = sesiones.obtener(token)
        if encontrada is None:
            raise SesionNoEncontrada()
        return encontrada.controlador

    @router.get("/health")
    def health():
        persistencia.client.admin.command("ping")
        return {"status": "ok", "database": "mongodb"}

    @router.get("/health/live")
    def health_live():
        return {"status": "ok"}

    @router.get("/health/ready")
    def health_ready():
        persistencia.client.admin.command("ping")
        return {"status": "ready", "database": "mongodb"}

    @router.get("/warehouses")
    def listar_almacenes():
        return [
            {
                "id": almacen.id_almacen,
                "name": almacen.nombre,
                "products": len(almacen.inventario),
            }
            for almacen in sesiones.obtener_almacenes()
        ]

    @router.post("/sessions/user", status_code=201)
    def iniciar_usuario(datos: UsuarioSesion):
        nueva = sesiones.crear()
        controlador = nueva.controlador
        controlador.registrar_usuario(datos.nombre)
        if not controlador.iniciar_sesion(datos.nombre):
            raise ApiError(400, "No se pudo iniciar la sesión de usuario")
        return {"session_id": nueva.token, "usuario": datos.nombre, "rol": "CLIENTE"}

    @router.post("/sessions/admin", status_code=201)
    def iniciar_admin(datos: ClaveAdministrador):
        nueva = sesiones.crear()
        if not nueva.controlador.login_admin(datos.clave):
            sesiones.eliminar(nueva.token)
            raise ApiError(401, "Clave de administrador inválida")
        return {"session_id": nueva.token, "usuario": "ADMIN", "rol": "ADMIN"}

    @router.delete("/sessions/{token}", status_code=204)
    def cerrar_sesion(token: str):
        sesion(token)
        sesiones.eliminar(token)

    @router.get("/sessions/{token}")
    def estado_sesion(token: str):
        controlador = sesion(token)
        return {
            "usuario": controlador.obtener_usuario_actual(),
            "rol": controlador.obtener_rol(),
            "lista": controlador.obtener_compras_usuario(),
            "carrito": resumen_carrito(controlador),
        }

    @router.post("/sessions/{token}/shopping-list")
    def agregar_lista(token: str, datos: ListaProductoSolicitud):
        controlador = sesion(token)
        resultado = controlador.agregar_producto_usuario(datos.nombre)
        if resultado == "denegado":
            raise OperacionNoPermitida("crear_lista")
        if resultado != "ok":
            raise ApiError(400, f"No se pudo agregar el producto: {resultado}")
        return {"lista": controlador.obtener_compras_usuario()}

    @router.delete("/sessions/{token}/shopping-list/{nombre}")
    def eliminar_lista(token: str, nombre: str):
        controlador = sesion(token)
        resultado = controlador.eliminar_producto_usuario(nombre)
        if resultado == "denegado":
            raise OperacionNoPermitida("eliminar_producto")
        if resultado != "ok":
            raise ApiError(404, "Producto no encontrado en la lista")
        return {"lista": controlador.obtener_compras_usuario()}

    @router.post("/sessions/{token}/search")
    def buscar(token: str, datos: BusquedaSolicitud):
        controlador = sesion(token)
        modos = {
            "mejor_precio": controlador.ejecutar_busqueda_precios,
            "catalogo": controlador.ejecutar_catalogo,
            "global": controlador.ejecutar_comparacion_global,
        }
        try:
            resultado = modos[datos.modo.strip().lower()]()
        except KeyError:
            raise ApiError(400, "Modo inválido: mejor_precio, catalogo o global")
        if resultado == {} or resultado == []:
            if controlador.obtener_rol() == "INVITADO":
                raise OperacionNoPermitida("comparar")
        return {"modo": datos.modo, "resultados": resultado_busqueda_json(resultado)}

    def resumen_carrito(controlador) -> dict:
        resumen = controlador.obtener_resumen_carrito()
        return {
            "productos": [producto_json(p) for p in resumen["productos"]],
            "subtotal": resumen["subtotal"],
            "total": resumen["total"],
            "descuento": resumen["descuento"],
        }

    @router.get("/sessions/{token}/cart")
    def obtener_carrito(token: str):
        return resumen_carrito(sesion(token))

    @router.post("/sessions/{token}/cart/items")
    def agregar_carrito(token: str, datos: CarritoProductoSolicitud):
        controlador = sesion(token)
        almacen = controlador.gestor_almacenes.obtener_almacen(datos.almacen_id)
        if almacen is None:
            raise ApiError(404, "Almacén no encontrado")
        producto = next(
            (p for p in almacen.inventario.mostrar()
             if p.producto_id == datos.producto_id),
            None,
        )
        if producto is None:
            raise ApiError(404, "Producto no encontrado")
        if not controlador.agregar_seleccion_al_carrito(producto, datos.almacen_id):
            raise OperacionNoPermitida("agregar_producto")
        return resumen_carrito(controlador)

    @router.delete("/sessions/{token}/cart/items/{indice}")
    def quitar_carrito(token: str, indice: int):
        controlador = sesion(token)
        if not controlador.quitar_producto_carrito(indice):
            raise ApiError(404, "Ítem no encontrado en el carrito")
        return resumen_carrito(controlador)

    @router.delete("/sessions/{token}/cart")
    def vaciar_carrito(token: str):
        controlador = sesion(token)
        controlador.vaciar_carrito()
        return resumen_carrito(controlador)

    @router.post("/sessions/{token}/cart/discount")
    def aplicar_descuento(token: str, datos: DescuentoSolicitud):
        controlador = sesion(token)
        resultado = controlador.establecer_descuento(datos.tipo, datos.valor)
        if resultado == "denegado":
            raise OperacionNoPermitida("aplicar_descuento")
        if resultado != "ok":
            raise ApiError(400, "Descuento inválido")
        return resumen_carrito(controlador)

    @router.post("/sessions/{token}/admin/warehouses/{almacen_id}/products")
    def agregar_producto(token: str, almacen_id: int, datos: ProductoSolicitud):
        controlador = sesion(token)
        extra = {}
        if datos.costo_envio is not None:
            extra["costo_envio"] = datos.costo_envio
        if datos.meses is not None:
            extra["meses"] = datos.meses
        if not controlador.agregar_producto_almacen(
            almacen_id, datos.nombre, datos.precio, datos.marca,
            datos.categoria, datos.tipo, **extra
        ):
            raise OperacionNoPermitida("gestionar_almacenes")
        return {"ok": True}

    @router.patch("/sessions/{token}/admin/warehouses/{almacen_id}/products")
    def editar_precio(token: str, almacen_id: int, datos: PrecioSolicitud):
        controlador = sesion(token)
        almacen = controlador.gestor_almacenes.obtener_almacen(almacen_id)
        if almacen is None:
            raise ApiError(404, "Almacén no encontrado")
        indice = next(
            (i for i, p in enumerate(almacen.inventario.mostrar())
             if p.producto_id == datos.producto_id),
            None,
        )
        if indice is None or not controlador.editar_precio(
            almacen_id, indice, datos.precio
        ):
            raise OperacionNoPermitida("editar_precio")
        return {"ok": True}

    @router.post("/sessions/{token}/admin/csv")
    def cargar_csv(token: str, datos: CsvSolicitud):
        controlador = sesion(token)
        ruta = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, encoding="utf-8"
            ) as archivo:
                archivo.write(datos.contenido)
                ruta = archivo.name
            resultado = controlador.cargar_csv(ruta)
        finally:
            if ruta:
                try:
                    os.unlink(ruta)
                except OSError:
                    pass
        if controlador.obtener_rol() != "ADMIN":
            raise OperacionNoPermitida("cargar_csv")
        return resultado

    return router
