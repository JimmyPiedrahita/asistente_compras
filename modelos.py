# PATRÓN 1: FACTORY METHOD 

class Producto:
    """Clase base para todos los productos."""
    def __init__(self, nombre: str, precio: float, marca: str = "Generica",
                 categoria: str = "General"):
        self.nombre = nombre
        self.precio = precio
        self.marca = marca
        self.categoria = categoria

    def obtener_precio_final(self) -> float:
        return self.precio

    def __str__(self):
        return f"{self.nombre} - ${self.obtener_precio_final():.2f}"


class ProductoFisico(Producto):
    """Producto físico que requiere costo de envío."""
    def __init__(self, nombre: str, precio: float, costo_envio: float = 5.0,
                 marca: str = "Generica", categoria: str = "General"):
        super().__init__(nombre, precio, marca, categoria)
        self.costo_envio = costo_envio

    def obtener_precio_final(self) -> float:
        return self.precio + self.costo_envio


class ProductoDigital(Producto):
    """Producto digital sin costo de envío."""
    def obtener_precio_final(self) -> float:
        return self.precio


class ProductoSuscripcion(Producto):
    """Producto por suscripción recurrente."""
    def __init__(self, nombre: str, precio_mensual: float, meses: int = 1,
                 marca: str = "Generica", categoria: str = "General"):
        super().__init__(nombre, precio_mensual, marca, categoria)
        self.meses = meses

    def obtener_precio_final(self) -> float:
        return self.precio * self.meses


class FabricaProductos:
    """La Fábrica centraliza la instanciación de objetos según el tipo."""
    @staticmethod
    def crear_producto(tipo: str, nombre: str, precio: float, **kwargs) -> Producto:
        tipo_norm = tipo.lower().strip()
        if tipo_norm in ("normal", ""):
            return Producto(nombre, precio)
        if tipo_norm == "fisico":
            costo_envio = kwargs.get("costo_envio", 5.0)
            return ProductoFisico(nombre, precio, costo_envio)
        if tipo_norm == "digital":
            return ProductoDigital(nombre, precio)
        if tipo_norm == "suscripcion":
            meses = kwargs.get("meses", 1)
            return ProductoSuscripcion(nombre, precio, meses)
        raise ValueError(f"Tipo de producto no soportado: {tipo}")


class Almacen:
    """Almacén con inventario en una lista simplemente enlazada."""
    def __init__(self, id_almacen: int, nombre: str):
        from listas import ListaSimple
        self.id_almacen = id_almacen
        self.nombre = nombre
        self.inventario = ListaSimple()


class GestorAlmacenes:
    """Gestiona la colección de almacenes del sistema."""
    def __init__(self):
        self.almacenes = []

    def agregar_almacen(self, almacen: Almacen):
        self.almacenes.append(almacen)

    def obtener_almacenes(self) -> list:
        return self.almacenes


# PATRÓN 2: OBSERVER 

class SujetoObservable:
    """Mantiene una lista de observadores y los notifica al cambiar."""
    def __init__(self):
        self._observadores = []

    def agregar_observador(self, observador):
        if observador not in self._observadores:
            self._observadores.append(observador)

    def remover_observador(self, observador):
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar_observadores(self, mensaje: str = ""):
        for obs in self._observadores:
            obs.actualizar(self, mensaje)