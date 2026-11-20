# Asistente de Compras

Aplicación web de compras y comparación de productos entre almacenes. El cliente
arma una lista, compara precios, usa un carrito, aplica cupones por almacén y
finaliza con un **pago**. Cada almacén gestiona sus productos, cupones,
compras y estadísticas de forma independiente.

- Interfaz React + Tailwind CSS servida por la propia API.
- Backend FastAPI + PyMongo sobre MongoDB en replica set.
- Una base global `global_asistente_compras` y **una base dedicada por almacén**.
- Replicación del catálogo y proyección de compras mediante Change Streams.
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

- Crear almacenes, con su base y su usuario nativo de MongoDB.
- Crear y vincular administradores de almacén.
- Actualizar correo y contraseña de los administradores de almacén.

## Reglas principales

- Hay tres roles de aplicación: `CLIENTE`, `ADMINISTRADOR_ALMACEN` y
  `ADMINISTRADOR_APP`. Los permisos se validan en la API, no solo en la interfaz.
- La aplicación inicia sin almacenes, productos, cupones, compras ni
  administradores de almacén. Solo se crea la cuenta inicial del administrador de
  la aplicación si todavía no existe.
- Todos los productos de un mismo `tipo_producto` deben usar la misma
  presentación; se valida en alta manual, edición e importación CSV.
- Los cupones pertenecen a un almacén y descuentan solo el subtotal de ese
  almacén. El código es único en toda la aplicación.
- Las compras guardan una copia inmutable de productos, precios, cupones y datos
  de entrega. Eliminar productos o cupones después no altera compras pasadas.
- La compra registra el pago y los datos necesarios para coordinar la entrega.

## Almacenamiento

La persistencia se reparte en dos niveles:

```text
global_asistente_compras          # metadata y datos compartidos
├── usuarios                      # cuentas de los tres roles
├── almacenes                     # metadata y credenciales internas
├── productos_global              # réplica del catálogo de todos los almacenes
├── cupones_global                # réplica de cupones para consulta del cliente
├── compras                       # compras completas del cliente
├── sync_state_catalogo           # tokens de los Change Streams de catálogo
└── sync_state_compras            # estado del proyector de compras

almacen_<nombre>_<id>             # una base por almacén
├── productos                     # catálogo propio
├── cupones                       # cupones propios
└── compras_almacen               # proyección de sus compras
```

- La API nunca expone nombres de base, usuarios, contraseñas ni URIs de MongoDB.
- Un **usuario MongoDB compartido** atiende a todos los clientes (`cliente_app`);
  cada almacén tiene un usuario nativo propio para sus administradores.
- Los administradores de un mismo almacén comparten el usuario del almacén.
- La contraseña del usuario de cada almacén se deriva con HMAC-SHA256 a partir de
  `MONGODB_WAREHOUSE_SECRET` y del `almacen_id`; no se guarda en texto plano.
- La base global y las bases de almacén se crean desde cero. No se migra la base
  única de versiones anteriores.

### Replicación

Un proceso `listener` mantiene dos tareas:

1. **Sincronizador de catálogo**: escucha los Change Streams de `productos` y
   `cupones` de cada base de almacén y actualiza `productos_global` y
   `cupones_global`. Cada colección conserva su propio token de reanudación.
2. **Proyector de compras**: escucha `compras` en la base global y escribe en
   `compras_almacen` solo la parte correspondiente a cada almacén.

La consistencia es eventual. La API sigue funcionando si el listener está
detenido; los scripts de reconciliación reconstruyen el estado. Al descubrir un
almacén nuevo, el sincronizador abre primero el Change Stream y luego reconcilia
su catálogo para no perder cambios anteriores.

## Inicio rápido con Docker

Requisitos: Docker y Docker Compose.

1. Revisa `.env` y define credenciales propias. Como mínimo:

   ```env
   MONGO_ROOT_PASSWORD=una-clave-segura
   MONGODB_WAREHOUSE_SECRET=un-secreto-de-al-menos-32-caracteres
   MONGO_CLIENTE_PASSWORD=clave-cliente
   MONGO_ADMIN_APP_PASSWORD=clave-admin-app
   MONGO_AUTH_PASSWORD=clave-auth
   MONGO_VALIDADOR_PASSWORD=clave-validador
   MONGO_CATALOGO_PASSWORD=clave-catalogo
   MONGO_COMPRAS_PASSWORD=clave-compras
   MONGO_PROVISIONER_PASSWORD=clave-provisioner
   ADMIN_EMAIL=admin@tu-dominio.com
   ADMIN_PASSWORD=una-clave-de-al-menos-8-caracteres
   ADMIN_NOMBRE="Administrador de la aplicación"
   ```

