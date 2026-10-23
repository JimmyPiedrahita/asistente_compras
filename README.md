# Asistente de Compras Inteligente

Aplicación de escritorio en Python que simula un comparador de precios entre
tres almacenes. El usuario arma una lista de compras, el sistema busca cada
producto en los inventarios y permite agregar la mejor opción a un carrito con
descuentos. Un administrador carga y edita los precios.

El proyecto es un ejercicio académico de **patrones de diseño** y **estructuras
de datos implementadas a mano** (sin usar `list` para los inventarios ni para la
lista de compras).

## Requisitos

- Python 3.10 o superior
- Tkinter (incluido en la mayoría de instalaciones de Python)
- Sin dependencias externas para el modo en memoria. MongoDB requiere
  `pymongo` (ver `requirements.txt`).

En Debian/Ubuntu, si falta Tkinter: `sudo apt install python3-tk`

## Cómo ejecutar

```bash
# Interfaz gráfica (por defecto)
python3 main.py

# Menú de consola: carrito, descuentos, lista de compras y administración
python3 main.py --consola

# Omitir la impresión de la matriz de permisos al arrancar
python3 main.py --sin-banner
```

## Persistencia MongoDB

Por defecto la aplicación sigue usando memoria, lo que permite ejecutar las
pruebas sin MongoDB. Para usar inventarios persistentes, instala la dependencia
y define `MONGODB_URI`:

```bash
pip install -r requirements.txt
MONGODB_URI=mongodb://localhost:27017 python3 main.py
```

La URI debe apuntar a un replica set o clúster, ya que el listener de
sincronización usa Change Streams. La aplicación escribe solamente en
`almacen_1.productos`, `almacen_2.productos` o `almacen_3.productos`.
Ejecuta el listener en otro proceso:

```bash
MONGODB_URI=mongodb://localhost:27017 python3 run_listener.py
```

El listener usa un `MongoClient.watch()` global y replica hacia
`comparador.productos` con consistencia eventual. Al iniciar la aplicación, los
inventarios visibles se cargan directamente desde las bases dedicadas
`almacen_X`, que son la fuente de verdad; por ello pueden mostrarse aunque el
listener esté detenido. Cada documento requiere un
`producto_id` estable y se replica con `_id` compuesto
`{almacen_id}_{producto_id}`. Guarda el resume token en
`comparador.sync_state`; si MongoDB devuelve `ChangeStreamHistoryLost` (286),
realiza una reconciliación completa y reanuda desde un punto de corte anterior
al escaneo.

Para un replica set local de un nodo:

```bash
docker run --name compras-mongo -p 27017:27017 -d \
  mongo:7 --replSet rs0 --bind_ip_all
docker exec compras-mongo mongosh --eval \
  'rs.initiate({_id:"rs0",members:[{_id:0,host:"localhost:27017"}]})'
```

Credenciales de administrador: **`admin123`**.
Se puede cambiar con la variable de entorno `ADMIN_CLAVE`:

```bash
ADMIN_CLAVE=mi_clave python3 main.py
```

## Flujos principales

### Usuario (rol CLIENTE)

1. `Ingresar como Usuario` → se pide un nombre (se registra si es nuevo).
2. Se agregan nombres a **Mi lista de compras** (se rechazan duplicados).
3. Se elige un modo de búsqueda y se pulsa **Buscar**:
   - *Mejor precio por almacén*: el producto más barato de cada almacén.
   - *Catálogo completo*: todas las coincidencias por almacén.
   - *Mejor precio global*: el almacén más barato para cada producto.
4. Se selecciona un resultado y **Agregar al carrito**.
5. En **Mi carrito** se aplican descuentos (sin descuento, porcentaje o monto
   fijo), se quitan ítems y se ve el total en tiempo real (patrón Observer).
6. **Exportar lista** / **Exportar carrito** generan archivos CSV.

### Administrador (rol ADMIN)

1. `Administrar Almacenes` → clave de acceso.
2. Alta de productos con nombre, marca, categoría, tipo
   (`normal`, `fisico`, `digital`, `suscripcion`), precio y un extra
   (costo de envío o meses de suscripción).
3. Edición de precio: se selecciona un producto del inventario, se escribe el
   nuevo precio y se pulsa **Actualizar**.
4. **Cargar CSV...** importa productos de forma masiva (ver formato abajo).

### Modo consola

`python3 main.py --consola` ofrece el mismo circuito sin Tkinter:

- carrito y descuentos,
- lista de compras (con rechazo de duplicados),
- búsqueda de mejores precios y vista de almacenes,
- opción 9: login de administrador para cargar productos o un CSV.

