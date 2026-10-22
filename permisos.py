import time

ROLES = ("INVITADO", "CLIENTE", "ADMIN")

MATRIZ_PERMISOS = {
    "INVITADO": ["ver_menu"],
    "CLIENTE": ["ver_menu", "crear_lista", "agregar_producto",
                "eliminar_producto", "comparar", "exportar"],
    "ADMIN": ["ver_menu", "crear_lista", "agregar_producto",
              "eliminar_producto", "comparar", "exportar",
              "login_admin", "cargar_csv", "editar_precio",
              "gestionar_almacenes"],
}

SEPARADOR = "=" * 72


def mostrar_matriz_permisos():
    print("MATRIZ DE PERMISOS POR ROL")
    print(SEPARADOR)
    for rol in ROLES:
        print(f" {rol:>8}: {', '.join(MATRIZ_PERMISOS[rol])}")
    print(SEPARADOR)


def mostrar_relaciones_sistema():
    print("RELACIONES DEL SISTEMA (MVC + Strategy)")
    print("  InterfazUsuario     --eventos UI-->  ControladorCompras")
    print("  ControladorCompras  --check permiso-->  logger.tiene_permiso")
    print("  ControladorCompras  --invoca-->  EstrategiaBusqueda (Strategy)")
    print("  EstrategiaBusqueda  --consulta-->  GestorAlmacenes")
    print("  GestorAlmacenes     --contiene-->  Almacen.inventario")
    print("  logger.tiene_permiso --consulta-->  MATRIZ_PERMISOS")


class Logger:
    @staticmethod
    def log(etiqueta: str, mensaje: str, detalle: str = None):
        hora = time.strftime('%H:%M:%S')
        linea = f"[{hora}] [{etiqueta:>12}] {mensaje}"
        if detalle:
            linea += f"  ->  {detalle}"
        print(linea)

    @staticmethod
    def tiene_permiso(rol: str, permiso: str) -> bool:
        permitido = rol in MATRIZ_PERMISOS and permiso in MATRIZ_PERMISOS[rol]
        Logger.log(rol, f"CHECK PERMISO '{permiso}'",
                   "CONCEDIDO" if permitido else "DENEGADO")
        return permitido


logger = Logger()