2. Levanta los servicios:

   ```bash
   docker compose up -d --build
   ```

   `docker compose` arranca MongoDB como replica set `rs0` con autenticación,
   ejecuta `mongo-init` (roles, usuarios e índices), y levanta `app` y
   `listener`.

3. Abre `http://localhost:8000` e inicia sesión con las credenciales del
   administrador de la aplicación.

La primera vez la base está vacía. El flujo de puesta en marcha es:

1. El administrador de la aplicación crea un almacén. La API aprovisiona su base,
   su rol, su usuario nativo y sus índices.
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
uvicorn main:app --reload
```

Para desarrollo sin Docker se necesita un MongoDB en replica set. La forma más
sencilla es usar el `docker-compose.yml` incluido y ejecutar solo la API en
local:

```bash
docker compose up -d mongodb mongo-init
export MONGODB_HOST=127.0.0.1:27017
export MONGODB_REPLICA_SET=rs0
export MONGODB_AUTH_SOURCE=admin
# Exporta también las credenciales de servicio y de administrador del .env.
uvicorn main:app --reload
```

Para ejecutar el listener en local:

```bash
python scripts/run_listener.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite sirve la interfaz en `http://localhost:3000` y redirige `/api` a
`http://127.0.0.1:8000`.

### Modo de pruebas

Las pruebas de integración pueden reutilizar un único `MONGODB_URI` sin crear
usuarios nativos. En ese modo la fábrica de URIs devuelve el mismo URI para todos
los roles y los repositorios siguen usando bases distintas:

