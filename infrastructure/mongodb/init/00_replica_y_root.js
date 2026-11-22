/*
 * Bootstrap del replica set con autenticación.
 *
 * Este script se ejecuta desde el servicio ``mongo-init`` con
 * ``network_mode: service:mongodb``, por lo que ``127.0.0.1`` es el propio
 * mongod y aplica la excepción de localhost para crear el primer usuario.
 *
 * Es idempotente:
 *   1. Si el usuario root ya existe, se autentica.
 *   2. Si es un volumen nuevo, inicia el replica set y crea root.
 *   3. Reconfigura el host anunciado si el volumen se creó con otro nombre.
 */

const rootUser = process.env.MONGO_ROOT_USER || "root";
const rootPassword = process.env.MONGO_ROOT_PASSWORD;
const replicaHost = process.env.MONGO_REPLICA_HOST || "mongodb:27017";

if (!rootPassword) {
  print("MONGO_ROOT_PASSWORD es obligatoria");
  quit(1);
}

function autenticar() {
  try {
    const resultado = db.getSiblingDB("admin").auth(rootUser, rootPassword);
    return resultado === 1 || (resultado && resultado.ok === 1);
  } catch (error) {
    return false;
  }
}

function esperarPrimario(intentos) {
  for (let i = 0; i < intentos; i++) {
    try {
      if (db.hello().isWritablePrimary) {
        return true;
      }
    } catch (error) {
      /* El nodo todavía no acepta conexiones. */
    }
    sleep(500);
  }
  return false;
}

const admin = db.getSiblingDB("admin");
let autenticado = autenticar();

if (!autenticado) {
  print("Primer arranque con autenticación: inicializando replica set y usuario root...");

  try {
    rs.initiate({ _id: "rs0", members: [{ _id: 0, host: replicaHost }] });
    print("Replica set rs0 iniciado con " + replicaHost);
  } catch (error) {
    // Ya estaba iniciado. La excepción de localhost solo permite crear el
    // primer usuario; el resto de comandos requieren autenticación.
    print("rs.initiate: " + error.codeName + " (" + error.message + ")");
  }

  if (!esperarPrimario(60)) {
    print("El replica set no alcanzó el estado primario");
    quit(1);
  }

  try {
    admin.createUser({
      user: rootUser,
      pwd: rootPassword,
      roles: [{ role: "root", db: "admin" }],
    });
    print("Usuario " + rootUser + " creado en admin");
  } catch (error) {
    print(
      "No se pudo crear " + rootUser + ": " + error.codeName + " " + error.message
    );
    print("Si el usuario ya existe, revisa MONGO_ROOT_PASSWORD.");
    quit(1);
  }

  autenticado = autenticar();
}

if (!autenticado) {
  print("No se pudo autenticar como " + rootUser);
  quit(1);
}

// Un volumen creado con otro hostname (por ejemplo localhost:27017) anuncia
// una dirección inalcanzable para los demás contenedores.
try {
  const configuracion = rs.conf();
  const hosts = configuracion.members.map((miembro) => miembro.host);
  if (hosts.length !== 1 || hosts[0] !== replicaHost) {
    print("Reconfigurando miembros " + JSON.stringify(hosts) + " -> " + replicaHost);
    configuracion.members = [{ _id: 0, host: replicaHost }];
    configuracion.version = (configuracion.version || 1) + 1;
    rs.reconfig(configuracion, { force: true });
  }
  if (!esperarPrimario(60)) {
    print("El replica set no alcanzó el estado primario tras reconfigurar");
    quit(1);
  }
  print("Primario listo en " + replicaHost);
} catch (error) {
  print("No se pudo verificar el replica set: " + error.codeName + " " + error.message);
  quit(1);
}
