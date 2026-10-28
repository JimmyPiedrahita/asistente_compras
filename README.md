# Asistente de compras

API REST multi-almacén para comparar precios y gestionar listas y carritos de
compra. El backend está organizado siguiendo MVC y usa **una base de datos
MongoDB independiente por almacén**.

- Documentación de arquitectura: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)
- Contrato HTTP: [`openapi.yaml`](openapi.yaml)
- Documentación interactiva: `http://localhost:8000/docs`

## Funcionalidades

- Sesiones de cliente y administrador con roles y permisos.
- Lista de compras sin duplicados.
- Búsquedas por mejor precio por almacén, catálogo completo y mejor precio
  global.
- Productos normales, físicos, digitales y por suscripción.
- Carrito con descuento porcentual o fijo.
- Alta de productos, edición de precios e importación CSV.
- Exportación CSV de la lista y del carrito.
- Inventario en caché al arrancar y recarga administrativa desde MongoDB.
- Compatibilidad con las rutas anteriores bajo `/api`; la versión recomendada
  es `/api/v1`.

## Arquitectura

```text
main.py                         Punto de entrada ASGI
core/                           Configuración, errores, logging, Observer, resultados
models/                         Entidades, listas enlazadas, carrito, permisos
models/estrategias/             Strategy: búsquedas y descuentos
infrastructure/mongodb/         Cliente, índices, repositorio por almacén
controllers/                    Casos de uso y fachada ControladorCompras
views/api/                      FastAPI, DTOs, serializadores, routers y errores
tests/unit/                     Dominio, estrategias, controladores y sesiones
tests/integration/              API con persistencia falsa y MongoDB real
scripts/                        Seed y generación de OpenAPI
docs/                           Arquitectura y decisiones
```

La dirección de dependencias es `views -> controllers -> models` y
`controllers -> infrastructure` a través del contrato `InventarioRepository`.
El dominio no importa FastAPI ni PyMongo.

### MVC

- **Modelo**: `models/`, con las entidades, reglas de negocio, estructuras de
  datos y estrategias. El inventario usa `ListaSimple`; la lista de compras y
  el carrito usan `ListaDoblementeEnlazada`.
- **Controlador**: `controllers/`, con casos de uso pequeños coordinados por
  `ControladorCompras`. Cada sesión HTTP tiene su propia instancia.
- **Vista**: `views/api/`, que traduce HTTP a casos de uso y los resultados a
  JSON/CSV. No contiene reglas de negocio.

### Patrones aplicados

- **Factory Method**: `FabricaProductos`.
- **Strategy**: búsquedas y descuentos intercambiables.
- **Observer**: el carrito notifica cambios a la vista.
- **Repository**: `MongoInventarioRepository` y `RepositorioNulo`.
- **Facade**: `ControladorCompras` mantiene una interfaz estable.
- **MVC**: separación estricta entre modelo, controlador y vista.

## MongoDB por almacén

Un único `MongoClient` con pool atiende todas las bases:

```text
MongoClient
├── warehouse_1.productos
├── warehouse_2.productos
└── warehouse_3.productos
```

El prefijo es configurable con `MONGODB_DB_PREFIX`. El número y los nombres de
almacenes se pueden cambiar con `WAREHOUSES=1:Centro,2:Norte`.

Cada documento guarda `_id = producto_id`, los datos del producto y campos
normalizados (`nombre_normalizado`, `marca_normalizada`) con índices auxiliares
para búsquedas. La estructura principal en memoria sigue siendo la lista
enlazada; los índices son una optimización.

Las escrituras persisten primero en MongoDB y después actualizan la caché en
memoria. Al arrancar se carga cada inventario una sola vez. Un administrador
puede forzar la recarga con `POST /api/v1/sessions/{token}/admin/reload`.

> **Importante:** las sesiones y la caché viven en memoria. Ejecuta **un solo
> worker** de Uvicorn. Para escalar horizontalmente habría que compartir
> sesiones y caché (por ejemplo con Redis).

