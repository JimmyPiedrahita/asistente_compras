from listas import ListaSimple
from modelos import Producto, normalizar_texto


class Almacen:
    """Almacén con inventario en una lista simplemente enlazada."""

    def __init__(self, id_almacen: int, nombre: str):
        self.id_almacen = id_almacen
        self.nombre = nombre
        self.inventario = ListaSimple()

    def __repr__(self):
        return f"Almacen({self.id_almacen}, {self.nombre!r})"


class GestorAlmacenes:
    """Gestiona la colección de almacenes del sistema."""

    def __init__(self, persistencia=None):
        self.almacenes = []
        self.persistencia = persistencia

    def agregar_almacen(self, almacen: Almacen):
        self.almacenes.append(almacen)

    def obtener_almacenes(self) -> list:
        return self.almacenes

    def obtener_almacen(self, id_almacen: int):
        for almacen in self.almacenes:
            if almacen.id_almacen == id_almacen:
                return almacen
        return None

    def agregar_producto(self, id_almacen: int, producto: Producto) -> bool:
        almacen = self.obtener_almacen(id_almacen)
        if almacen is None:
            return False
        if self.persistencia is not None:
            self.persistencia.insertar(id_almacen, producto)
        almacen.inventario.agregar(producto)
        return True

    def cargar_inventarios(self):
        if self.persistencia is None:
            return
        for almacen in self.almacenes:
            almacen.inventario = ListaSimple()
            for producto in self.persistencia.cargar_almacen(almacen.id_almacen):
                almacen.inventario.agregar(producto)

    def buscar_producto(self, id_almacen: int, nombre: str, marca: str = None):
        almacen = self.obtener_almacen(id_almacen)
        if almacen is None:
            return None
        for producto in almacen.inventario.mostrar():
            if normalizar_texto(producto.nombre) != normalizar_texto(nombre):
                continue
            if marca is not None and normalizar_texto(producto.marca) != normalizar_texto(marca):
                continue
            return producto
        return None

    def productos(self):
        """Itera pares (almacén, producto) de todo el sistema."""
        for almacen in self.almacenes:
            for producto in almacen.inventario.mostrar():
                yield almacen, producto