La vista sigue actuando como observador del carrito, por lo que cada cambio
imprime la notificación y el total en tiempo real.

## Formato del CSV

Cabecera obligatoria: `almacen,nombre,marca,categoria,tipo,precio,extra`

```csv
almacen,nombre,marca,categoria,tipo,precio,extra
1,Leche,LaSerenisima,Lacteos,normal,1200,
2,Leche,Ilolay,Lacteos,normal,1100,
1,Curso Python,Udemy,Digital,digital,50,
1,Netflix,Netflix,Streaming,suscripcion,10,3
2,Caja,Generica,General,fisico,100,7
```

- `almacen`: id (1, 2 o 3).
- `tipo`: si se omite, se asume `normal`.
- `extra`: costo de envío para `fisico`, meses para `suscripcion`.
- Las filas inválidas se rechazan y se informan con su número de línea.

El repositorio incluye **`productos_ejemplo.csv`** con 57 productos repartidos
entre los tres almacenes (19 / 18 / 20). Para cargarlo:

- GUI: `Administrar Almacenes` → clave → **Cargar CSV...**
- Consola: opción `9` → clave → opción `2` → ruta `productos_ejemplo.csv`

Incluye productos repetidos en varios almacenes con precios distintos (Leche,
Pan, Arroz, Mouse, Monitor, Netflix, etc.) y ejemplos de los cuatro tipos:
`normal`, `fisico`, `digital` y `suscripcion`.

## Estructura del proyecto

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Bootstrapper: parsea argumentos y cablea modelo, vista y controlador. |
| `modelos.py` | Productos, Factory Method y utilidades de normalización. |
| `observer.py` | `SujetoObservable` reutilizable (Observer). |
| `listas.py` | `ListaSimple`, `ListaDoblementeEnlazada` y `CarritoCompras`. |
| `almacenes.py` | `Almacen` (inventario en lista simple) y `GestorAlmacenes`. |
| `persistencia_mongodb.py` | Escrituras en las bases dedicadas y lectura de la proyección. |
| `listener_mongodb.py` | Change Stream global y réplica idempotente a `comparador`. |
| `estrategias.py` | Estrategias de descuento y de búsqueda (Strategy). |
| `controlador.py` | Lógica de aplicación, sesiones, permisos y operaciones. |
| `interfaz.py` | Vista Tkinter (menú, usuario, login y panel admin). |
| `permisos.py` | Matriz de permisos por rol y `Logger`. |
| `pruebas.py` | Pruebas unitarias con `unittest`. |
| `pruebas_gui.py` | Prueba de humo de la interfaz Tkinter. |

## Patrones de diseño

| Patrón | Dónde |
|---|---|
| **Factory Method** | `Producto` y subclases creadas por `FabricaProductos.crear_producto()`. |
| **Observer** | `CarritoCompras` notifica a `InterfazUsuario.actualizar()` en cada cambio. |
| **Strategy** | Descuentos (`SinDescuento`, `DescuentoPorcentaje`, `DescuentoFijo`) y búsquedas (`BusquedaMejorPrecioStrategy`, `BusquedaCatalogoStrategy`, `MejorPrecioGlobalStrategy`). |
| **MVC** | Modelo (`modelos`, `listas`, `almacenes`), vista (`interfaz`) y controlador (`controlador`). |
| **Bootstrapper** | `main.py` compone las dependencias. |

## Roles y permisos

| Permiso | INVITADO | CLIENTE | ADMIN |
|---|:---:|:---:|:---:|
| ver_menu | ✓ | ✓ | ✓ |
| crear_lista / agregar / eliminar / comparar / exportar / aplicar_descuento | | ✓ | ✓ |
| gestionar_almacenes / editar_precio / cargar_csv / login_admin | | | ✓ |

Cada operación sensible pasa por `logger.tiene_permiso()` y deja un registro en
consola con el resultado (`CONCEDIDO` / `DENEGADO`).

## Pruebas

```bash
python3 -m compileall -q .
python3 pruebas.py
python3 pruebas_gui.py        # requiere display; en CI: xvfb-run python3 pruebas_gui.py
```

`pruebas.py` cubre listas enlazadas, Factory, descuentos, búsquedas, Observer y
el flujo completo del controlador (permisos, carrito, CSV y exportación).

## Limitaciones

- Sin `MONGODB_URI`, los datos viven en memoria: al cerrar la aplicación se reinician.
- Con MongoDB, `comparador` tiene consistencia eventual mientras el listener
  procesa los cambios.
- Los usuarios son solo nombres; no hay contraseñas por usuario.
- La clave de administrador es única y local.
