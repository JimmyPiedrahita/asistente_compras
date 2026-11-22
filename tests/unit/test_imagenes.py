"""Pruebas del servicio de imágenes de producto."""

from __future__ import annotations

import unittest

from core.config import Settings
from core.errors import ServicioNoDisponible, SolicitudInvalida
from infrastructure.imagenes import (
    ServicioImagenesProducto,
    detectar_tipo_imagen,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"contenido"
JPEG = b"\xff\xd8\xff" + b"contenido"
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"contenido"


class ClienteFalso:
    def __init__(self) -> None:
        self.subidas: list[dict[str, object]] = []
        self.eliminadas: list[str] = []
        self.error: Exception | None = None

    def subir(self, contenido: bytes, *, carpeta: str, public_id: str) -> dict[str, str]:
        if self.error is not None:
            raise self.error
        self.subidas.append({"contenido": contenido, "carpeta": carpeta, "public_id": public_id})
        return {
            "url": f"https://cdn.test/{carpeta}/{public_id}.webp",
            "public_id": f"{carpeta}/{public_id}",
        }

    def eliminar(self, public_id: str) -> None:
        if self.error is not None:
            raise self.error
        self.eliminadas.append(public_id)


class PruebasDeteccion(unittest.TestCase):
    def test_detecta_tipos_permitidos(self) -> None:
        self.assertEqual(detectar_tipo_imagen(PNG), "image/png")
        self.assertEqual(detectar_tipo_imagen(JPEG), "image/jpeg")
        self.assertEqual(detectar_tipo_imagen(WEBP), "image/webp")

    def test_rechaza_otros_contenidos(self) -> None:
        self.assertIsNone(detectar_tipo_imagen(b""))
        self.assertIsNone(detectar_tipo_imagen(b"<svg></svg>"))
        self.assertIsNone(detectar_tipo_imagen(b"GIF89a"))


class PruebasValidacion(unittest.TestCase):
    def setUp(self) -> None:
        self.servicio = ServicioImagenesProducto(max_bytes=32)

    def test_valida_tamano_y_tipo(self) -> None:
        self.assertEqual(self.servicio.validar(PNG), "image/png")
        with self.assertRaises(SolicitudInvalida):
            self.servicio.validar(b"")
        with self.assertRaises(SolicitudInvalida):
            self.servicio.validar(PNG + b"x" * 64)
        with self.assertRaises(SolicitudInvalida):
            self.servicio.validar(b"texto plano")

    def test_sin_credenciales_no_esta_configurado(self) -> None:
        self.assertFalse(self.servicio.configurado)
        with self.assertRaises(ServicioNoDisponible):
            self.servicio.subir(almacen_id="a1", producto_id="p1", contenido=PNG)
        with self.assertRaises(ServicioNoDisponible):
            self.servicio.eliminar("asistente-compras/a1/p1")

    def test_desde_settings(self) -> None:
        settings = Settings.de_pruebas(
            cloudinary_cloud_name="demo",
            cloudinary_api_key="clave",
            cloudinary_api_secret="secreto",
            cloudinary_folder="/tienda/",
            max_product_image_bytes=4096,
        )
        servicio = ServicioImagenesProducto.desde_settings(settings)
        self.assertTrue(servicio.configurado)
        self.assertEqual(servicio.carpeta, "tienda")
        self.assertEqual(servicio.max_bytes, 4096)


class PruebasCarga(unittest.TestCase):
    def setUp(self) -> None:
        self.cliente = ClienteFalso()
        self.servicio = ServicioImagenesProducto(
            carpeta="asistente-compras",
            max_bytes=1024,
            cliente=self.cliente,
        )

    def test_subir_aisla_por_almacen_y_producto(self) -> None:
        resultado = self.servicio.subir(
            almacen_id="almacen-1", producto_id="producto-1", contenido=PNG
        )
        self.assertTrue(resultado["imagen_url"].startswith("https://cdn.test/"))
        self.assertIn("almacen-1-producto-1-", resultado["imagen_public_id"])
        self.assertEqual(len(self.cliente.subidas), 1)
        subida = self.cliente.subidas[0]
        self.assertEqual(subida["carpeta"], "asistente-compras")
        self.assertEqual(subida["contenido"], PNG)

    def test_subidas_generan_identificadores_distintos(self) -> None:
        primera = self.servicio.subir(almacen_id="a1", producto_id="p1", contenido=PNG)
        segunda = self.servicio.subir(almacen_id="a1", producto_id="p1", contenido=PNG)
        self.assertNotEqual(primera["imagen_public_id"], segunda["imagen_public_id"])

    def test_eliminar(self) -> None:
        self.servicio.eliminar("asistente-compras/a1/p1")
        self.assertEqual(self.cliente.eliminadas, ["asistente-compras/a1/p1"])
        self.servicio.eliminar("")
        self.assertEqual(len(self.cliente.eliminadas), 1)

    def test_errores_del_cliente_se_traducen(self) -> None:
        self.cliente.error = RuntimeError("fallo remoto")
        with self.assertRaises(ServicioNoDisponible):
            self.servicio.subir(almacen_id="a1", producto_id="p1", contenido=PNG)
        with self.assertRaises(ServicioNoDisponible):
            self.servicio.eliminar("asistente-compras/a1/p1")


if __name__ == "__main__":
    unittest.main()
