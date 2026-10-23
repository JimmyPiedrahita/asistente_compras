"""Persistencia del inventario en MongoDB.

La aplicación solo escribe en la base dedicada de cada almacén. La colección
``comparador.productos`` es una proyección mantenida por ``listener_mongodb``.
"""

from modelos import FabricaProductos


class MongoInventarioRepository:
    def __init__(self, uri: str, base_comparador: str = "comparador"):
        try:
            from pymongo import MongoClient
        except ImportError as error:
            raise RuntimeError(
                "MongoDB requiere instalar pymongo (pip install -r requirements.txt)"
            ) from error

        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.client.admin.command("ping")
        self.base_comparador = base_comparador
        self.client[base_comparador].productos.create_index(
            [("nombre_normalizado", 1), ("almacen_id", 1)]
        )

    def _coleccion(self, id_almacen: int):
        return self.client[f"almacen_{id_almacen}"].productos

    @staticmethod
    def _documento(producto):
        documento = {
            "_id": producto.producto_id,
            "producto_id": producto.producto_id,
            "nombre": producto.nombre,
            "nombre_normalizado": producto.nombre.strip().lower(),
            "marca": producto.marca,
            "categoria": producto.categoria,
            "tipo": producto.tipo,
            "precio": producto.precio,
        }
        if producto.tipo == "fisico":
            documento["costo_envio"] = producto.costo_envio
        elif producto.tipo == "suscripcion":
            documento["meses"] = producto.meses
        return documento

    @staticmethod
    def _producto(documento):
        extra = {}
        if documento.get("tipo") == "fisico":
            extra["costo_envio"] = documento.get("costo_envio", 5.0)
        elif documento.get("tipo") == "suscripcion":
            extra["meses"] = documento.get("meses", 1)
        return FabricaProductos.crear_producto(
            documento.get("tipo", "normal"),
            documento["nombre"],
            documento["precio"],
            marca=documento.get("marca", "Generica"),
            categoria=documento.get("categoria", "General"),
            producto_id=str(documento.get("producto_id", documento["_id"])),
            **extra,
        )

    def cargar_almacen(self, id_almacen: int):
        return [self._producto(doc) for doc in self._coleccion(id_almacen).find()]

    def cargar_comparador(self):
        productos = {}
        for doc in self.client[self.base_comparador].productos.find():
            productos.setdefault(int(doc["almacen_id"]), []).append(self._producto(doc))
        return productos

    def insertar(self, id_almacen: int, producto):
        self._coleccion(id_almacen).insert_one(self._documento(producto))

    def actualizar(self, id_almacen: int, producto):
        resultado = self._coleccion(id_almacen).replace_one(
            {"_id": producto.producto_id}, self._documento(producto)
        )
        if resultado.matched_count != 1:
            raise KeyError(f"Producto no encontrado: {producto.producto_id}")

    def close(self):
        self.client.close()
