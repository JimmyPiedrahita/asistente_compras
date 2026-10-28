# Asistente de compras

Backend REST para comparar productos entre inventarios MongoDB aislados por
almacén. El proyecto expone únicamente una API HTTP; no incluye interfaz
Tkinter ni modo consola.

## Arquitectura

El backend está organizado como MVC modular:

- `views/api/`: presentación HTTP, DTOs, sesiones, errores y rutas.
- `controllers/`: coordinación de casos de uso de la aplicación.
- `models/`: entidades, estrategias de búsqueda/descuento e interfaces de
  persistencia.
- `permisos.py`: roles, permisos y logging.

La API es la única superficie de presentación. El dominio no depende de
FastAPI y la persistencia no devuelve documentos Mongo directamente.

## MongoDB

Cada almacén se mantiene en una base independiente:

- `warehouse_1.productos`
- `warehouse_2.productos`
- `warehouse_3.productos`

La aplicación consulta esas bases directamente. No existe una colección
`comparador` ni un listener de Change Streams obligatorio: no se mantiene una
segunda fuente de verdad para inventarios y precios.

Para desarrollo local:

```bash
docker compose up -d
pip install -r requirements.txt
export MONGODB_URI=mongodb://127.0.0.1:27017/
.venv/bin/uvicorn views.api.app:create_app --factory --reload
```

La documentación interactiva queda en `http://localhost:8000/docs`.

## API

La versión recomendada está bajo `/api/v1`. Las rutas `/api` se conservan
temporalmente para compatibilidad:

- `GET /api/v1/health`
- `POST /api/v1/sessions/user`
- `POST /api/v1/sessions/admin`
- `GET/DELETE /api/v1/sessions/{token}`
- `POST/DELETE /api/v1/sessions/{token}/shopping-list`
- `POST /api/v1/sessions/{token}/search`
- `GET/DELETE /api/v1/sessions/{token}/cart`
- `POST/DELETE /api/v1/sessions/{token}/cart/items`
- `POST /api/v1/sessions/{token}/cart/discount`
- Rutas administrativas para inventario y CSV.

El contrato completo se encuentra en [`openapi.yaml`](openapi.yaml).

## Funcionalidades

- Sesiones de cliente y administrador con permisos.
- Lista de compras sin duplicados.
- Búsqueda por mejor precio por almacén, catálogo completo y mejor precio
  global.
- Productos normales, físicos, digitales y por suscripción.
- Carrito y descuentos porcentuales o fijos.
- Alta, actualización e importación CSV de inventarios.
- Exportación de lista y carrito desde los casos de uso existentes.

## Desarrollo y pruebas

```bash
.venv/bin/python -m unittest pruebas.py pruebas_api.py
```

La suite no necesita MongoDB porque usa una persistencia falsa para los casos
de API. Las pruebas de integración con MongoDB deben ejecutarse contra el
servicio de Docker.

## Configuración

Variables principales:

- `MONGODB_URI`: URI obligatoria para iniciar la API.
- `ADMIN_CLAVE`: clave administrativa; debe configurarse fuera del código.
- `CORS_ORIGINS`: orígenes permitidos separados por comas.
