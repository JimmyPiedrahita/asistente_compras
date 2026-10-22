from listas import ListaDoblementeEnlazada
from modelos import FabricaProductos, Producto, Almacen, GestorAlmacenes
from estrategias import (SinDescuento, DescuentoPorcentaje, DescuentoFijo,
                         BusquedaMejorPrecioStrategy, BusquedaCatalogoStrategy)

# PATRÓN 4: MODELO_VISTA_CONTROLADOR 

class ControladorCompras:
    def __init__(self, carrito, vista):
        self.carrito = carrito
        self.vista = vista
        self.lista_compras = ListaDoblementeEnlazada()
        self.gestor_almacenes = GestorAlmacenes()
        self.estrategia_busqueda = BusquedaMejorPrecioStrategy()
        self.estrategia_catalogo = BusquedaCatalogoStrategy()
        self._clave_admin = "admin123"

        self._usuarios = []
        self._usuario_actual = None

        for i in range(1, 4):
            self.gestor_almacenes.agregar_almacen(
                Almacen(id_almacen=i, nombre=f"Almacen {i}"))

        # Conectamos la Vista como Observador del Carrito
        self.carrito.agregar_observador(self.vista)

    #  SESIÓN DE USUARIOS =
    def registrar_usuario(self, nombre: str) -> bool:
        nombre = nombre.strip()
        if not nombre or nombre in self._usuarios:
            return False
        self._usuarios.append(nombre)
        return True

    def iniciar_sesion(self, nombre: str) -> bool:
        nombre = nombre.strip()
        if nombre in self._usuarios:
            self._usuario_actual = nombre
            return True
        return False

    def obtener_usuario_actual(self):
        return self._usuario_actual

    def cerrar_sesion(self):
        self._usuario_actual = None

    #  LISTA DE COMPRAS DEL USUARIO 
    def agregar_producto_usuario(self, nombre: str):
        nombre = nombre.strip()
        if nombre:
            # Uso de Factory Method
            producto = FabricaProductos.crear_producto("normal", nombre, 0.0)
            self.lista_compras.agregar_al_final(producto.nombre)

    def eliminar_producto_usuario(self, nombre: str) -> bool:
        return self.lista_compras.eliminar(nombre.strip())

    def obtener_compras_usuario(self):
        return list(self.lista_compras.mostrar())

    def login_admin(self, clave: str) -> bool:
        if clave == self._clave_admin:
            self._usuario_actual = "ADMIN"
            return True
        return False

    #  ADMINISTRACIÓN DE ALMACENES 
    def agregar_producto_almacen(self, id_almacen: int, nombre: str, precio: float):
        prod = Producto(nombre, float(precio))
        for alm in self.gestor_almacenes.obtener_almacenes():
            if alm.id_almacen == id_almacen:
                alm.inventario.agregar(prod)
                break

    def ejecutar_busqueda_precios(self):
        return self.estrategia_busqueda.buscar(self.lista_compras,
                                               self.gestor_almacenes)

    def ejecutar_catalogo(self):
        return self.estrategia_catalogo.buscar(self.lista_compras,
                                               self.gestor_almacenes)

    def obtener_catalogo_global(self) -> list:
        regs = []
        for alm in self.gestor_almacenes.obtener_almacenes():
            for p in alm.inventario.mostrar():
                regs.append({"producto": p, "almacen": alm})
        return regs

    def agregar_seleccion_al_carrito(self, nombre: str, marca: str,
                                     id_almacen: int):
        nombre_l = nombre.strip().lower()
        for alm in self.gestor_almacenes.obtener_almacenes():
            if alm.id_almacen == id_almacen:
                for p in alm.inventario.mostrar():
                    if (p.nombre.lower() == nombre_l
                            and p.marca.lower() == marca.strip().lower()):
                        self.carrito.agregar_producto(
                            Producto(p.nombre, p.precio, p.marca, p.categoria))
                        return True
        return False

    #  MODO CONSOLA (alternativo a la GUI) 
    def ejecutar(self):
        while True:
            self.vista.mostrar_menu()
            opcion = input("Elija una opción: ").strip()

            if opcion == "1":
                self.agregar_producto()
            elif opcion == "2":
                self.mostrar_carrito()
            elif opcion == "3":
                self.eliminar_producto()
            elif opcion == "4":
                self.aplicar_descuento()
            elif opcion == "5":
                print("\n¡Gracias por usar el Asistente de Compras!")
                break
            else:
                print("\nOpción no válida. Intente de nuevo.")

    def agregar_producto(self):
        try:
            tipo = self.vista.solicitar_tipo_producto()
            nombre, precio = self.vista.solicitar_datos_producto()
            
            kwargs = {}
            if tipo == "fisico":
                costo_envio = float(input("Costo de envío [defecto 5.0]: ") or "5.0")
                kwargs["costo_envio"] = costo_envio
            elif tipo == "suscripcion":
                meses = int(input("Número de meses [defecto 1]: ") or "1")
                kwargs["meses"] = meses

            # Uso de Factory Method
            producto = FabricaProductos.crear_producto(tipo, nombre, precio, **kwargs)
            self.carrito.agregar_producto(producto)

        except Exception as e:
            print(f"\nError al agregar el producto: {e}")

    def mostrar_carrito(self):
        productos = self.carrito.obtener_productos()
        subtotal = self.carrito.calcular_subtotal()
        total = self.carrito.calcular_total()
        self.vista.mostrar_carrito(productos, subtotal, total)

    def eliminar_producto(self):
        self.mostrar_carrito()
        if not self.carrito.obtener_productos():
            return
        try:
            idx = int(input("Número de producto a eliminar: ")) - 1
            if not self.carrito.eliminar_producto(idx):
                print("Índice inválido.")
        except ValueError:
            print("Por favor ingrese un número válido.")

    def aplicar_descuento(self):
        opcion = self.vista.solicitar_estrategia_descuento()
        # Uso del patrón Strategy
        if opcion == "1":
            estrategia = SinDescuento()
        elif opcion == "2":
            pct = float(input("Porcentaje de descuento (ej: 15): "))
            estrategia = DescuentoPorcentaje(pct)
        elif opcion == "3":
            monto = float(input("Monto fijo a descontar ($): "))
            estrategia = DescuentoFijo(monto)
        else:
            print("Opción inválida.")
            return

        self.carrito.establecer_estrategia_descuento(estrategia)