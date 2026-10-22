from listas import CarritoCompras
from interfaz import InterfazUsuario
from controlador import ControladorCompras
from permisos import mostrar_matriz_permisos, mostrar_relaciones_sistema

# PATRÓN 5: BOOTSTRAPPER

def main():
    mostrar_matriz_permisos()
    print()
    mostrar_relaciones_sistema()
    print()

    # Inicialización del Modelo y la Vista
    carrito_model = CarritoCompras()
    vista_ui = InterfazUsuario()

    # Inicialización del Controlador con sus dependencias
    controlador = ControladorCompras(carrito_model, vista_ui)
    vista_ui.set_controlador(controlador)

    # Arrancar la aplicación (Interfaz Gráfica)
    vista_ui.ejecutar()

if __name__ == "__main__":
    main()