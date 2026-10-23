import argparse
import os

from controlador import ControladorCompras
from interfaz import InterfazUsuario
from listas import CarritoCompras
from permisos import mostrar_matriz_permisos, mostrar_relaciones_sistema
from almacenes import GestorAlmacenes
from persistencia_mongodb import MongoInventarioRepository

# PATRÓN 5: BOOTSTRAPPER


def main():
    parser = argparse.ArgumentParser(description="Asistente de Compras Inteligente")
    parser.add_argument("--consola", action="store_true",
                        help="Usar el menú de consola en vez de la interfaz gráfica")
    parser.add_argument("--sin-banner", action="store_true",
                        help="No imprimir la matriz de permisos ni las relaciones")
    args = parser.parse_args()

    if not args.sin_banner:
        mostrar_matriz_permisos()
        print()
        mostrar_relaciones_sistema()
        print()

    persistencia = None
    mongo_uri = os.getenv("MONGODB_URI")
    if mongo_uri:
        persistencia = MongoInventarioRepository(mongo_uri)

    # Inicialización del Modelo y la Vista
    carrito_model = CarritoCompras()
    vista_ui = InterfazUsuario()

    # Inicialización del Controlador con sus dependencias
    controlador = ControladorCompras(carrito_model, vista_ui,
                                     gestor_almacenes=GestorAlmacenes(persistencia))
    vista_ui.set_controlador(controlador)

    # Arrancar la aplicación
    if args.consola:
        controlador.ejecutar()
    else:
        vista_ui.ejecutar()


if __name__ == "__main__":
    main()
