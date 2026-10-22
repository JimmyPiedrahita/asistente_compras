from abc import ABC, abstractmethod

from listas import ListaSimple
from modelos import normalizar_texto

# PATRÓN 3: STRATEGY


class EstrategiaDescuento(ABC):
    @abstractmethod
    def calcular(self, monto: float) -> float:
        pass


class SinDescuento(EstrategiaDescuento):
    def calcular(self, monto: float) -> float:
        return monto


class DescuentoPorcentaje(EstrategiaDescuento):
    def __init__(self, porcentaje: float):
        self.porcentaje = porcentaje

    def calcular(self, monto: float) -> float:
        return monto * (1 - self.porcentaje / 100.0)


class DescuentoFijo(EstrategiaDescuento):
    def __init__(self, monto_descuento: float):
        self.monto_descuento = monto_descuento

    def calcular(self, monto: float) -> float:
        return max(0.0, monto - self.monto_descuento)


class EstrategiaBusqueda(ABC):
    @abstractmethod
    def buscar(self, lista_compras, gestor_almacenes) -> dict:
        pass


class BusquedaMejorPrecioStrategy(EstrategiaBusqueda):
    """Mejor precio de cada producto dentro de cada almacén."""

    def buscar(self, lista_compras, gestor_almacenes) -> dict:
        resultado = {}
        for almacen in gestor_almacenes.obtener_almacenes():
            for nombre in lista_compras.mostrar():
                mejor = None
                for producto in almacen.inventario.mostrar():
                    if normalizar_texto(producto.nombre) != normalizar_texto(nombre):
                        continue
                    if mejor is None or producto.obtener_precio_final() < mejor.obtener_precio_final():
                        mejor = producto
                if mejor is not None:
                    resultado.setdefault(almacen, ListaSimple()).agregar(mejor)
        return resultado


class BusquedaCatalogoStrategy(EstrategiaBusqueda):
    """Todas las coincidencias disponibles en cada almacén."""

    def buscar(self, lista_compras, gestor_almacenes) -> dict:
        resultado = {}
        for almacen in gestor_almacenes.obtener_almacenes():
            encontrados = ListaSimple()
            for nombre in lista_compras.mostrar():
                for producto in almacen.inventario.mostrar():
                    if normalizar_texto(producto.nombre) == normalizar_texto(nombre):
                        encontrados.agregar(producto)
            if not encontrados.esta_vacia():
                resultado[almacen] = encontrados
        return resultado


class MejorPrecioGlobalStrategy:
    """Compara entre todos los almacenes y devuelve la opción más barata."""

    def buscar(self, lista_compras, gestor_almacenes) -> list:
        resultado = []
        for nombre in lista_compras.mostrar():
            mejor = None
            mejor_almacen = None
            for almacen, producto in gestor_almacenes.productos():
                if normalizar_texto(producto.nombre) != normalizar_texto(nombre):
                    continue
                if mejor is None or producto.obtener_precio_final() < mejor.obtener_precio_final():
                    mejor = producto
                    mejor_almacen = almacen
            if mejor is not None:
                resultado.append({
                    "nombre": mejor.nombre,
                    "producto": mejor,
                    "almacen": mejor_almacen,
                    "precio": mejor.obtener_precio_final(),
                })
        return resultado
