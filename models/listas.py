from typing import Iterator, Optional

from observer import SujetoObservable


class NodoSimple:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente: Optional['NodoSimple'] = None


class ListaSimple:
    """Lista simplemente enlazada con acceso por índice (para inventarios)."""

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

    def obtener(self, indice: int):
        if indice < 0:
            indice += len(self)
        for posicion, dato in enumerate(self.mostrar()):
            if posicion == indice:
                return dato
        raise IndexError(f"Índice fuera de rango: {indice}")

    def reemplazar(self, indice: int, dato) -> bool:
        if indice < 0:
            indice += len(self)
        actual = self.cabeza
        posicion = 0
        while actual is not None:
            if posicion == indice:
                actual.dato = dato
                return True
            actual = actual.siguiente
            posicion += 1
        return False

    def mostrar(self) -> Iterator:
        actual = self.cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente

    def __iter__(self):
        return self.mostrar()

    def __len__(self) -> int:
        total = 0
        actual = self.cabeza
        while actual is not None:
            total += 1
            actual = actual.siguiente
        return total


class Nodo:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente: Optional['Nodo'] = None
        self.anterior: Optional['Nodo'] = None


class ListaDoblementeEnlazada:
    """Lista doblemente enlazada: lista de compras del usuario."""

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

    def obtener(self, indice: int):
        if indice < 0:
            indice += len(self)
        for posicion, dato in enumerate(self.mostrar()):
            if posicion == indice:
                return dato
        raise IndexError(f"Índice fuera de rango: {indice}")

    def mostrar(self) -> Iterator:
        actual = self.cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente

    def __iter__(self):
        return self.mostrar()

    def __len__(self) -> int:
        total = 0
        actual = self.cabeza
        while actual is not None:
            total += 1
            actual = actual.siguiente
        return total


class CarritoCompras(SujetoObservable):
    """Carrito observable: notifica a la vista en cada cambio."""

    def __init__(self):
        super().__init__()
        self._productos = []
        self._estrategia_descuento = None

    def agregar_producto(self, producto):
        self._productos.append(producto)
        self.notificar_observadores(f"Producto '{producto.nombre}' añadido.")

    def eliminar_producto(self, indice: int) -> bool:
        if 0 <= indice < len(self._productos):
            eliminado = self._productos.pop(indice)
            self.notificar_observadores(f"Producto '{eliminado.nombre}' eliminado.")
            return True
        return False

    def vaciar(self):
        self._productos.clear()
        self.notificar_observadores("Carrito vaciado.")

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
