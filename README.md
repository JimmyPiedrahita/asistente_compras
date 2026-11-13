# Asistente de Compras

Aplicación web de compras y comparación de productos entre almacenes. El cliente
arma una lista, compara precios, usa un carrito, aplica cupones por almacén y
finaliza con un **pago**. Cada almacén gestiona sus productos, cupones,
compras y estadísticas de forma independiente.

- Interfaz React + Tailwind CSS servida por la propia API.
- Backend FastAPI + PyMongo con una única base MongoDB `asistente_compras`.
- Contrato HTTP: [`openapi.yaml`](openapi.yaml)
- Documentación interactiva: `http://localhost:8000/docs`
- Arquitectura: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)

## Funcionalidades

### Cliente

- Registro público e inicio de sesión con correo y contraseña.
- Lista de compras sin duplicados.
- Búsqueda con tres filtros: todo el catálogo, más barato por almacén y más
  barato global, con desempates estables.
- Carrito con productos de varios almacenes y cantidades editables.
- Hasta tres cupones por compra, uno por almacén.
- Resumen por almacén y total general.
- Datos de entrega editables antes de confirmar.
- Pago idempotente y comprobante de compra.

### Administrador de almacén

- Gestión completa de los productos de su almacén.
- Importación CSV total o nothing: si una fila falla, no se importa nada.
- Gestión de cupones de su almacén (crear, consultar y eliminar).
- Consulta de las compras que incluyen productos de su almacén.
- Estadísticas de productos más y menos vendidos por unidades.

### Administrador de la aplicación

- Crear almacenes.
- Crear y vincular administradores de almacén.
- Actualizar correo y contraseña de los administradores de almacén.

## Reglas principales

- Hay tres roles separados: `CLIENTE`, `ADMINISTRADOR_ALMACEN` y
  `ADMINISTRADOR_APP`. Los permisos se validan en la API, no solo en la interfaz.
- La aplicación inicia sin almacenes, productos, cupones, compras ni
  administradores de almacén. Solo se crea la cuenta inicial del administrador de
  la aplicación si todavía no existe.
- Todos los productos de un mismo `tipo_producto` deben usar la misma
  presentación; se valida en alta manual, edición e importación CSV.
- Los cupones pertenecen a un almacén y descuentan solo el subtotal de ese
  almacén. No existen cupones globales.
- Las compras guardan una copia inmutable de productos, precios, cupones y datos
  de entrega. Eliminar productos o cupones después no altera compras pasadas.
- La compra registra el pago y los datos necesarios para coordinar la entrega.

## Inicio rápido con Docker

Requisitos: Docker y Docker Compose.

1. Revisa `.env` y define credenciales propias. Como mínimo:

   ```env
   MONGO_ROOT_PASSWORD=una-clave-segura
   ADMIN_EMAIL=admin@tu-dominio.com
   ADMIN_PASSWORD=una-clave-de-al-menos-8-caracteres
   ADMIN_NOMBRE="Administrador de la aplicación"
   ```

2. Levanta los servicios:

   ```bash
   docker compose up -d --build
   ```

3. Abre `http://localhost:8000` e inicia sesión con las credenciales del
   administrador de la aplicación.

La primera vez la base está vacía. El flujo de puesta en marcha es:

1. El administrador de la aplicación crea un almacén.
2. Crea el administrador de ese almacén.
3. El administrador de almacén inicia sesión y agrega productos manualmente o por
   CSV.
4. Opcionalmente crea cupones.
5. Los clientes se registran y compran.

Para detener y eliminar también los datos:

```bash
docker compose down -v
```

## Desarrollo local

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
# MongoDB accesible en MONGODB_URI (por defecto, el del archivo .env)
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite sirve la interfaz en `http://localhost:3000` y redirige `/api` a
`http://127.0.0.1:8000`.

Para desarrollo sin Docker, exporta las variables del archivo `.env` o usa un
servicio MongoDB local:

