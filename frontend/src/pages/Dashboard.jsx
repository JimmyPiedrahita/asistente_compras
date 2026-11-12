import { useCallback, useEffect, useState } from "react";
import { ENDPOINTS, api, errorText } from "../api";
import Icon from "../components/Icon";
import {
  Alert,
  Badge,
  Button,
  Card,
  Money,
  Spinner,
  Stat,
} from "../components/ui";
import { useApp } from "../context/AppContext";

const HEALTH_ENDPOINTS = [
  { key: "live", label: "Liveness", path: "/health/live", check: () => api.healthLive() },
  { key: "ready", label: "Readiness", path: "/health/ready", check: () => api.healthReady() },
  { key: "health", label: "Salud completa", path: "/health", check: () => api.health() },
];

function HealthCard({ item, result, onRetry }) {
  const ok = result?.state === "ok";
  const failed = result?.state === "error";
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-slate-400">
            {item.label}
          </p>
          <p className="mt-1 font-mono text-xs text-slate-500">GET {item.path}</p>
        </div>
        {result?.state === "loading" ? (
          <Spinner size={16} className="text-slate-400" />
        ) : (
          <span
            className={`grid h-8 w-8 place-items-center rounded-md bg-slate-100 ${
              failed ? "text-rose-600" : "text-slate-500"
            }`}
          >
            <Icon name={ok ? "check" : failed ? "alert" : "database"} size={16} />
          </span>
        )}
      </div>
      <div className="mt-3">
        {ok && (
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="emerald">200 OK</Badge>
            <span className="text-xs text-slate-500">
              status: <span className="font-mono">{result.data?.status}</span>
              {result.data?.database ? ` · db: ${result.data.database}` : ""}
            </span>
          </div>
        )}
        {failed && (
          <div className="space-y-2">
            <Badge tone="rose">sin respuesta</Badge>
            <p className="line-clamp-2 text-xs text-rose-600">{errorText(result.error)}</p>
          </div>
        )}
        {!ok && !failed && result?.state !== "loading" && (
          <Badge tone="slate">pendiente</Badge>
        )}
      </div>
      {failed && (
        <button
          onClick={onRetry}
          className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900"
        >
          <Icon name="refresh" size={12} /> Reintentar
        </button>
      )}
    </div>
  );
}

