/*
 * Usuarios de servicio de la aplicación.
 *
 * Se ejecuta después de 10_roles.js, autenticado como root.
 * Es idempotente: actualiza la contraseña y los roles si el usuario existe.
 *
 * Los usuarios de almacén (``almacen_<db>_app``) no se crean aquí: los crea
 * el servicio de aprovisionamiento con una contraseña derivada por HMAC.
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
  print("No se pudo autenticar como " + rootUser + " para crear usuarios");
  quit(1);
}

function requerido(nombre) {
  const valor = process.env[nombre];
  if (!valor) {
    print("Falta la variable de entorno " + nombre);
    quit(1);
  }
  return valor;
}

function crearUsuario(nombre, password, roles) {
  if (!password) {
    print("Falta la contraseña del usuario " + nombre);
    quit(1);
  }
  if (admin.getUser(nombre)) {
    admin.updateUser(nombre, { pwd: password, roles: roles });
    print("Usuario actualizado: " + nombre);
  } else {
    admin.createUser({ user: nombre, pwd: password, roles: roles });
    print("Usuario creado: " + nombre);
  }
}

const usuarios = [
  {
    nombre: process.env.MONGO_CLIENTE_USER || "cliente_app",
    password: requerido("MONGO_CLIENTE_PASSWORD"),
    roles: [{ role: "rol_cliente", db: "admin" }],
  },
  {
    nombre: process.env.MONGO_ADMIN_APP_USER || "admin_app",
    password: requerido("MONGO_ADMIN_APP_PASSWORD"),
    roles: [{ role: "rol_admin_app", db: "admin" }],
  },
  {
    nombre: process.env.MONGO_AUTH_USER || "auth_service",
    password: requerido("MONGO_AUTH_PASSWORD"),
    roles: [{ role: "rol_auth", db: "admin" }],
  },
  {
    nombre: process.env.MONGO_VALIDADOR_USER || "validador_catalogo",
    password: requerido("MONGO_VALIDADOR_PASSWORD"),
    roles: [{ role: "rol_validador", db: "admin" }],
  },
  {
    nombre: process.env.MONGO_CATALOGO_USER || "replicador_catalogo",
    password: requerido("MONGO_CATALOGO_PASSWORD"),
    roles: [{ role: "rol_catalogo", db: "admin" }],
  },
  {
    nombre: process.env.MONGO_COMPRAS_USER || "proyector_compras",
    password: requerido("MONGO_COMPRAS_PASSWORD"),
    roles: [{ role: "rol_proyector", db: "admin" }],
  },
  {
    nombre: process.env.MONGO_PROVISIONER_USER || "provisioner",
    password: requerido("MONGO_PROVISIONER_PASSWORD"),
    roles: [
      { role: "userAdminAnyDatabase", db: "admin" },
      { role: "dbAdminAnyDatabase", db: "admin" },
    ],
  },
];

usuarios.forEach((usuario) => crearUsuario(usuario.nombre, usuario.password, usuario.roles));

print("");
print("Usuarios de servicio configurados: " + usuarios.map((u) => u.nombre).join(", "));
