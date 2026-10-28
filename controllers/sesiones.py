"""Registro de sesiones HTTP con TTL, límite y protección para concurrencia."""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from core.observer import Observador, ObservadorNulo
from models.almacenes import GestorAlmacenes

from .compras import ControladorCompras


@dataclass
class Sesion:
    token: str
    controlador: ControladorCompras
    creada_en: float
    ultimo_acceso: float
    datos: dict[str, object] = field(default_factory=dict)


class RegistroSesiones:
    def __init__(
        self,
        gestor_almacenes: GestorAlmacenes,
        *,
        admin_clave: str,
        ttl_seconds: int = 3600,
        max_sesiones: int = 1000,
        max_csv_bytes: int = 1_000_000,
        clock: Callable[[], float] = time.monotonic,
        vista_factory: Callable[[], Observador] = ObservadorNulo,
    ) -> None:
        self._gestor_almacenes = gestor_almacenes
        self._admin_clave = admin_clave
        self._ttl_seconds = int(ttl_seconds)
        self._max_sesiones = int(max_sesiones)
        self._max_csv_bytes = int(max_csv_bytes)
        self._clock = clock
        self._vista_factory = vista_factory
        self._sesiones: dict[str, Sesion] = {}
        self._candado = threading.RLock()

    def crear(self) -> Sesion:
        with self._candado:
            self._limpiar_expiradas_locked()
            if len(self._sesiones) >= self._max_sesiones:
                self._expulsar_mas_antigua_locked()

            token = secrets.token_urlsafe(32)
            controlador = ControladorCompras(
                gestor_almacenes=self._gestor_almacenes,
                clave_admin=self._admin_clave,
                max_csv_bytes=self._max_csv_bytes,
                vista=self._vista_factory(),
            )
            ahora = self._clock()
            sesion = Sesion(
                token=token,
                controlador=controlador,
                creada_en=ahora,
                ultimo_acceso=ahora,
            )
            self._sesiones[token] = sesion
            return sesion

    def obtener(self, token: str) -> Sesion | None:
        with self._candado:
            sesion = self._sesiones.get(token)
            if sesion is None:
                return None
            ahora = self._clock()
            if ahora - sesion.ultimo_acceso >= self._ttl_seconds:
                del self._sesiones[token]
                return None
            sesion.ultimo_acceso = ahora
            return sesion

    def eliminar(self, token: str) -> None:
        with self._candado:
            self._sesiones.pop(token, None)

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
        token = min(
            self._sesiones,
            key=lambda clave: self._sesiones[clave].ultimo_acceso,
        )
        del self._sesiones[token]

    def obtener_almacenes(self):
        return self._gestor_almacenes.obtener_almacenes()

    def __len__(self) -> int:
        with self._candado:
            return len(self._sesiones)


__all__ = ["RegistroSesiones", "Sesion"]