export default function Dashboard({ onNavigate }) {
  const { session, token, apiBase, docs, can } = useApp();
  const [health, setHealth] = useState(() =>
    Object.fromEntries(HEALTH_ENDPOINTS.map((item) => [item.key, { state: "loading" }])),
  );
  const [warehouses, setWarehouses] = useState({ loading: true, items: [], error: null });
  const [sessionInfo, setSessionInfo] = useState({ loading: false, data: null, error: null });

  const checkHealth = useCallback(async () => {
    setHealth((current) =>
      Object.fromEntries(
        Object.entries(current).map(([key, value]) => [key, { ...value, state: "loading" }]),
      ),
    );
    const results = await Promise.allSettled(HEALTH_ENDPOINTS.map((item) => item.check()));
    setHealth(
      Object.fromEntries(
        HEALTH_ENDPOINTS.map((item, index) => {
          const result = results[index];
          return [
            item.key,
            result.status === "fulfilled"
              ? { state: "ok", data: result.value.data }
              : { state: "error", error: result.reason },
          ];
        }),
      ),
    );
  }, []);

  const loadWarehouses = useCallback(async () => {
    setWarehouses((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.listWarehouses();
      setWarehouses({ loading: false, items: data || [], error: null });
    } catch (error) {
      setWarehouses({ loading: false, items: [], error });
    }
  }, []);

  useEffect(() => {
    checkHealth();
    loadWarehouses();
  }, [checkHealth, loadWarehouses]);

  useEffect(() => {
    if (!token) {
      setSessionInfo({ loading: false, data: null, error: null });
      return;
    }
    let cancelled = false;
    setSessionInfo({ loading: true, data: null, error: null });
    api
      .getSession(token)
      .then(({ data }) => {
        if (!cancelled) setSessionInfo({ loading: false, data, error: null });
      })
      .catch((error) => {
        if (!cancelled) setSessionInfo({ loading: false, data: null, error });
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const totalProducts = warehouses.items.reduce(
    (sum, warehouse) => sum + Number(warehouse.products || 0),
    0,
  );
  const healthy = HEALTH_ENDPOINTS.filter((item) => health[item.key]?.state === "ok").length;
  const groups = ENDPOINTS.reduce((acc, endpoint) => {
    acc[endpoint.group] = (acc[endpoint.group] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.08em] text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-900" />
              Consola integral
            </span>
            <h2 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
              Todos los endpoints del Asistente de Compras
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">
              Prueba salud, inventarios, sesiones, lista de compras, búsquedas, carrito,
              administración y exportaciones desde una sola interfaz.
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-2">
              {can("comparar") ? (
                <Button size="sm" icon="search" onClick={() => onNavigate("busqueda")}>
                  Buscar productos
                </Button>
              ) : can("gestionar_inventario") ? (
                <Button size="sm" icon="settings" onClick={() => onNavigate("admin")}>
                  Gestionar inventario
                </Button>
              ) : (
                <Button size="sm" icon="key" onClick={() => onNavigate("sesion")}>
                  Iniciar sesión
                </Button>
              )}
              <Button
                size="sm"
                variant="secondary"
                icon="warehouse"
                onClick={() => onNavigate("almacenes")}
              >
                Ver almacenes
              </Button>
              <Button
                size="sm"
                variant="secondary"
                icon="shield"
                onClick={() => onNavigate("roles")}
              >
                Roles y permisos
              </Button>
              <a
                href={docs}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-slate-500 transition hover:text-slate-900"
              >
                Swagger <Icon name="external" size={12} />
              </a>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-left sm:grid-cols-4 lg:grid-cols-2">
            {[
              ["Endpoints", ENDPOINTS.length],
              ["Almacenes", warehouses.items.length],
              ["Health OK", `${healthy}/3`],
              ["API base", apiBase.replace(/^https?:\/\//, "")],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 px-4 py-3">
                <p
                  className={`truncate font-semibold text-slate-900 ${
                    label === "API base" ? "text-xs" : "text-xl"
                  }`}
                  title={String(value)}
                >
                  {value}
                </p>
                <p className="mt-0.5 text-[10px] uppercase tracking-[0.08em] text-slate-400">
                  {label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Almacenes activos"
          value={warehouses.loading ? "…" : warehouses.items.length}
          hint="GET /warehouses"
          icon="warehouse"
        />
        <Stat
          label="Productos totales"
          value={warehouses.loading ? "…" : totalProducts}
          hint="Suma de inventarios"
          icon="package"
        />
        <Stat
          label="Sesión actual"
          value={session ? session.rol : "Sin sesión"}
          hint={session ? session.usuario : "Crea una sesión para continuar"}
          icon="key"
        />
        {can("agregar_producto") ? (
          <Stat
            label="Carrito"
            value={
              sessionInfo.loading
                ? "…"
                : sessionInfo.data
                  ? <Money value={sessionInfo.data.carrito?.total} />
                  : "—"
            }
            hint={
              sessionInfo.data
                ? `${sessionInfo.data.carrito?.productos?.length || 0} ítems`
                : "GET /sessions/{token}"
            }
            icon="cart"
          />
        ) : can("gestionar_inventario") ? (
          <Stat
            label="Almacén asignado"
            value={session?.almacen_id ?? "—"}
            hint={session ? session.rol : "Sin sesión"}
            icon="warehouse"
          />
        ) : (
          <Stat
            label="Permisos"
            value={session ? session.permisos?.length ?? 0 : "—"}
            hint={session ? session.rol : "Inicia sesión para autorizar acciones"}
            icon="shield"
          />
        )}
      </div>

      <Card
        title="Estado de la API"
        description="Tres endpoints de salud consultados en paralelo."
        actions={
          <Button size="sm" variant="secondary" icon="refresh" onClick={checkHealth}>
            Actualizar
          </Button>
        }
      >
        <div className="grid gap-3 md:grid-cols-3">
          {HEALTH_ENDPOINTS.map((item) => (
            <HealthCard
              key={item.key}
              item={item}
              result={health[item.key]}
              onRetry={checkHealth}
            />
          ))}
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card
          title="Almacenes"
          description="Inventarios disponibles y cantidad de productos."
          className="xl:col-span-2"
          actions={
            <Button size="sm" variant="secondary" icon="external" onClick={() => onNavigate("almacenes")}>
              Abrir
            </Button>
          }
        >
          {warehouses.loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
              <Spinner /> Cargando almacenes…
            </div>
          ) : warehouses.error ? (
            <Alert tone="error" title="No se pudieron cargar los almacenes">
              {errorText(warehouses.error)}
            </Alert>
          ) : warehouses.items.length === 0 ? (
            <Alert tone="warning" title="No hay almacenes configurados">
              Revisa <span className="font-mono">WAREHOUSES</span> y la conexión a MongoDB.
            </Alert>
          ) : (
            <div className="divide-y divide-slate-100">
              {warehouses.items.map((warehouse) => (
                <div key={warehouse.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-slate-100 text-slate-500">
                      <Icon name="warehouse" size={15} />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-800">
                        {warehouse.name}
                      </p>
                      <p className="font-mono text-xs text-slate-400">ID {warehouse.id}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge tone="slate">{warehouse.products} productos</Badge>
                    <button
                      onClick={() => onNavigate("almacenes")}
                      className="rounded-md p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
                      aria-label={`Ver ${warehouse.name}`}
                    >
                      <Icon name="arrow" size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Cobertura de la consola" description={`${ENDPOINTS.length} rutas agrupadas por dominio.`}>
          <div className="space-y-2">
            {Object.entries(groups).map(([group, count]) => (
              <div
                key={group}
                className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/60 px-3 py-2"
              >
                <span className="text-sm text-slate-600">{group}</span>
                <Badge tone="slate">{count}</Badge>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">
            <p className="font-medium text-slate-900">Sesión requerida</p>
            <p className="mt-0.5">
              Las rutas de lista, carrito, búsqueda, administración y exportación envían el
              token como <span className="font-mono">Authorization: Bearer</span>.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
