/*
 * Índices de las colecciones globales.
 *
 * Se ejecuta después de 20_usuarios.js, autenticado como root.
 * Es idempotente: MongoDB no recrea un índice con la misma especificación.
 */

const admin = db.getSiblingDB("admin");
const rootUser = process.env.MONGO_ROOT_USER || "root";
const rootPassword = process.env.MONGO_ROOT_PASSWORD;

if (!rootPassword) {
  print("MONGO_ROOT_PASSWORD es obligatoria");
  quit(1);
}

const auth = admin.auth(rootUser, rootPassword);
if (!(auth === 1 || (auth && auth.ok === 1))) {
  print("No se pudo autenticar como " + rootUser + " para crear índices");
  quit(1);
}

const globalDb = process.env.MONGODB_GLOBAL_DB || "global_asistente_compras";
const base = db.getSiblingDB(globalDb);

function indices(coleccion, especificaciones) {
  especificaciones.forEach((especificacion) => {
    try {
      base[coleccion].createIndex(especificacion.clave, especificacion.opciones || {});
      print("Índice asegurado: " + coleccion + " " + JSON.stringify(especificacion.clave));
    } catch (error) {
      print(
        "No se pudo crear el índice de " + coleccion + ": " + error.codeName + " " + error.message
      );
      quit(1);
    }
  });
}

indices("usuarios", [
  { clave: { email_normalizado: 1 }, opciones: { unique: true, name: "email_unico" } },
  { clave: { rol: 1, almacen_id: 1 }, opciones: { name: "rol_almacen" } },
]);

indices("almacenes", [
  { clave: { nombre_normalizado: 1 }, opciones: { unique: true, name: "nombre_unico" } },
  { clave: { db_name: 1 }, opciones: { unique: true, name: "db_unica" } },
  { clave: { mongo_user: 1 }, opciones: { unique: true, name: "usuario_unico" } },
]);

indices("productos_global", [
  { clave: { tipo_normalizado: 1, precio: 1 }, opciones: { name: "tipo_precio" } },
  { clave: { almacen_id: 1, tipo_normalizado: 1 }, opciones: { name: "almacen_tipo" } },
  { clave: { presentacion_normalizada: 1 }, opciones: { name: "presentacion" } },
  { clave: { producto_id: 1 }, opciones: { name: "producto" } },
]);

indices("cupones_global", [
  { clave: { codigo_normalizado: 1 }, opciones: { unique: true, name: "codigo_unico" } },
  { clave: { almacen_id: 1 }, opciones: { name: "almacen" } },
]);

indices("compras", [
  {
    clave: { cliente_id: 1, clave_idempotencia: 1 },
    opciones: { unique: true, name: "idempotencia" },
  },
  { clave: { "items.almacen_id": 1, fecha: 1 }, opciones: { name: "almacen_fecha" } },
]);

print("");
print("Índices globales listos en " + globalDb);
