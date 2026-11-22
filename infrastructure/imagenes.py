"""Almacenamiento de imágenes de producto en Cloudinary.

La API nunca expone las credenciales de Cloudinary: recibe el archivo, valida
su tamaño y su tipo real y lo sube desde el servidor. En MongoDB solo se
guardan la URL pública y el identificador público del activo.
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from core.config import Settings
from core.errors import ServicioNoDisponible, SolicitudInvalida

TIPOS_PERMITIDOS = frozenset({"image/jpeg", "image/png", "image/webp"})


def detectar_tipo_imagen(contenido: bytes) -> str | None:
    """Devuelve el MIME real del archivo según sus primeros bytes."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(contenido) >= 12 and contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    return None


def _texto_tamano(bytes_maximos: int) -> str:
    if bytes_maximos >= 1024 * 1024:
        valor = bytes_maximos / (1024 * 1024)
        return f"{valor:.0f} MB" if valor.is_integer() else f"{valor:.1f} MB"
    return f"{bytes_maximos / 1024:.0f} KB"


class ClienteImagenes(Protocol):
    """Contrato mínimo del cliente de almacenamiento de imágenes."""

    def subir(self, contenido: bytes, *, carpeta: str, public_id: str) -> dict[str, Any]:
        """Sube el archivo y devuelve ``url`` y ``public_id``."""

    def eliminar(self, public_id: str) -> None:
        """Elimina un activo por su identificador público."""


class CargadorCloudinary:
    """Adaptador del SDK oficial de Cloudinary."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str) -> None:
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self._configurado = False

    def _modulo(self) -> Any:
        try:
            import cloudinary
        except ImportError as error:  # pragma: no cover - depende del entorno
            raise ServicioNoDisponible(
                "La biblioteca de Cloudinary no está instalada en el servidor"
            ) from error
        if not self._configurado:
            cloudinary.config(
                cloud_name=self.cloud_name,
                api_key=self.api_key,
                api_secret=self.api_secret,
                secure=True,
            )
            self._configurado = True
        return cloudinary

    def subir(self, contenido: bytes, *, carpeta: str, public_id: str) -> dict[str, Any]:
        self._modulo()
        try:
            from cloudinary import uploader
            from cloudinary.utils import cloudinary_url

            respuesta = uploader.upload(
                contenido,
                folder=carpeta,
                public_id=public_id,
                resource_type="image",
                overwrite=False,
                unique_filename=False,
                use_filename=False,
                invalidate=True,
            )
            identificador = str(respuesta.get("public_id") or "")
            if not identificador:
                raise ServicioNoDisponible("Cloudinary no devolvió el identificador de la imagen")
            # Versión cuadrada optimizada: 600x600, encuadre automático y
            # entrega en WebP con la mejor calidad posible.
            url, _ = cloudinary_url(
                identificador,
                resource_type="image",
                width=600,
                height=600,
                crop="fill",
                gravity="auto",
                fetch_format="webp",
                quality="auto",
                secure=True,
            )
        except ServicioNoDisponible:
            raise
        except Exception as error:
            raise ServicioNoDisponible("No se pudo subir la imagen a Cloudinary") from error
        return {"url": str(url), "public_id": identificador}

    def eliminar(self, public_id: str) -> None:
        self._modulo()
        try:
            from cloudinary import uploader

            uploader.destroy(public_id, resource_type="image", invalidate=True)
        except Exception as error:
            raise ServicioNoDisponible("No se pudo eliminar la imagen en Cloudinary") from error


class ServicioImagenesProducto:
    """Valida, sube y elimina imágenes de producto."""

    def __init__(
        self,
        *,
        cloud_name: str = "",
        api_key: str = "",
        api_secret: str = "",
        carpeta: str = "asistente-compras",
        max_bytes: int = 2_000_000,
        cliente: ClienteImagenes | None = None,
    ) -> None:
        self.carpeta = str(carpeta or "").strip().strip("/") or "asistente-compras"
        self.max_bytes = int(max_bytes)
        credenciales = all((cloud_name, api_key, api_secret))
        if cliente is not None:
            self._cliente: ClienteImagenes | None = cliente
        elif credenciales:
            self._cliente = CargadorCloudinary(cloud_name, api_key, api_secret)
        else:
            self._cliente = None

    @classmethod
    def desde_settings(cls, settings: Settings) -> ServicioImagenesProducto:
        return cls(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            carpeta=settings.cloudinary_folder,
            max_bytes=settings.max_product_image_bytes,
        )

    @property
    def configurado(self) -> bool:
        return self._cliente is not None

    def _exigir_configurado(self) -> ClienteImagenes:
        if self._cliente is None:
            raise ServicioNoDisponible(
                "La carga de imágenes no está configurada. Define CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY y CLOUDINARY_API_SECRET."
            )
        return self._cliente

    def validar(self, contenido: bytes) -> str:
        """Valida tamaño y tipo real; devuelve el MIME detectado."""
        if not contenido:
            raise SolicitudInvalida("El archivo de imagen está vacío")
        if len(contenido) > self.max_bytes:
            raise SolicitudInvalida(
                f"La imagen supera el tamaño máximo de {_texto_tamano(self.max_bytes)}"
            )
        tipo = detectar_tipo_imagen(contenido)
        if tipo not in TIPOS_PERMITIDOS:
            raise SolicitudInvalida(
                "Formato de imagen no permitido. Usa una imagen JPEG, PNG o WebP."
            )
        return tipo

    def subir(self, *, almacen_id: str, producto_id: str, contenido: bytes) -> dict[str, str]:
        cliente = self._exigir_configurado()
        self.validar(contenido)
        public_id = f"{almacen_id}-{producto_id}-{uuid.uuid4().hex[:12]}"
        try:
            respuesta = cliente.subir(contenido, carpeta=self.carpeta, public_id=public_id)
        except ServicioNoDisponible:
            raise
        except Exception as error:
            raise ServicioNoDisponible("No se pudo subir la imagen a Cloudinary") from error

        url = str(respuesta.get("url") or "")
        identificador = str(respuesta.get("public_id") or "")
        if not url or not identificador:
            raise ServicioNoDisponible("Cloudinary devolvió una respuesta incompleta")
        return {"imagen_url": url, "imagen_public_id": identificador}

    def eliminar(self, public_id: str) -> None:
        if not public_id:
            return
        cliente = self._exigir_configurado()
        try:
            cliente.eliminar(public_id)
        except ServicioNoDisponible:
            raise
        except Exception as error:
            raise ServicioNoDisponible("No se pudo eliminar la imagen en Cloudinary") from error


__all__ = [
    "TIPOS_PERMITIDOS",
    "CargadorCloudinary",
    "ClienteImagenes",
    "ServicioImagenesProducto",
    "detectar_tipo_imagen",
]
