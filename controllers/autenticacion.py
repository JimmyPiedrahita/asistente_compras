"""Registro, inicio de sesión y cierre de sesión."""

from __future__ import annotations

from core.errors import CredencialesInvalidas, SolicitudInvalida
from core.logging import obtener_logger
from infrastructure.mongodb.repositorio import RepositorioMongo
from models.permisos import CLIENTE
from models.seguridad import Usuario, es_email_valido, verificar_password

from .sesiones import RegistroSesiones, Sesion

logger = obtener_logger("asistente_compras.autenticacion")


class ControladorAutenticacion:
    def __init__(self, repositorio: RepositorioMongo, registro: RegistroSesiones) -> None:
        self.repo = repositorio
        self.registro = registro

    def registrar_cliente(self, datos: dict[str, object]) -> Sesion:
        nombre = str(datos.get("nombre") or "").strip()
        email = str(datos.get("email") or "").strip().lower()
        password = str(datos.get("password") or "")
        confirmacion = str(datos.get("password_confirmacion") or "")
        telefono = str(datos.get("telefono") or "").strip()
        direccion = str(datos.get("direccion") or "").strip()
        ciudad = str(datos.get("ciudad") or "").strip()
        autoriza = bool(datos.get("autoriza_datos"))

        if not nombre:
            raise SolicitudInvalida("El nombre es obligatorio")
        if not es_email_valido(email):
            raise SolicitudInvalida("El correo electrónico no es válido")
        if len(password) < 6:
            raise SolicitudInvalida("La contraseña debe tener al menos 6 caracteres")
        if password != confirmacion:
            raise SolicitudInvalida("La contraseña y su confirmación no coinciden")
        if not telefono or not direccion or not ciudad:
            raise SolicitudInvalida("El teléfono, la dirección y la ciudad son obligatorios")
        if not autoriza:
            raise SolicitudInvalida(
                "Debes autorizar el tratamiento de tus datos personales para registrarte"
            )

        usuario = self.repo.crear_usuario(
            nombre=nombre,
            email=email,
            password=password,
            rol=CLIENTE,
            telefono=telefono,
            direccion=direccion,
            ciudad=ciudad,
            autoriza_datos=True,
        )
        logger.info("Cliente registrado: %s", email)
        return self.registro.crear(usuario)

    def iniciar_sesion(self, email: str, password: str) -> Sesion:
        usuario = self.repo.buscar_usuario_por_email(email)
        if (
            usuario is None
            or not usuario.activo
            or not verificar_password(password, usuario.password_hash)
        ):
            logger.warning("Inicio de sesión rechazado: %s", str(email)[:120])
            raise CredencialesInvalidas("Credenciales incorrectas")
        logger.info("Inicio de sesión: %s (%s)", usuario.email, usuario.rol)
        return self.registro.crear(usuario)

    def cerrar_sesion(self, token: str) -> None:
        self.registro.eliminar(token)

    def usuario_actual(self, sesion: Sesion) -> Usuario | None:
        return self.repo.obtener_usuario(sesion.usuario_id)


__all__ = ["ControladorAutenticacion"]