## Inicio rápido con Docker

1. Copia y edita las variables:

   ```bash
   cp .env.example .env
   # Cambia ADMIN_CLAVE por una clave de al menos 8 caracteres
   ```

2. Levanta MongoDB y carga los datos de ejemplo **antes** de arrancar la API
   (la caché se llena al iniciar):

   ```bash
   docker compose up -d mongodb
   docker compose --profile tools run --rm seed
   ```

3. Levanta la API:

   ```bash
   docker compose up -d --build app
   curl http://localhost:8000/api/v1/health
   ```

4. Abre `http://localhost:8000/docs`.

Si la API ya estaba arrancada cuando ejecutaste el seed, recarga la caché con
`POST /api/v1/sessions/{token}/admin/reload` o reinicia el contenedor `app`.

Para detener los servicios:

```bash
docker compose down
```

## Desarrollo local

Requisitos: Python 3.10+ y MongoDB 7 (o el contenedor de MongoDB).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# Edita .env: al menos ADMIN_CLAVE
set -a
source .env
set +a

docker compose up -d mongodb
python scripts/seed_mongodb.py
uvicorn main:app --reload
```

La API queda en `http://127.0.0.1:8000` y la documentación en `/docs`.

También se puede ejecutar directamente:

```bash
python main.py
```

## Variables de entorno

| Variable | Obligatoria | Defecto | Descripción |
| --- | --- | --- | --- |
| `MONGODB_URI` | Sí | — | URI de MongoDB, por ejemplo `mongodb://127.0.0.1:27017/`. |
| `ADMIN_CLAVE` | Sí | — | Clave administrativa. Mínimo 8 caracteres. No existe valor por defecto. |
| `MONGODB_DB_PREFIX` | No | `warehouse` | Prefijo de bases: `warehouse_1`, `warehouse_2`, ... |
| `WAREHOUSES` | No | `1,2,3` | Almacenes con formato `1:Centro,2:Norte`. |
| `MONGODB_TIMEOUT_MS` | No | `5000` | Timeout de selección/conexión de MongoDB. |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Orígenes separados por comas. |
| `SESSION_TTL_SECONDS` | No | `3600` | Inactividad máxima de una sesión. |
| `MAX_SESSIONS` | No | `1000` | Número máximo de sesiones en memoria. |
| `MAX_CSV_BYTES` | No | `1000000` | Tamaño máximo del CSV de importación. |
| `LOG_LEVEL` | No | `INFO` | Nivel de logging. |

## Uso de la API

Crear una sesión de usuario:

```bash
curl -s -X POST http://localhost:8000/api/v1/sessions/user \
  -H 'Content-Type: application/json' \
  -d '{"nombre":"Ana"}'
```

La respuesta incluye `session_id`. Salvo los endpoints públicos de salud y
almacenes, las rutas de sesión reciben el token en la ruta. También se admite
`Authorization: Bearer <token>` (el token de la ruta se ignora si hay cabecera
Bearer).

Crear una sesión de administrador:

```bash
curl -s -X POST http://localhost:8000/api/v1/sessions/admin \
  -H 'Content-Type: application/json' \
  -d "{\"clave\":\"$ADMIN_CLAVE\"}"
```