```bash
export MONGODB_URI="mongodb://root:clave@127.0.0.1:27017/?authSource=admin"
make test
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `MONGODB_HOST` | Sí (Docker) | Host y puerto del replica set, por ejemplo `mongodb:27017`. |
| `MONGODB_REPLICA_SET` | No | Nombre del replica set. Por defecto `rs0`. |
| `MONGODB_AUTH_SOURCE` | No | Base de autenticación. Por defecto `admin`. |
| `MONGODB_GLOBAL_DB` | No | Base global. Por defecto `global_asistente_compras`. |
| `MONGODB_ALMACEN_PREFIX` | No | Prefijo de las bases por almacén. Por defecto `almacen_`. |
| `MONGODB_WAREHOUSE_SECRET` | Sí | Secreto maestro HMAC, mínimo 32 caracteres. |
| `MONGODB_WAREHOUSE_SECRET_ANTERIOR` | Solo rotación | Secreto anterior usado para confirmar la rotación; nunca se pasa como argumento. |
| `MONGO_CLIENTE_USER/PASSWORD` | Sí | Usuario compartido de los clientes. |
| `MONGO_ADMIN_APP_USER/PASSWORD` | Sí | Usuario del administrador de la aplicación. |
| `MONGO_AUTH_USER/PASSWORD` | Sí | Usuario del servicio de autenticación. |
| `MONGO_VALIDADOR_USER/PASSWORD` | Sí | Usuario de solo lectura para validaciones globales. |
| `MONGO_CATALOGO_USER/PASSWORD` | Sí | Usuario del listener de catálogo. |
| `MONGO_COMPRAS_USER/PASSWORD` | Sí | Usuario del proyector de compras. |
| `MONGO_PROVISIONER_USER/PASSWORD` | Sí | Usuario que crea bases, roles y usuarios de almacén. |
| `ADMIN_EMAIL` | Sí | Correo de la cuenta inicial del administrador de la app. |
| `ADMIN_PASSWORD` | Sí | Contraseña inicial, mínimo 8 caracteres. |
| `ADMIN_NOMBRE` | No | Nombre visible de la cuenta inicial. |
| `MONGO_ROOT_USER/PASSWORD` | Docker | Credenciales root, solo para `mongo-init` y scripts. |
| `MONGO_REPLICA_HOST` | Docker | Host usado al iniciar el replica set. |
| `CORS_ORIGINS` | No | Orígenes permitidos, separados por coma. |
| `SESSION_TTL_SECONDS` | No | Vida de la sesión en memoria. Por defecto 3600. |
| `MAX_SESSIONS` | No | Máximo de sesiones simultáneas. Por defecto 1000. |
| `MAX_CSV_BYTES` | No | Tamaño máximo del CSV. Por defecto 1 000 000. |
| `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` | No | Credenciales del servidor para subir imágenes; si faltan, las imágenes responden 503. |
| `CLOUDINARY_FOLDER` | No | Carpeta raíz de imágenes. Por defecto `asistente-compras`. |
| `MAX_PRODUCT_IMAGE_BYTES` | No | Tamaño máximo por imagen. Por defecto 2 000 000 bytes. |
| `MONGODB_TIMEOUT_MS` | No | Tiempo de espera de MongoDB. Por defecto 5000. |
| `LISTENER_REFRESH_SECONDS` | No | Frecuencia con la que el listener busca almacenes nuevos. Por defecto 15. |
| `LOG_LEVEL` | No | Nivel de logging. |
| `MONGODB_URI` | Solo pruebas | URI único usado en modo de pruebas y scripts. |
| `MONGODB_DB` | Solo pruebas | Base global del modo de pruebas. |

Las credenciales del administrador inicial no están fijadas en el código: se leen
del entorno y la cuenta solo se crea cuando no existe ningún administrador de la
aplicación. Los usuarios y contraseñas de MongoDB solo los usa el backend; nunca
se envían al frontend ni aparecen en la API.

## API

Prefijo: `/api/v1`. La autenticación usa `Authorization: Bearer <session_id>`.
El contrato público incluye los endpoints de imagen de productos descritos abajo
cuando Cloudinary está configurado.

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
| POST | `/admin-almacen/productos/{id}/imagen` | Subir o reemplazar una imagen. |
| DELETE | `/admin-almacen/productos/{id}/imagen` | Eliminar la imagen. |
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

## Operación

| Comando | Descripción |
| --- | --- |
| `make docker-up` | Levanta MongoDB, `mongo-init`, API y listener. |
| `make docker-logs` | Sigue los logs de todos los servicios. |
| `make rbac-test` | Verifica los permisos nativos de cada rol MongoDB. |
| `make reconciliar` | Reconcilia catálogo global y proyección de compras. |
| `make reconciliar-catalogo` | Reconstruye `productos_global` y `cupones_global`. |
| `make reconciliar-compras` | Reconstruye `compras_almacen` en todos los almacenes. |
| `make rotar-secretos` | Rota las contraseñas HMAC de los usuarios de almacén. |
| `make reset` | Elimina contenedores y volúmenes (solo desarrollo). |

La API expone `/api/v1/health/ready`, que hace ping con las conexiones de
`auth_service` y `admin_app`. El contenedor `listener` no expone puerto y tiene el
healthcheck de la imagen deshabilitado.

### Rotación de secretos

Si se cambia `MONGODB_WAREHOUSE_SECRET`, hay que rotar las contraseñas nativas de
los almacenes con el secreto anterior:

```bash
docker compose run --rm tools python scripts/rotar_secretos_almacenes.py
```

Después se actualiza `MONGODB_WAREHOUSE_SECRET` en el entorno y se reinician la
API y el listener. El script no imprime contraseñas. Usa un gestor de secretos
o un `.env` protegido; no pases los secretos como argumentos CLI ni los copies
directamente en el historial de shell.

Por seguridad, el Compose enlaza el puerto de la API solo a `127.0.0.1` en el
host. En despliegues accesibles desde otras máquinas, ejecuta la API detrás de
un proxy HTTPS y no publiques el puerto HTTP directamente.

## Pruebas

Las pruebas unitarias no necesitan MongoDB. Las de integración se ejecutan
cuando existe `MONGODB_URI` y crean una base global temporal y bases de almacén
por prueba; como el listener no corre, la reconciliación se hace explícita.

```bash
make test
make lint
```

En CI se levanta MongoDB 7.0 como replica set con autenticación, se ejecutan
lint, formato, pruebas, verificación RBAC nativa, compilación del frontend y
verificación de que `openapi.yaml` esté actualizado.

## Estructura

```text
main.py                         Punto de entrada ASGI
core/                           Configuración, errores y logging
models/                         Entidades y reglas de dominio
infrastructure/mongodb/         Conexiones por rol, repositorios y aprovisionamiento
infrastructure/mongodb/init/    Scripts de replica set, roles, usuarios e índices
controllers/                    Casos de uso y permisos
views/api/                      FastAPI, esquemas, routers y errores
frontend/                       React + Tailwind CSS (Vite)
tests/unit/                     Dominio, sesiones, URIs, réplica y aprovisionamiento
tests/integration/              API y MongoDB reales
scripts/                        Listener, reconciliación, RBAC y OpenAPI
docs/                           Arquitectura
```
