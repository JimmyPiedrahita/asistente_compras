/*
 * Roles y usuarios nativos de MongoDB para la demostración de RBAC.
 *
 * Se ejecuta después de 00_replica_y_root.js, autenticado como root.
 * Es idempotente: actualiza roles y usuarios si ya existen.
 *
 * Capas de seguridad del proyecto:
 *   - MongoDB: estos roles controlan qué puede hacer cada credencial al
 *     conectarse con mongosh, Compass o un driver.
 *   - Aplicación: models/permisos.py controla qué puede hacer cada sesión
 *     HTTP (CLIENTE, PROVEEDOR, ADMIN) dentro de la API.
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
  print("No se pudo autenticar como " + rootUser + " para crear roles y usuarios");
  quit(1);
}

const prefijo = process.env.MONGODB_DB_PREFIX || "warehouse";
const comparador = process.env.MONGODB_COMPARADOR_DB || "comparador";
const seguridad = process.env.MONGODB_SEGURIDAD_DB || "seguridad";
const demoPassword = process.env.MONGO_DEMO_PASSWORD;
const appUser = process.env.MONGO_APP_USER || "app_asistente";
const appPassword = process.env.MONGO_APP_PASSWORD;

if (!demoPassword || !appPassword) {
  print("MONGO_DEMO_PASSWORD y MONGO_APP_PASSWORD son obligatorias");
  quit(1);
}

const idsAlmacenes = (process.env.WAREHOUSES || "1,2,3")
  .split(",")
  .map((parte) => parte.trim().split(":")[0])
  .filter((id) => id.length > 0);

if (idsAlmacenes.length === 0) {
  print("No se configuraron almacenes en WAREHOUSES");
  quit(1);
}

const almacenes = idsAlmacenes.map((id) => prefijo + "_" + id);
const almacenPrincipal = almacenes[0];
const almacenesSecundarios = almacenes.slice(1);

function crearRol(nombre, privilegios, roles) {
  const actual = admin.getRole(nombre);
  if (actual) {
    admin.updateRole(nombre, { privileges: privilegios, roles: roles });
    print("Rol actualizado: " + nombre + " (" + roles.length + " roles heredados)");
  } else {
    admin.createRole({ role: nombre, privileges: privilegios, roles: roles });
    print("Rol creado: " + nombre + " (" + roles.length + " roles heredados)");
  }
}

function crearUsuario(nombre, password, roles) {
  if (admin.getUser(nombre)) {
    admin.updateUser(nombre, { pwd: password, roles: roles });
    print("Usuario actualizado: " + nombre);
  } else {
    admin.createUser({ user: nombre, pwd: password, roles: roles });
    print("Usuario creado: " + nombre);
  }
}

// ---------------------------------------------------------------------------
// Roles de MongoDB
// ---------------------------------------------------------------------------

// 1. CLIENTE: lectura de catálogos y del comparador. No puede escribir.
crearRol(
  "rol_cliente",
  [],
  almacenes
    .map((base) => ({ role: "read", db: base }))
    .concat([{ role: "read", db: comparador }])
);

// 2. PROVEEDOR: escribe únicamente el primer almacén configurado.
crearRol(
  "rol_proveedor",
  [],
  [
    { role: "readWrite", db: almacenPrincipal },
    { role: "read", db: comparador },
  ]
);

// 3. GERENTE: hereda PROVEEDOR y CLIENTE, y además escribe el resto de
//    almacenes. Demuestra la jerarquía de roles del material de clase.
crearRol(
  "rol_gerente",
  [],
  [
    { role: "rol_proveedor", db: "admin" },
    { role: "rol_cliente", db: "admin" },
  ].concat(almacenesSecundarios.map((base) => ({ role: "readWrite", db: base })))
);

// 4. ADMINISTRADOR: lectura y escritura de todos los almacenes, el
//    comparador y la base de seguridad de la aplicación.
crearRol(
  "rol_administrador",
  [],
  almacenes
    .map((base) => ({ role: "readWrite", db: base }))
    .concat([
      { role: "readWrite", db: comparador },
      { role: "readWrite", db: seguridad },
    ])
);

// ---------------------------------------------------------------------------
// Usuarios de demostración (mongosh / Compass)
// ---------------------------------------------------------------------------

crearUsuario("u_cliente", demoPassword, [{ role: "rol_cliente", db: "admin" }]);
crearUsuario("u_proveedor", demoPassword, [{ role: "rol_proveedor", db: "admin" }]);
crearUsuario("u_gerente", demoPassword, [{ role: "rol_gerente", db: "admin" }]);
crearUsuario("u_admin", demoPassword, [{ role: "rol_administrador", db: "admin" }]);

// Usuario de servicio que usa la API y el listener. No es root: solo tiene
// permisos sobre las bases del proyecto. readAnyDatabase es necesario para el
// Change Stream a nivel de cluster que usa el listener (allChangesForCluster).
crearUsuario(appUser, appPassword, [
  { role: "rol_administrador", db: "admin" },
  { role: "readAnyDatabase", db: "admin" },
]);

print("");
print("=== RBAC nativo de MongoDB configurado ===");
print("Almacenes: " + almacenes.join(", "));
print("Roles: rol_cliente, rol_proveedor, rol_gerente, rol_administrador");
print("Usuarios demo: u_cliente, u_proveedor, u_gerente, u_admin");
print("Usuario de la API: " + appUser);
print("");
print("Prueba desde el host:");
print(
  '  mongosh "mongodb://u_proveedor:' +
    demoPassword +
    '@127.0.0.1:27017/?authSource=admin&directConnection=true"'
);
print(
  '  mongosh "mongodb://u_gerente:' +
    demoPassword +
    '@127.0.0.1:27017/?authSource=admin&directConnection=true"'
);
print("");