### Endpoints principales

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Salud de la API y MongoDB. |
| `GET` | `/api/v1/health/live` | Liveness sin consultar MongoDB. |
| `GET` | `/api/v1/health/ready` | Readiness con ping a MongoDB. |
| `GET` | `/api/v1/warehouses` | Almacenes y cantidad de productos. |
| `GET` | `/api/v1/warehouses/{id}/products` | Inventario de un almacén. |
| `POST` | `/api/v1/sessions/user` | Crea sesión de cliente. |
| `POST` | `/api/v1/sessions/admin` | Crea sesión de administrador. |
| `GET` | `/api/v1/sessions/{token}` | Estado, lista y carrito. |
| `DELETE` | `/api/v1/sessions/{token}` | Cierra la sesión. |
| `GET` | `/api/v1/sessions/{token}/shopping-list` | Lista de compras. |
| `POST` | `/api/v1/sessions/{token}/shopping-list` | Agrega un producto. |
| `DELETE` | `/api/v1/sessions/{token}/shopping-list/{nombre}` | Elimina un producto. |
| `POST` | `/api/v1/sessions/{token}/search` | Busca con `mejor_precio`, `catalogo` o `global`. |
| `GET` | `/api/v1/sessions/{token}/cart` | Resumen del carrito. |
| `POST` | `/api/v1/sessions/{token}/cart/items` | Agrega por `almacen_id` + `producto_id`. |
| `DELETE` | `/api/v1/sessions/{token}/cart/items/{indice}` | Quita un ítem. |
| `DELETE` | `/api/v1/sessions/{token}/cart` | Vacía el carrito. |
| `POST` | `/api/v1/sessions/{token}/cart/discount` | Aplica `sin`, `porcentaje` o `fijo`. |
| `POST` | `/api/v1/sessions/{token}/admin/warehouses/{id}/products` | Alta de producto. |
| `PATCH` | `/api/v1/sessions/{token}/admin/warehouses/{id}/products` | Edita precio por `producto_id`. |
| `POST` | `/api/v1/sessions/{token}/admin/csv` | Importa inventario CSV. |
| `POST` | `/api/v1/sessions/{token}/admin/reload` | Recarga inventarios desde MongoDB. |
| `GET` | `/api/v1/sessions/{token}/export/shopping-list` | Exporta la lista en CSV. |
| `GET` | `/api/v1/sessions/{token}/export/cart` | Exporta el carrito en CSV. |

Las mismas rutas existen bajo `/api` por compatibilidad, pero no aparecen en
OpenAPI.

### Formato CSV

Cabecera obligatoria:

```csv
almacen,nombre,marca,categoria,tipo,precio,extra
1,Leche,La Serenisima,Lacteos,normal,1200,
1,Mouse,Logitech,Tecnologia,fisico,15000,500
1,Netflix,Netflix,Streaming,suscripcion,3500,12
```

- `almacen` debe existir.
- `tipo`: `normal`, `fisico`, `digital` o `suscripcion`.
- `extra`: costo de envío para `fisico` y meses para `suscripcion`.
- Las filas duplicadas por almacén + nombre + marca se rechazan.

## Pruebas y calidad

```bash
# Toda la suite (MongoDB se omite si no hay MONGODB_URI)
python -m unittest discover -s tests -t .

# Con MongoDB real (Docker local)
docker compose up -d mongodb
MONGODB_URI=mongodb://127.0.0.1:27017/ ADMIN_CLAVE=test-admin-key \
  python -m unittest discover -s tests -t . -v

# Lint y formato
ruff check .
ruff format --check .

# Regenerar el contrato OpenAPI
python scripts/exportar_openapi.py
```

La suite de API usa `PersistenciaFalsa`, por lo que no necesita MongoDB. Las
pruebas de `tests/integration/test_mongodb.py` se ejecutan contra MongoDB real
y comprueban aislamiento entre almacenes, índices y upsert idempotente.

## Seguridad y operación

- `ADMIN_CLAVE` es obligatoria y no tiene valor por defecto.
- No se registran claves ni tokens completos.
- Las sesiones expiran por inactividad y tienen un límite máximo.
- Los errores HTTP usan códigos coherentes (`400`, `401`, `403`, `404`, `409`,
  `422`, `503`) y un cuerpo JSON con `error`, `codigo` y, si aplica,
  `detalles`.
- Cada respuesta incluye `X-Request-ID`; se puede enviar uno propio.
- El contenedor se ejecuta con usuario no root y healthcheck de readiness.

## Documentación adicional

- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md): capas, flujos, MongoDB,
  decisiones y patrones.
- [`openapi.yaml`](openapi.yaml): contrato generado desde FastAPI.