```bash
export MONGODB_URI="mongodb://127.0.0.1:27017"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="AdminPass123"
uvicorn main:app --reload
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `MONGODB_URI` | Sí | URI de conexión a MongoDB. |
| `MONGODB_DB` | No | Base de datos única. Por defecto `asistente_compras`. |
| `ADMIN_EMAIL` | Sí | Correo de la cuenta inicial del administrador de la app. |
| `ADMIN_PASSWORD` | Sí | Contraseña inicial, mínimo 8 caracteres. |
| `ADMIN_NOMBRE` | No | Nombre visible de la cuenta inicial. |
| `MONGO_ROOT_USER` | Docker | Usuario root de MongoDB. |
| `MONGO_ROOT_PASSWORD` | Docker | Contraseña root de MongoDB. |
| `CORS_ORIGINS` | No | Orígenes permitidos, separados por coma. |
| `SESSION_TTL_SECONDS` | No | Vida de la sesión en memoria. Por defecto 3600. |
| `MAX_SESSIONS` | No | Máximo de sesiones simultáneas. Por defecto 1000. |
| `MAX_CSV_BYTES` | No | Tamaño máximo del CSV. Por defecto 1 000 000. |
| `MONGODB_TIMEOUT_MS` | No | Tiempo de espera de MongoDB. |
| `LOG_LEVEL` | No | Nivel de logging. |

Las credenciales del administrador inicial no están fijadas en el código: se leen
del entorno y la cuenta solo se crea cuando no existe ningún administrador de la
aplicación.

## API

Prefijo: `/api/v1`. La autenticación usa `Authorization: Bearer <session_id>`.

### Salud y autenticación

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/health`, `/health/live`, `/health/ready` | Estado de la API y MongoDB. |
| POST | `/auth/register` | Registro público de clientes. |
| POST | `/auth/login` | Inicio de sesión único para los tres roles. |
| GET | `/auth/me` | Sesión actual. |
| DELETE | `/auth/session` | Cerrar sesión. |

### Cliente

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET/POST | `/shopping-list` | Consultar o agregar a la lista. |
| DELETE | `/shopping-list/{nombre}` | Quitar un producto de la lista. |
| POST | `/search` | Buscar con `modo`: `catalogo`, `mejor_precio` o `global`. |
| GET/DELETE | `/cart` | Consultar o vaciar el carrito. |
| POST | `/cart/items` | Agregar producto. |
| PATCH/DELETE | `/cart/items/{item_id}` | Cambiar cantidad o quitar. |
| POST | `/cart/coupons` | Aplicar cupón. |
| DELETE | `/cart/coupons/{codigo}` | Quitar cupón. |
| POST | `/checkout` | Confirmar pago. |

### Administrador de almacén

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET/POST | `/admin-almacen/productos` | Listar o crear productos. |
| PATCH/DELETE | `/admin-almacen/productos/{id}` | Editar o eliminar. |
| POST | `/admin-almacen/productos/importar` | Importar CSV. |
| GET/POST | `/admin-almacen/cupones` | Listar o crear cupones. |
| DELETE | `/admin-almacen/cupones/{id}` | Eliminar cupón. |
| GET | `/admin-almacen/compras` | Compras de su almacén. |
| GET | `/admin-almacen/estadisticas` | Más y menos vendidos. |

### Administrador de la aplicación

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET/POST | `/admin-app/almacenes` | Listar o crear almacenes. |
| GET/POST | `/admin-app/administradores` | Listar o crear administradores. |
| PATCH | `/admin-app/administradores/{id}/credenciales` | Actualizar correo o contraseña. |

## Formato del CSV

```csv
tipo_producto,nombre,marca_variedad,precio,presentacion
arroz,Arroz Diana,Diana,3000,500 g
leche,Leche entera,Marca de ejemplo,4500,1 litro
```

- UTF-8, separador coma, encabezados en la primera fila.
- `tipo_producto`, `nombre`, `precio` y `presentacion` son obligatorios.
- `marca_variedad` es opcional.
- Sin símbolos de moneda ni separadores de miles; decimales con punto.
- Sin columna de almacén: se asigna el almacén del administrador autenticado.
- La importación es atómica: si alguna fila falla, se informa la fila y el motivo,
  y no se guarda ningún producto.

## Pruebas

Las pruebas unitarias no necesitan MongoDB. Las de integración se ejecutan
cuando existe `MONGODB_URI` y usan una base temporal por prueba.

```bash
make test
make lint
```

En CI se levanta MongoDB 7.0, se ejecutan lint, formato, pruebas, compilación del
frontend y verificación de que `openapi.yaml` esté actualizado.

## Estructura

```text
main.py                         Punto de entrada ASGI
core/                           Configuración, errores y logging
models/                         Entidades y reglas de dominio
infrastructure/mongodb/         Cliente y repositorio MongoDB
controllers/                    Casos de uso y permisos
views/api/                      FastAPI, esquemas, routers y errores
frontend/                       React + Tailwind CSS (Vite)
tests/unit/                     Dominio, sesiones y controladores
tests/integration/              API y MongoDB reales
scripts/                        Exportación de OpenAPI
docs/                           Arquitectura
```
