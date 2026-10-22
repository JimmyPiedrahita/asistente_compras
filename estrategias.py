from abc import ABC, abstractmethod

from listas import ListaSimple

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
    def buscar(self, lista_compras, gestor_almacenes) -> dict:
        resultado = {}
        for almacen in gestor_almacenes.obtener_almacenes():
            for nombre in lista_compras.mostrar():
                mejor = None
                for p in almacen.inventario.mostrar():
                    if str(p.nombre).strip().lower() == str(nombre).strip().lower():
                        if mejor is None or p.precio < mejor.precio:
                            mejor = p
                if mejor is not None:
                    resultado.setdefault(almacen, ListaSimple()).agregar(mejor)
        return resultado


class BusquedaCatalogoStrategy(EstrategiaBusqueda):
    def buscar(self, lista_compras, gestor_almacenes) -> dict:
        resultado = {}
        for almacen in gestor_almacenes.obtener_almacenes():
            encontrados = ListaSimple()
            for nombre in lista_compras.mostrar():
                for p in almacen.inventario.mostrar():
                    if str(p.nombre).strip().lower() == str(nombre).strip().lower():
                        encontrados.agregar(p)
            if not encontrados.esta_vacia():
                resultado[almacen] = encontrados
        return resultado