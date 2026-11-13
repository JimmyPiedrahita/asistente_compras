#!/usr/bin/env bash
# Verifica los roles nativos de MongoDB del docker-compose.
#
# Requiere el stack levantado y las variables MONGO_* del .env.
# Uso:
#   bash scripts/verificar_rbac_mongodb.sh
#   make rbac-test

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  . ./.env
  set +a
fi

: "${MONGO_DEMO_PASSWORD:?Define MONGO_DEMO_PASSWORD}"
: "${MONGO_ROOT_USER:=root}"
: "${MONGO_ROOT_PASSWORD:?Define MONGO_ROOT_PASSWORD}"
: "${MONGO_APP_USER:=app_asistente}"
: "${MONGO_APP_PASSWORD:?Define MONGO_APP_PASSWORD}"

BASE_URI="127.0.0.1:27017/?authSource=admin&directConnection=true"
COLECCION="__rbac_check"
FALLOS=0

uri_demo() {
  echo "mongodb://${1}:${MONGO_DEMO_PASSWORD}@${BASE_URI}"
}

ejecutar_como() {
  local usuario="$1"
  local codigo="$2"
  docker compose exec -T mongodb mongosh --quiet "$(uri_demo "$usuario")" --eval "$codigo"
}

limpiar() {
  docker compose exec -T mongodb mongosh --quiet \
    "mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@${BASE_URI}" \
    --eval "
      ['warehouse_1','warehouse_2','warehouse_3'].forEach((base) => {
        db.getSiblingDB(base).getCollection('${COLECCION}').drop();
      });
    " >/dev/null 2>&1 || true
}
trap limpiar EXIT

comprobar() {
  local descripcion="$1"
  local esperado="$2"
  local salida="$3"
  if [[ "$salida" == *"$esperado"* ]]; then
    echo "OK   $descripcion"
  else
    echo "FALLO $descripcion (se esperaba '$esperado', salida: $salida)"
    FALLOS=$((FALLOS + 1))
  fi
}

echo "Verificando RBAC nativo de MongoDB..."
docker compose exec -T mongodb mongosh --quiet \
  "mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@${BASE_URI}" \
  --eval 'db.adminCommand({ ping: 1 })' >/dev/null

salida="$(ejecutar_como u_proveedor "
  try {
    db.getSiblingDB('warehouse_1').getCollection('${COLECCION}').insertOne({ok: 1});
    print('PERMITIDO');
  } catch (error) {
    print('DENEGADO');
  }
")"
comprobar "u_proveedor escribe warehouse_1" "PERMITIDO" "$salida"

salida="$(ejecutar_como u_proveedor "
  try {
    db.getSiblingDB('warehouse_2').getCollection('${COLECCION}').insertOne({ok: 1});
    print('PERMITIDO');
  } catch (error) {
    print('DENEGADO');
  }
")"
comprobar "u_proveedor NO escribe warehouse_2" "DENEGADO" "$salida"

salida="$(ejecutar_como u_cliente "
  try {
    db.getSiblingDB('warehouse_1').getCollection('${COLECCION}').insertOne({ok: 1});
    print('PERMITIDO');
  } catch (error) {
    print('DENEGADO');
  }
")"
comprobar "u_cliente NO escribe warehouse_1" "DENEGADO" "$salida"

salida="$(ejecutar_como u_cliente "
  print('DOCUMENTOS:' + db.getSiblingDB('comparador').productos.countDocuments({}));
")"
comprobar "u_cliente lee el comparador" "DOCUMENTOS:" "$salida"

salida="$(ejecutar_como u_gerente "
  try {
    db.getSiblingDB('warehouse_2').getCollection('${COLECCION}').insertOne({ok: 1});
    print('PERMITIDO');
  } catch (error) {
    print('DENEGADO');
  }
")"
comprobar "u_gerente hereda escritura de warehouse_2" "PERMITIDO" "$salida"

limpiar
trap - EXIT

echo
if [ "$FALLOS" -eq 0 ]; then
  echo "RBAC nativo verificado: todos los controles pasaron."
  exit 0
fi
echo "RBAC nativo con $FALLOS fallo(s)."
exit 1
