import csv
import os

from models.almacenes import Almacen, GestorAlmacenes
from models.estrategias import (
    SinDescuento, DescuentoPorcentaje, DescuentoFijo,
    BusquedaMejorPrecioStrategy, BusquedaCatalogoStrategy,
    MejorPrecioGlobalStrategy)
from models.listas import ListaDoblementeEnlazada
from models.modelos import FabricaProductos, normalizar_texto
from permisos import logger

# PATRÓN 4: MODELO_VISTA_CONTROLADOR


class _VistaNula:
    """Observador interno para ejecutar casos de uso sin una UI."""

    def actualizar(self, sujeto, mensaje: str):
        return None

    def notificar_denegado(self, permiso: str):
        return None


class ControladorCompras:
    def __init__(self, carrito, vista=None, gestor_almacenes=None):
        self.carrito = carrito
        self.vista = vista or _VistaNula()
        self.lista_compras = ListaDoblementeEnlazada()
        self.gestor_almacenes = gestor_almacenes or GestorAlmacenes()
        self.estrategia_busqueda = BusquedaMejorPrecioStrategy()
        self.estrategia_catalogo = BusquedaCatalogoStrategy()
        self.comparador_global = MejorPrecioGlobalStrategy()
        self._clave_admin = os.getenv("ADMIN_CLAVE", "admin123")

        self._usuarios = []
        self._usuario_actual = None
        self._rol = "INVITADO"
        self._descuento_actual = "Sin descuento"
        self._nombre_consola = None

        for i in range(1, 4):
            if self.gestor_almacenes.obtener_almacen(i) is None:
                self.gestor_almacenes.agregar_almacen(
                    Almacen(id_almacen=i, nombre=f"Almacen {i}"))
        self.gestor_almacenes.cargar_inventarios()

        # Conectamos la Vista como Observador del Carrito
        self.carrito.agregar_observador(self.vista)

    # = SESIÓN DE USUARIOS Y PERMISOS =

    def _autorizar(self, permiso: str) -> bool:
        permitido = logger.tiene_permiso(self._rol, permiso)
        if not permitido and hasattr(self.vista, "notificar_denegado"):
            self.vista.notificar_denegado(permiso)
        return permitido

    def registrar_usuario(self, nombre: str) -> bool:
        nombre = (nombre or "").strip()
        if not nombre or nombre in self._usuarios:
            return False
        self._usuarios.append(nombre)
        logger.log("SISTEMA", "Usuario registrado", nombre)
        return True

    def iniciar_sesion(self, nombre: str) -> bool:
        nombre = (nombre or "").strip()
        if nombre in self._usuarios:
            self._usuario_actual = nombre
            self._rol = "CLIENTE"
            logger.log("SISTEMA", "Inicio de sesión", f"{nombre} (CLIENTE)")
            return True
        logger.log("SISTEMA", "Inicio de sesión fallido", nombre or "(vacío)")
        return False

    def cerrar_sesion(self):
        if self._usuario_actual:
            logger.log("SISTEMA", "Cierre de sesión", self._usuario_actual)
        self._usuario_actual = None
        self._rol = "INVITADO"
        self._descuento_actual = "Sin descuento"
        self.carrito.establecer_estrategia_descuento(None)

    def obtener_usuario_actual(self):
        return self._usuario_actual

    def obtener_rol(self) -> str:
        return self._rol

    def login_admin(self, clave: str) -> bool:
        if clave == self._clave_admin:
            self._usuario_actual = "ADMIN"
            self._rol = "ADMIN"
            logger.log("ADMIN", "Inicio de sesión", "CONCEDIDO")
            return True
        logger.log("ADMIN", "Intento de login fallido", "DENEGADO")
        return False

    # = LISTA DE COMPRAS DEL USUARIO =

    def agregar_producto_usuario(self, nombre: str) -> str:
        nombre = (nombre or "").strip()
        if not nombre:
            return "vacio"
        if not self._autorizar("crear_lista"):
            return "denegado"
        for existente in self.lista_compras.mostrar():
            if normalizar_texto(existente) == normalizar_texto(nombre):
                logger.log("CLIENTE", "Producto duplicado en la lista", nombre)
                return "duplicado"
        self.lista_compras.agregar_al_final(nombre)
        logger.log("CLIENTE", "Producto agregado a la lista", nombre)
        return "ok"

    def eliminar_producto_usuario(self, nombre: str) -> str:
        nombre = (nombre or "").strip()
        if not nombre:
            return "vacio"
        if not self._autorizar("eliminar_producto"):
            return "denegado"
        # La lista guarda nombres; se busca la coincidencia normalizada.
        for existente in list(self.lista_compras.mostrar()):
            if normalizar_texto(existente) == normalizar_texto(nombre):
                self.lista_compras.eliminar(existente)
                logger.log("CLIENTE", "Producto eliminado de la lista", existente)
                return "ok"
        return "no_encontrado"

    def obtener_compras_usuario(self):
        return list(self.lista_compras.mostrar())

    # = ADMINISTRACIÓN DE ALMACENES =

    def _insertar_producto(self, id_almacen: int, producto) -> bool:
        if not self.gestor_almacenes.agregar_producto(id_almacen, producto):
            logger.log("ADMIN", f"Almacén {id_almacen} inexistente", "RECHAZADO")
            return False
        logger.log("ADMIN", "Producto en inventario",
                   f"{producto} -> Almacen {id_almacen}")
        return True

    def agregar_producto_almacen(self, id_almacen: int, nombre: str, precio: float,
                                 marca: str = "Generica", categoria: str = "General",
                                 tipo: str = "normal", **extra) -> bool:
        if not self._autorizar("gestionar_almacenes"):
            return False
        try:
            producto = FabricaProductos.crear_producto(
                tipo, nombre, precio, marca=marca, categoria=categoria, **extra)
        except (ValueError, TypeError) as error:
            logger.log("ADMIN", "Producto rechazado", str(error))
            return False
        return self._insertar_producto(id_almacen, producto)

    def editar_precio(self, id_almacen: int, indice: int, nuevo_precio: float) -> bool:
        if not self._autorizar("editar_precio"):
            return False
        almacen = self.gestor_almacenes.obtener_almacen(id_almacen)
        if almacen is None:
            return False
        try:
            nuevo_precio = float(nuevo_precio)
        except (TypeError, ValueError):
            return False
        if nuevo_precio < 0:
            return False
        try:
            producto = almacen.inventario.obtener(indice)
        except IndexError:
            return False
        anterior = producto.precio
        producto.precio = nuevo_precio
        if self.gestor_almacenes.persistencia is not None:
            try:
                self.gestor_almacenes.persistencia.actualizar(id_almacen, producto)
            except (KeyError, OSError, RuntimeError):
                producto.precio = anterior
                logger.log("ADMIN", "Precio no actualizado",
                           "No se pudo persistir en MongoDB")
                return False
        logger.log("ADMIN", "Precio actualizado",
                   f"{producto.nombre}: ${anterior:.2f} -> ${nuevo_precio:.2f}")
        return True

    def cargar_csv(self, ruta: str) -> dict:
        resultado = {"importados": 0, "rechazados": 0, "errores": []}
        if not self._autorizar("cargar_csv"):
            resultado["errores"].append("Permiso denegado para cargar_csv")
            return resultado

        try:
            archivo = open(ruta, newline="", encoding="utf-8-sig")
        except OSError as error:
            resultado["errores"].append(f"No se pudo abrir el archivo: {error}")
            return resultado

        with archivo:
            lector = csv.DictReader(archivo)
            columnas = {normalizar_texto(c) for c in (lector.fieldnames or [])}
            requeridas = {"almacen", "nombre", "precio"}
            if not requeridas.issubset(columnas):
                resultado["errores"].append(
                    "Cabecera inválida: se requieren almacen, nombre y precio")
                return resultado

            for numero, fila in enumerate(lector, start=2):
                try:
                    datos = {(normalizar_texto(k)): (v or "").strip()
                             for k, v in fila.items() if k is not None}
                    id_almacen = int(datos.get("almacen", ""))
                    nombre = datos.get("nombre", "")
                    precio = float(datos.get("precio", ""))
                    marca = datos.get("marca") or "Generica"
                    categoria = datos.get("categoria") or "General"
                    tipo = datos.get("tipo") or "normal"
                    extra = datos.get("extra") or ""

                    kwargs = {}
                    if normalizar_texto(tipo) == "fisico":
                        kwargs["costo_envio"] = float(extra) if extra else 5.0
                    elif normalizar_texto(tipo) == "suscripcion":
                        kwargs["meses"] = int(extra) if extra else 1

                    producto = FabricaProductos.crear_producto(
                        tipo, nombre, precio, marca=marca, categoria=categoria, **kwargs)
                    if self._insertar_producto(id_almacen, producto):
                        resultado["importados"] += 1
                    else:
                        raise ValueError(f"almacén {id_almacen} inexistente")
                except (ValueError, TypeError) as error:
                    resultado["rechazados"] += 1
                    resultado["errores"].append(f"Línea {numero}: {error}")

        logger.log("ADMIN", "Carga CSV finalizada",
                   f"{resultado['importados']} importados, "
                   f"{resultado['rechazados']} rechazados")
        return resultado

    # = BÚSQUEDAS (STRATEGY) =

    def ejecutar_busqueda_precios(self):
        if not self._autorizar("comparar"):
            return {}
        return self.estrategia_busqueda.buscar(self.lista_compras,
                                               self.gestor_almacenes)

    def ejecutar_catalogo(self):
        if not self._autorizar("comparar"):
            return {}
        return self.estrategia_catalogo.buscar(self.lista_compras,
                                               self.gestor_almacenes)

    def ejecutar_comparacion_global(self) -> list:
        if not self._autorizar("comparar"):
            return []
        return self.comparador_global.buscar(self.lista_compras,
                                             self.gestor_almacenes)

    # = CARRITO =

    def _agregar_al_carrito(self, producto) -> bool:
        self.carrito.agregar_producto(producto.clonar())
        return True

    def agregar_producto_carrito(self, producto) -> bool:
        if not self._autorizar("agregar_producto"):
            return False
        return self._agregar_al_carrito(producto)

    def agregar_seleccion_al_carrito(self, producto, id_almacen: int) -> bool:
        if not self._autorizar("agregar_producto"):
            return False
        almacen = self.gestor_almacenes.obtener_almacen(id_almacen)
        if almacen is None:
            return False
        for candidato in almacen.inventario.mostrar():
            coincide = (
                candidato is producto
                or (normalizar_texto(candidato.nombre) == normalizar_texto(producto.nombre)
                    and normalizar_texto(candidato.marca) == normalizar_texto(producto.marca)
                    and abs(float(candidato.precio) - float(producto.precio)) < 1e-9)
            )
            if coincide:
                return self._agregar_al_carrito(candidato)
        logger.log("CLIENTE", "Selección no válida", "El producto ya no está en el almacén")
        return False

    def quitar_producto_carrito(self, indice: int) -> bool:
        if not self._autorizar("eliminar_producto"):
            return False
        return self.carrito.eliminar_producto(indice)

    def vaciar_carrito(self):
        if self._autorizar("eliminar_producto"):
            self.carrito.vaciar()

    def establecer_descuento(self, opcion: str, valor=None) -> str:
        """Devuelve 'ok', 'invalido' o 'denegado'."""
        if not self._autorizar("aplicar_descuento"):
            return "denegado"
        opcion = normalizar_texto(opcion)
        try:
            if opcion in ("sin", "sin descuento", "0", "1", ""):
                estrategia = SinDescuento()
                etiqueta = "Sin descuento"
            elif opcion in ("porcentaje", "porcentaje (%)", "2"):
                porcentaje = float(valor)
                if not 0 <= porcentaje <= 100:
                    return "invalido"
                estrategia = DescuentoPorcentaje(porcentaje)
                etiqueta = f"{porcentaje:g}%"
            elif opcion in ("fijo", "monto fijo", "monto fijo ($)", "3"):
                monto = float(valor)
                if monto < 0:
                    return "invalido"
                estrategia = DescuentoFijo(monto)
                etiqueta = f"-${monto:.2f}"
            else:
                return "invalido"
        except (TypeError, ValueError):
            return "invalido"

        self.carrito.establecer_estrategia_descuento(estrategia)
        self._descuento_actual = etiqueta
        logger.log("CLIENTE", "Descuento aplicado", etiqueta)
        return "ok"

    def obtener_resumen_carrito(self) -> dict:
        productos = list(self.carrito.obtener_productos())
        return {
            "productos": productos,
            "subtotal": self.carrito.calcular_subtotal(),
            "total": self.carrito.calcular_total(),
            "descuento": self._descuento_actual,
        }

    # = EXPORTACIÓN =

    def exportar_lista(self, ruta: str) -> dict:
        if not self._autorizar("exportar"):
            return {"ok": False, "filas": 0}
        filas = self.comparador_global.buscar(self.lista_compras,
                                             self.gestor_almacenes)
        try:
            with open(ruta, "w", newline="", encoding="utf-8") as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(["producto", "marca", "precio_final", "almacen"])
                for fila in filas:
                    escritor.writerow([
                        fila["nombre"],
                        fila["producto"].marca,
                        f"{fila['precio']:.2f}",
                        fila["almacen"].nombre,
                    ])
        except OSError as error:
            logger.log("ERROR", "No se pudo exportar la lista", str(error))
            return {"ok": False, "filas": 0}
        logger.log("CLIENTE", "Lista exportada", f"{len(filas)} filas -> {ruta}")
        return {"ok": True, "filas": len(filas)}

    def exportar_carrito(self, ruta: str) -> dict:
        if not self._autorizar("exportar"):
            return {"ok": False, "filas": 0}
        resumen = self.obtener_resumen_carrito()
        try:
            with open(ruta, "w", newline="", encoding="utf-8") as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(["producto", "marca", "precio_final"])
                for producto in resumen["productos"]:
                    escritor.writerow([producto.nombre, producto.marca,
                                       f"{producto.obtener_precio_final():.2f}"])
                escritor.writerow([])
                escritor.writerow(["subtotal", f"{resumen['subtotal']:.2f}"])
                escritor.writerow(["descuento", resumen["descuento"]])
                escritor.writerow(["total", f"{resumen['total']:.2f}"])
        except OSError as error:
            logger.log("ERROR", "No se pudo exportar el carrito", str(error))
            return {"ok": False, "filas": 0}
        logger.log("CLIENTE", "Carrito exportado",
                   f"{len(resumen['productos'])} ítems -> {ruta}")
        return {"ok": True, "filas": len(resumen["productos"])}
