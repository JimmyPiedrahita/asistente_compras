from typing import Optional, Iterator

from modelos import SujetoObservable


class NodoSimple:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente: Optional['NodoSimple'] = None


class ListaSimple:
    def __init__(self):
        self.cabeza: Optional[NodoSimple] = None
        self.cola: Optional[NodoSimple] = None

    def esta_vacia(self) -> bool:
        return self.cabeza is None

    def agregar(self, dato):
        nuevo_nodo = NodoSimple(dato)
        if self.cabeza is None:
            self.cabeza = nuevo_nodo
            self.cola = nuevo_nodo
        else:
            if self.cola is not None:
                self.cola.siguiente = nuevo_nodo
                self.cola = nuevo_nodo

    def mostrar(self) -> Iterator:
        actual = self.cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente


class Nodo:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente: Optional['Nodo'] = None
        self.anterior: Optional['Nodo'] = None


class ListaDoblementeEnlazada:
    def __init__(self):
        self.cabeza: Optional[Nodo] = None
        self.cola: Optional[Nodo] = None

    def esta_vacia(self) -> bool:
        return self.cabeza is None

    def agregar_al_final(self, dato):
        nuevo_nodo = Nodo(dato)
        if self.cabeza is None or self.cola is None:
            self.cabeza = self.cola = nuevo_nodo
        else:
            self.cola.siguiente = nuevo_nodo
            nuevo_nodo.anterior = self.cola
            self.cola = nuevo_nodo

    def agregar_al_inicio(self, dato):
        nuevo_nodo = Nodo(dato)
        if self.cabeza is None or self.cola is None:
            self.cabeza = self.cola = nuevo_nodo
        else:
            nuevo_nodo.siguiente = self.cabeza
            self.cabeza.anterior = nuevo_nodo
            self.cabeza = nuevo_nodo

    def eliminar(self, dato) -> bool:
        actual = self.cabeza
        while actual is not None:
            if actual.dato == dato:
                if actual.anterior is not None:
                    actual.anterior.siguiente = actual.siguiente
                else:
                    self.cabeza = actual.siguiente

                if actual.siguiente is not None:
                    actual.siguiente.anterior = actual.anterior
                else:
                    self.cola = actual.anterior
                return True
            actual = actual.siguiente
        return False

    def mostrar(self) -> Iterator:
        actual = self.cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente


class CarritoCompras(SujetoObservable):
    def __init__(self):
        super().__init__()
        self._productos = []
        self._estrategia_descuento = None

    def agregar_producto(self, producto):
        self._productos.append(producto)
        self.notificar_observadores(f"Producto '{producto.nombre}' añadido.")

    def eliminar_producto(self, indice: int):
        if 0 <= indice < len(self._productos):
            eliminado = self._productos.pop(indice)
            self.notificar_observadores(f"Producto '{eliminado.nombre}' eliminado.")
            return True
        return False

    def establecer_estrategia_descuento(self, estrategia):
        self._estrategia_descuento = estrategia
        self.notificar_observadores("Estrategia de descuento actualizada.")

    def obtener_productos(self):
        return self._productos

    def calcular_subtotal(self) -> float:
        return sum(p.obtener_precio_final() for p in self._productos)

    def calcular_total(self) -> float:
        subtotal = self.calcular_subtotal()
        if self._estrategia_descuento:
            return self._estrategia_descuento.calcular(subtotal)
        return subtotal