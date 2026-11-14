"""Sesiones autenticadas en memoria."""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from models.carrito import Carrito
from models.seguridad import Usuario


@dataclass
class Sesion:
    token: str
    usuario_id: str
    nombre: str
    email: str
    rol: str
    almacen_id: str | None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    autoriza_datos: bool = False
    carrito: Carrito = field(default_factory=Carrito)
    lista: list[str] = field(default_factory=list)
    creada_en: float = 0.0
    ultimo_acceso: float = 0.0

    def publica(self) -> dict[str, object]:
        return {
            "session_id": self.token,
            "usuario_id": self.usuario_id,
            "usuario": self.nombre,
            "email": self.email,
            "rol": self.rol,
            "almacen_id": self.almacen_id,
            "telefono": self.telefono,
            "direccion": self.direccion,
            "ciudad": self.ciudad,
        }


class RegistroSesiones:
    def __init__(
        self,
        *,
        ttl_seconds: int = 3600,
        max_sesiones: int = 1000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_seconds = int(ttl_seconds)
        self._max_sesiones = int(max_sesiones)
        self._clock = clock
        self._sesiones: dict[str, Sesion] = {}
        self._candado = threading.RLock()

    def crear(self, usuario: Usuario) -> Sesion:
        with self._candado:
            self._limpiar_expiradas_locked()
            if len(self._sesiones) >= self._max_sesiones:
                self._expulsar_mas_antigua_locked()
            ahora = self._clock()
            sesion = Sesion(
                token=secrets.token_urlsafe(32),
                usuario_id=usuario.usuario_id,
                nombre=usuario.nombre,
                email=usuario.email,
                rol=usuario.rol,
                almacen_id=usuario.almacen_id,
                telefono=usuario.telefono,
                direccion=usuario.direccion,
                ciudad=usuario.ciudad,
                autoriza_datos=usuario.autoriza_datos,
                creada_en=ahora,
                ultimo_acceso=ahora,
            )
            self._sesiones[sesion.token] = sesion
            return sesion

    def obtener(self, token: str) -> Sesion | None:
        with self._candado:
            sesion = self._sesiones.get(str(token))
            if sesion is None:
                return None
            ahora = self._clock()
            if ahora - sesion.ultimo_acceso >= self._ttl_seconds:
                del self._sesiones[sesion.token]
                return None
            sesion.ultimo_acceso = ahora
            return sesion

    def eliminar(self, token: str) -> None:
        with self._candado:
            self._sesiones.pop(str(token), None)

    def limpiar_expiradas(self) -> int:
        with self._candado:
            return self._limpiar_expiradas_locked()

    def _limpiar_expiradas_locked(self) -> int:
        ahora = self._clock()
        expiradas = [
            token
            for token, sesion in self._sesiones.items()
            if ahora - sesion.ultimo_acceso >= self._ttl_seconds
        ]
        for token in expiradas:
            del self._sesiones[token]
        return len(expiradas)

    def _expulsar_mas_antigua_locked(self) -> None:
        if not self._sesiones:
            return
        token = min(self._sesiones, key=lambda clave: self._sesiones[clave].ultimo_acceso)
        del self._sesiones[token]

    def __len__(self) -> int:
        with self._candado:
            return len(self._sesiones)


__all__ = ["RegistroSesiones", "Sesion"]
