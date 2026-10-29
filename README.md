# Asistente de compras

API REST multi-almacén para comparar precios y gestionar listas y carritos de
compra. El backend está organizado siguiendo MVC, usa **una base de datos
MongoDB independiente por almacén** y mantiene una base integrada
`comparador` sincronizada mediante **Change Streams** sobre un replica set.

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
- Alta de productos, edición de precios, eliminación e importación CSV.
- Exportación CSV de la lista y del carrito.
- Base integrada `comparador` con `_id` compuesto, índices y paginación.
- Sincronización automática de altas, cambios y bajas mediante Change Streams.
- Reconciliación administrativa y estado de la proyección.
- Catálogo consultado en MongoDB: no se carga completo en memoria.
- Compatibilidad con las rutas anteriores bajo `/api`; la versión recomendada
  es `/api/v1`.

## Arquitectura

```text
main.py                         Punto de entrada ASGI
core/                           Configuración, errores, logging, Observer, resultados
models/                         Entidades, listas enlazadas, carrito, permisos
models/estrategias/             Strategy: búsquedas y descuentos
infrastructure/mongodb/         Cliente, índices, repositorio y proyector comparador
controllers/                    Casos de uso y fachada ControladorCompras
views/api/                      FastAPI, DTOs, serializadores, routers y errores
tests/unit/                     Dominio, estrategias, controladores y sesiones
tests/integration/              API con persistencia falsa y MongoDB real
scripts/                        Seed, listener, reconciliación y OpenAPI
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

## MongoDB, replica set y base integrada

Un único `MongoClient` con pool atiende todas las bases:

```text
MongoDB (replica set rs0)
├── warehouse_1.productos      fuente de verdad
├── warehouse_2.productos      fuente de verdad
├── warehouse_3.productos      fuente de verdad
└── comparador
    ├── productos              read model integrado
    └── sync_state             resume token y estado del listener
```

El prefijo de los almacenes es configurable con `MONGODB_DB_PREFIX`. El número
y los nombres se pueden cambiar con `WAREHOUSES=1:Centro,2:Norte`. La base
integrada se configura con `MONGODB_COMPARADOR_DB` y no puede coincidir con la
base de un almacén.

Cada documento de almacén guarda `_id = producto_id`, los datos del producto y
campos normalizados (`nombre_normalizado`, `marca_normalizada`) con índices.
La proyección `comparador.productos` usa un `_id` compuesto
`"{almacen_id}_{producto_id}"`, guarda `precio_final` e incluye índices por
nombre y precio.

### Sincronización

El servicio `listener` ejecuta `scripts/run_listener.py` y mantiene
`comparador` al día:

1. Si no existe `resume_token`, reconstruye la proyección completa.
2. Abre un Change Stream sobre las colecciones `productos` de los almacenes.
3. Aplica `insert`, `update`, `replace` y `delete` de forma idempotente.
4. Guarda el `resume_token` en `comparador.sync_state`.
5. Ante `ChangeStreamHistoryLost` (código 286), reconstruye y reabre el stream.
6. Reintenta con backoff si se pierde la conexión.

La consistencia es **eventual**: una escritura del administrador se refleja en
`comparador` en cuanto el listener procesa el cambio. No se hace una
proyección síncrona en la API.

### Sin caché del catálogo

La API **no carga el catálogo completo en memoria**. Las consultas se resuelven
en MongoDB:

| Consulta | Fuente |
| --- | --- |
| `GET /warehouses/{id}/products` | `warehouse_X`, paginado |
| `mejor_precio` | `comparador`, agregación por almacén |
| `catalogo` | `comparador`, paginado |
| `global` | `comparador`, el más barato entre almacenes |
| Carrito por `producto_id` | `warehouse_X` |

Las listas enlazadas se mantienen para la lista de compras, el carrito y los
resultados acotados de una consulta. Las sesiones siguen en memoria, por lo que
se recomienda **un solo worker** de Uvicorn. Un administrador puede
reconstruir `comparador` con
`POST /api/v1/sessions/{token}/admin/comparador/reconciliar` o con
`POST /api/v1/sessions/{token}/admin/reload`.

## Inicio rápido con Docker

1. Copia y edita las variables:

   ```bash
   cp .env.example .env
   # Cambia ADMIN_CLAVE por una clave de al menos 8 caracteres
   ```

2. Levanta MongoDB como replica set e inicialízalo:

   ```bash
   docker compose up -d mongodb mongo-init
   ```

   `mongo-init` anuncia `mongodb:27017` como miembro del replica set. Si el
   volumen `mongo_data` se creó antes con otro hostname (por ejemplo
   `localhost:27017`), lo reconfigura automáticamente; el host se puede cambiar
   con `MONGO_REPLICA_HOST`.

3. Carga los datos de ejemplo (opcional):

   ```bash
   docker compose --profile tools run --rm seed
   ```

4. Levanta el listener y la API:

   ```bash
   docker compose up -d --build listener app
   curl http://localhost:8000/api/v1/health
   ```

   El listener reanuda desde `comparador.sync_state`; si no hay
   `resume_token`, reconstruye la proyección y luego escucha cambios.
   Si el seed se ejecutó antes, la reconciliación inicial ya incluye esos
   productos; si se ejecuta después, los Change Streams los incorporan.

5. Abre `http://localhost:8000/docs`.

