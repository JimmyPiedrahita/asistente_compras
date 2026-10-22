"""Prueba de humo de la interfaz Tkinter (sin interacción manual).

Requiere un display. En un servidor sin pantalla usar: xvfb-run python3 pruebas_gui.py
"""

import sys
import tkinter as tk
from tkinter import ttk

from controlador import ControladorCompras
from interfaz import InterfazUsuario
from listas import CarritoCompras


def descendientes(widget):
    for hijo in widget.winfo_children():
        yield hijo
        yield from descendientes(hijo)


def buscar(widget, texto):
    for candidato in descendientes(widget):
        try:
            if candidato.cget("text") == texto:
                return candidato
        except tk.TclError:
            continue
    raise LookupError(f"No se encontró el widget con texto {texto!r}")


def primeros(widget, clase, cantidad=None):
    encontrados = [w for w in descendientes(widget) if isinstance(w, clase)]
    return encontrados if cantidad is None else encontrados[:cantidad]


def entradas_de(widget):
    """Entry reales: ttk.Combobox hereda de ttk.Entry y no debe contarse."""
    return [w for w in descendientes(widget) if type(w) is ttk.Entry]


def main():
    carrito = CarritoCompras()
    vista = InterfazUsuario()
    controlador = ControladorCompras(carrito, vista)
    vista.set_controlador(controlador)

    vista.root = tk.Tk()
    vista.root.withdraw()
    vista.root.geometry("1000x700")
    ttk.Style(vista.root).theme_use("clam")

    # 1. Menú principal
    vista._mostrar_menu_principal()
    vista.root.update()
    buscar(vista.root, "Ingresar como Usuario")
    buscar(vista.root, "Administrar Almacenes")

    # 2. Login admin (pantalla)
    vista._mostrar_login_admin()
    vista.root.update()
    buscar(vista.root, "Ingresar")

    # 3. Panel admin: alta y edición de precio
    assert controlador.login_admin("admin123")
    vista._mostrar_menu_admin()
    vista.root.update()
    frame_add = buscar(vista.root, "Agregar producto a un almacén")
    entradas = entradas_de(frame_add)
    assert len(entradas) >= 5
    entradas[0].insert(0, "Arroz")
    entradas[1].insert(0, "MarcaX")
    entradas[2].insert(0, "Comida")
    entradas[3].insert(0, "250")
    buscar(frame_add, "Guardar producto").invoke()
    vista.root.update()

    almacen_1 = controlador.gestor_almacenes.obtener_almacen(1)
    assert len(almacen_1.inventario) == 1, "El alta desde la GUI no insertó el producto"

    frame_inv = buscar(vista.root, "Inventario de almacenes")
    listboxes = primeros(frame_inv, tk.Listbox)
    assert len(listboxes) == 3
    assert listboxes[0].size() == 1
    listboxes[0].selection_set(0)
    entradas_precio = entradas_de(frame_inv)
    entradas_precio[0].insert(0, "200")
    buscar(frame_inv, "Actualizar").invoke()
    vista.root.update()
    assert almacen_1.inventario.obtener(0).precio == 200

    # 4. Pantalla de usuario y flujo de lista/búsqueda/carrito
    controlador.cerrar_sesion()
    controlador.registrar_usuario("Ana")
    assert controlador.iniciar_sesion("Ana")
    vista._mostrar_menu_usuario()
    vista.root.update()

    frame_lista = buscar(vista.root, "Mi lista de compras")
    entrada_producto = entradas_de(frame_lista)[0]
    entrada_producto.insert(0, "Arroz")
    buscar(frame_lista, "Agregar").invoke()
    vista.root.update()
    assert controlador.obtener_compras_usuario() == ["Arroz"]

    frame_busqueda = buscar(vista.root, "Buscar en almacenes")
    buscar(frame_busqueda, "Buscar").invoke()
    vista.root.update()
    resultados = primeros(frame_busqueda, tk.Listbox)[0]
    assert resultados.size() >= 2, "La búsqueda no pintó resultados"
    resultados.selection_set(1)
    buscar(frame_busqueda, "Agregar al carrito").invoke()
    vista.root.update()
    assert len(carrito.obtener_productos()) == 1, "No se agregó al carrito"
    assert buscar(vista.root, "Total: $200.00")

    frame_carrito = buscar(vista.root, "Mi carrito")
    combo = primeros(frame_carrito, ttk.Combobox)[0]
    combo.set("Porcentaje (%)")
    entrada_descuento = entradas_de(frame_carrito)[0]
    entrada_descuento.insert(0, "10")
    buscar(frame_carrito, "Aplicar").invoke()
    vista.root.update()
    assert abs(carrito.calcular_total() - 180) < 1e-9
    assert buscar(vista.root, "Total: $180.00")

    carrito_listbox = primeros(frame_carrito, tk.Listbox)[0]
    carrito_listbox.selection_set(0)
    buscar(frame_carrito, "Quitar del carrito").invoke()
    vista.root.update()
    assert not carrito.obtener_productos()

    # 5. Volver al menú cierra la sesión
    buscar(vista.root, "Cerrar sesión y volver").invoke()
    vista.root.update()
    assert controlador.obtener_rol() == "INVITADO"

    vista.root.destroy()
    print("OK: prueba de humo de la GUI completada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
