/*
 * Roles nativos globales de la aplicación.
 *
 * Se ejecuta después de 00_replica_y_root.js, autenticado como root.
 * Es idempotente: actualiza los roles si ya existen.
 *
 * Los privilegios sobre las bases de cada almacén se agregan dinámicamente
 * cuando el servicio de aprovisionamiento crea un almacén. Aquí solo se
 * definen los permisos sobre la base global.
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
  print("No se pudo autenticar como " + rootUser + " para crear roles");
  quit(1);
}

const globalDb = process.env.MONGODB_GLOBAL_DB || "global_asistente_compras";

function privilegio(coleccion, acciones) {
  return {
    resource: { db: globalDb, collection: coleccion },
    actions: acciones,
  };
}

function crearRol(nombre, privilegios, roles) {
  const actual = admin.getRole(nombre);
  if (actual) {
    admin.updateRole(nombre, { privileges: privilegios, roles: roles || [] });
    print("Rol actualizado: " + nombre);
  } else {
    admin.createRole({
      role: nombre,
      privileges: privilegios,
      roles: roles || [],
    });
    print("Rol creado: " + nombre);
  }
}

// Clientes: catálogo global, cupones y compras propias.
crearRol("rol_cliente", [
  privilegio("productos_global", ["find"]),
  privilegio("cupones_global", ["find"]),
  privilegio("almacenes", ["find"]),
  privilegio("compras", ["find", "insert", "update", "createIndex"]),
]);

// Administrador de la aplicación: almacenes y conteo de catálogo.
crearRol("rol_admin_app", [
  privilegio("almacenes", ["find", "insert", "update", "createIndex"]),
  privilegio("productos_global", ["find"]),
  privilegio("cupones_global", ["find"]),
]);

// Servicio de autenticación: usuarios de la aplicación.
crearRol("rol_auth", [
  privilegio("usuarios", ["find", "insert", "update", "createIndex"]),
]);

// Validador global de solo lectura.
crearRol("rol_validador", [
  privilegio("productos_global", ["find"]),
  privilegio("cupones_global", ["find"]),
]);

// Listener de catálogo: lee cambios de cada almacén y escribe la réplica
// global. Los privilegios de las bases de almacén se agregan al crearlas.
crearRol("rol_catalogo", [
  privilegio("productos_global", ["find", "insert", "update", "remove"]),
  privilegio("cupones_global", ["find", "insert", "update", "remove"]),
  privilegio("sync_state_catalogo", ["find", "insert", "update", "remove"]),
  privilegio("almacenes", ["find"]),
]);

// Proyector de compras: lee compras globales y escribe la proyección en cada
// base de almacén. Los privilegios de las bases de almacén se agregan al
// crearlas.
crearRol("rol_proyector", [
  privilegio("compras", ["find", "changeStream"]),
  privilegio("almacenes", ["find"]),
  privilegio("sync_state_compras", ["find", "insert", "update"]),
]);

print("");
print("Roles globales configurados en la base " + globalDb);