Para forzar una reconstrucción manual:

```bash
docker compose exec listener python scripts/reconciliar_comparador.py
```

Para detener los servicios:

```bash
docker compose down
```

## Desarrollo local

Requisitos: Python 3.10+ y MongoDB 7 configurado como replica set.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# Edita .env: al menos ADMIN_CLAVE
set -a
source .env
set +a

# MongoDB en replica set (el compose ya lo configura)
docker compose up -d mongodb mongo-init
python scripts/seed_mongodb.py

# En dos terminales:
python scripts/run_listener.py
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
| `MONGODB_URI` | Sí | — | URI de MongoDB. En Docker: `mongodb://mongodb:27017/?replicaSet=rs0`. Desde el host: `mongodb://127.0.0.1:27017/?directConnection=true`. |
| `ADMIN_CLAVE` | Sí | — | Clave administrativa. Mínimo 8 caracteres. No existe valor por defecto. |
| `MONGODB_DB_PREFIX` | No | `warehouse` | Prefijo de bases: `warehouse_1`, `warehouse_2`, ... |
| `MONGODB_COMPARADOR_DB` | No | `comparador` | Base integrada de solo lectura mantenida por el listener. |
| `MONGO_REPLICA_HOST` | No | `mongodb:27017` | Host que anuncia `mongo-init` como miembro de `rs0` en Docker. |
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
| `GET` | `/api/v1/warehouses/{id}/products` | Inventario paginado (`limit`, `offset`, `X-Total-Count`). |
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
| `DELETE` | `/api/v1/sessions/{token}/admin/warehouses/{id}/products/{producto_id}` | Elimina un producto. |
| `POST` | `/api/v1/sessions/{token}/admin/csv` | Importa inventario CSV. |
| `GET` | `/api/v1/sessions/{token}/admin/comparador/status` | Estado de la proyección integrada. |
| `POST` | `/api/v1/sessions/{token}/admin/comparador/reconciliar` | Reconstruye `comparador` desde los almacenes. |
| `POST` | `/api/v1/sessions/{token}/admin/reload` | Alias de compatibilidad para reconciliar `comparador`. |
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

# Con MongoDB real en replica set (Docker local)
docker compose up -d mongodb mongo-init
MONGODB_URI='mongodb://127.0.0.1:27017/?directConnection=true' \
  ADMIN_CLAVE=test-admin-key \
  python -m unittest discover -s tests -t . -v

# Lint y formato
ruff check .
ruff format --check .

# Regenerar el contrato OpenAPI
python scripts/exportar_openapi.py
```

La suite de API usa `PersistenciaFalsa`, por lo que no necesita MongoDB. Las
pruebas de `tests/integration/test_mongodb.py` se ejecutan contra MongoDB real
y comprueban aislamiento entre almacenes, índices, paginación, eliminación,
reconstrucción de `comparador` y propagación de cambios con Change Streams.
Si MongoDB no está en replica set, la prueba de Change Streams se omite.

## Seguridad y operación

- `ADMIN_CLAVE` es obligatoria y no tiene valor por defecto.
- No se registran claves ni tokens completos.
- Las sesiones expiran por inactividad y tienen un límite máximo.
- MongoDB debe ser un **replica set** para que funcionen los Change Streams.
- El listener debe ejecutarse como **una sola instancia**; los eventos son
  idempotentes y el `resume_token` permite reanudar tras un reinicio.
- `comparador` es reconstruible desde `warehouse_*`; no es la única copia.
- Los errores HTTP usan códigos coherentes (`400`, `401`, `403`, `404`, `409`,
  `422`, `503`) y un cuerpo JSON con `error`, `codigo` y, si aplica,
  `detalles`.
- Cada respuesta incluye `X-Request-ID`; se puede enviar uno propio.
- El contenedor se ejecuta con usuario no root y healthcheck de readiness.

### Problemas frecuentes

- **`ServerSelectionTimeoutError` y el replica set anuncia `localhost:27017`**:
  el volumen se inicializó dentro del contenedor con otro hostname. Ejecuta
  `docker compose up -d mongo-init` para reconfigurarlo a `mongodb:27017` o
  ajusta `MONGO_REPLICA_HOST`.
- **`ChangeStreamHistoryLost` (código 286)**: el listener reconstruye
  `comparador` automáticamente; también se puede forzar con
  `POST /admin/comparador/reconciliar`.
- **Producto no visible tras un alta**: la consistencia es eventual; revisa
  `GET /admin/comparador/status` y los logs del servicio `listener`.

## Documentación adicional

- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md): capas, flujos, MongoDB,
  decisiones y patrones.
- [`openapi.yaml`](openapi.yaml): contrato generado desde FastAPI.
