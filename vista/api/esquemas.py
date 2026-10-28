from pydantic import BaseModel, Field


class UsuarioSesion(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


class ClaveAdministrador(BaseModel):
    clave: str = Field(min_length=1)


class ProductoSolicitud(BaseModel):
    nombre: str = Field(min_length=1)
    precio: float = Field(ge=0)
    marca: str = "Generica"
    categoria: str = "General"
    tipo: str = "normal"
    costo_envio: float | None = Field(default=None, ge=0)
    meses: int | None = Field(default=None, ge=1)


class PrecioSolicitud(BaseModel):
    producto_id: str = Field(min_length=1)
    precio: float = Field(ge=0)


class ListaProductoSolicitud(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)


class BusquedaSolicitud(BaseModel):
    modo: str = Field(
        default="mejor_precio",
        description="mejor_precio, catalogo o global",
    )


class CarritoProductoSolicitud(BaseModel):
    almacen_id: int = Field(ge=1)
    producto_id: str = Field(min_length=1)


class DescuentoSolicitud(BaseModel):
    tipo: str = Field(description="sin, porcentaje o fijo")
    valor: float | None = Field(default=None, ge=0)


class CsvSolicitud(BaseModel):
    contenido: str = Field(min_length=1)
