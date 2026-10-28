import time

ROLES = ("INVITADO", "CLIENTE", "ADMIN")

MATRIZ_PERMISOS = {
    "INVITADO": ["ver_menu"],
    "CLIENTE": ["ver_menu", "crear_lista", "agregar_producto",
                "eliminar_producto", "comparar", "exportar",
                "aplicar_descuento"],
    "ADMIN": ["ver_menu", "crear_lista", "agregar_producto",
              "eliminar_producto", "comparar", "exportar",
              "aplicar_descuento", "login_admin", "cargar_csv",
              "editar_precio", "gestionar_almacenes"],
}

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
