import copy

# PATRÓN 1: FACTORY METHOD


def normalizar_texto(texto) -> str:
    """Normaliza nombres/marcas para comparaciones tolerantes a mayúsculas."""
    return str(texto or "").strip().lower()


class Producto:
    """Clase base para todos los productos."""
    tipo = "normal"

    def __init__(self, nombre: str, precio: float, marca: str = "Generica",
                 categoria: str = "General"):
        self.nombre = nombre
        self.precio = precio
        self.marca = marca
        self.categoria = categoria

    def obtener_precio_final(self) -> float:
        return self.precio

    def clonar(self):
        """Copia independiente: editar el inventario no altera el carrito."""
        return copy.deepcopy(self)

    def __str__(self):
        return f"{self.nombre} ({self.marca}) - ${self.obtener_precio_final():.2f}"


class ProductoFisico(Producto):
    """Producto físico que requiere costo de envío."""
    tipo = "fisico"

    def __init__(self, nombre: str, precio: float, costo_envio: float = 5.0,
                 marca: str = "Generica", categoria: str = "General"):
        super().__init__(nombre, precio, marca, categoria)
        self.costo_envio = costo_envio

    def obtener_precio_final(self) -> float:
        return self.precio + self.costo_envio


class ProductoDigital(Producto):
    """Producto digital sin costo de envío."""
    tipo = "digital"

    def obtener_precio_final(self) -> float:
        return self.precio


class ProductoSuscripcion(Producto):
    """Producto por suscripción recurrente."""
    tipo = "suscripcion"

    def __init__(self, nombre: str, precio_mensual: float, meses: int = 1,
                 marca: str = "Generica", categoria: str = "General"):
        super().__init__(nombre, precio_mensual, marca, categoria)
        self.meses = meses

    def obtener_precio_final(self) -> float:
        return self.precio * self.meses


class FabricaProductos:
    """La Fábrica centraliza la instanciación de objetos según el tipo."""

    @staticmethod
    def crear_producto(tipo: str, nombre: str, precio: float,
                        marca: str = "Generica", categoria: str = "General",
                        **kwargs) -> Producto:
        tipo_norm = normalizar_texto(tipo) or "normal"
        nombre = str(nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre del producto no puede estar vacío")
        precio = float(precio)
        if precio < 0:
            raise ValueError("El precio no puede ser negativo")

        if tipo_norm in ("normal", "producto", ""):
            return Producto(nombre, precio, marca, categoria)

        if tipo_norm == "fisico":
            costo_envio = float(kwargs.get("costo_envio", 5.0))
            if costo_envio < 0:
                raise ValueError("El costo de envío no puede ser negativo")
            return ProductoFisico(nombre, precio, costo_envio, marca, categoria)

        if tipo_norm == "digital":
            return ProductoDigital(nombre, precio, marca, categoria)

        if tipo_norm == "suscripcion":
            meses = int(kwargs.get("meses", 1))
            if meses < 1:
                raise ValueError("Los meses deben ser al menos 1")
            return ProductoSuscripcion(nombre, precio, meses, marca, categoria)

        raise ValueError(f"Tipo de producto no soportado: {tipo}")
