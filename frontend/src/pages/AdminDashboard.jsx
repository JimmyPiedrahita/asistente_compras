import { useCallback, useEffect, useState } from "react";
import { api, errorText } from "../api";
import Icon from "../components/Icon";
import { Badge, Button, Card, EmptyState, Spinner, Stat } from "../components/ui";
import { useApp } from "../context/AppContext";

export default function AdminDashboard({ onNavigate }) {
  const { session, token, notifyError } = useApp();
  const [warehouses, setWarehouses] = useState({ loading: true, items: [], error: null });
  const [users, setUsers] = useState({ loading: true, items: [], error: null });
  const [comparador, setComparador] = useState({ loading: true, data: null, error: null });

  const loadWarehouses = useCallback(async () => {
    setWarehouses({ loading: true, items: [], error: null });
    try {
      const { data } = await api.listWarehouses();
      setWarehouses({ loading: false, items: data || [], error: null });
    } catch (error) {
      setWarehouses({ loading: false, items: [], error });
    }
  }, []);

  const loadUsers = useCallback(async () => {
    if (!token) return;
    setUsers({ loading: true, items: [], error: null });
    try {
      const { data } = await api.listUsers(token);
      setUsers({ loading: false, items: data || [], error: null });
    } catch (error) {
      setUsers({ loading: false, items: [], error });
    }
  }, [token]);

  const loadComparador = useCallback(async () => {
    if (!token) return;
    setComparador({ loading: true, data: null, error: null });
    try {
      const { data } = await api.comparadorStatus(token);
      setComparador({ loading: false, data, error: null });
    } catch (error) {
      setComparador({ loading: false, data: null, error });
    }
  }, [token]);

  useEffect(() => {
    loadWarehouses();
    loadUsers();
    loadComparador();
  }, [loadWarehouses, loadUsers, loadComparador]);

  const totalProducts = warehouses.items.reduce(
    (sum, w) => sum + Number(w.products || 0),
    0,
  );

  if (warehouses.loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <Spinner /> Cargando panel de administración…
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">
          Panel de administración
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Gestiona usuarios, inventarios y el comparador de precios.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Almacenes"
          value={warehouses.items.length}
          hint="En el sistema"
          icon="warehouse"
        />
        <Stat
          label="Productos totales"
          value={totalProducts}
          hint="En todos los almacenes"
          icon="package"
        />
        <Stat
          label="Usuarios activos"
          value={users.loading ? "…" : users.items.filter((user) => user.activo).length}
          hint="Usuarios registrados"
          icon="user"
        />
        <Stat
          label="Comparador"
          value={
            comparador.loading
              ? "…"
              : comparador.error
                ? "Error"
                : comparador.data?.sincronizado
                  ? "Sincronizado"
                  : "Pendiente"
          }
          hint="Estado de reconciliación"
          icon="chart"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Almacenes"
          description={`${warehouses.items.length} almacenes con ${totalProducts} productos`}
          actions={
            <Button size="sm" variant="secondary" icon="warehouse" onClick={() => onNavigate("almacenes")}>
              Ver todos
            </Button>
          }
        >
          {warehouses.error ? (
            <EmptyState
              icon="alert"
              title="No se pudieron cargar los almacenes"
              description={errorText(warehouses.error)}
              action={<Button size="sm" icon="refresh" onClick={loadWarehouses}>Reintentar</Button>}
            />
          ) : warehouses.items.length === 0 ? (
            <EmptyState icon="warehouse" title="No hay almacenes" description="Configura los almacenes en el backend." />
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
                    </div>
                  </div>
                  <Badge tone="slate">{warehouse.products} productos</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card
          title="Usuarios activos"
          description={`${users.items.length} usuarios registrados`}
          actions={
            <Button size="sm" variant="secondary" icon="user" onClick={() => onNavigate("roles")}>
              Gestionar
            </Button>
          }
        >
          {users.loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
              <Spinner /> Cargando usuarios…
            </div>
          ) : users.error ? (
            <EmptyState
              icon="alert"
              title="No se pudieron cargar los usuarios"
              description={errorText(users.error)}
              action={<Button size="sm" icon="refresh" onClick={loadUsers}>Reintentar</Button>}
            />
          ) : users.items.length === 0 ? (
            <EmptyState
              icon="user"
              title="No hay usuarios aún"
              description="Los usuarios aparecerán aquí cuando inicien sesión."
            />
          ) : (
            <div className="divide-y divide-slate-100">
              {users.items.slice(0, 5).map((user) => (
                <div key={user.usuario_id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-800">
                      {user.nombre}
                    </p>
                    <p className="text-xs text-slate-400">
                      {user.rol}{user.almacen_id ? ` · Almacén ${user.almacen_id}` : ""}
                    </p>
                  </div>
                  <Badge tone={user.rol === "ADMIN" ? "dark" : user.rol === "PROVEEDOR" ? "slate" : "slate"}>
                    {user.rol}
                  </Badge>
                </div>
              ))}
              {users.items.length > 5 && (
                <p className="pt-2 text-xs text-slate-400">
                  +{users.items.length - 5} usuarios más…
                </p>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card title="Accesos rápidos">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Button variant="secondary" icon="warehouse" onClick={() => onNavigate("almacenes")}>
            Ver almacenes
          </Button>
          <Button variant="secondary" icon="settings" onClick={() => onNavigate("admin")}>
            Gestionar productos
          </Button>
          <Button variant="secondary" icon="search" onClick={() => onNavigate("busqueda")}>
            Comparar precios
          </Button>
          <Button variant="secondary" icon="user" onClick={() => onNavigate("roles")}>
            Usuarios y roles
          </Button>
        </div>
      </Card>
    </div>
  );
}
