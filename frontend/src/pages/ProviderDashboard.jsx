import { useCallback, useEffect, useState } from "react";
import { api, errorText } from "../api";
import Icon from "../components/Icon";
import { Badge, Button, Card, EmptyState, Money, Spinner, Stat } from "../components/ui";
import { useApp } from "../context/AppContext";

export default function ProviderDashboard({ onNavigate }) {
  const { session, token, notifyError } = useApp();
  const [warehouses, setWarehouses] = useState({ loading: true, items: [], error: null });
  const [warehouseProducts, setWarehouseProducts] = useState({ loading: false, items: [], error: null });

  const loadWarehouses = useCallback(async () => {
    setWarehouses({ loading: true, items: [], error: null });
    try {
      const { data } = await api.listWarehouses();
      setWarehouses({ loading: false, items: data || [], error: null });
    } catch (error) {
      setWarehouses({ loading: false, items: [], error });
    }
  }, []);

  const loadMyProducts = useCallback(async () => {
    if (!session?.almacen_id) return;
    setWarehouseProducts({ loading: true, items: [], error: null });
    try {
      const { data } = await api.listProducts(session.almacen_id, { limit: 100, offset: 0 });
      setWarehouseProducts({ loading: false, items: data || [], error: null });
    } catch (error) {
      setWarehouseProducts({ loading: false, items: [], error });
    }
  }, [session?.almacen_id]);

  useEffect(() => {
    loadWarehouses();
  }, [loadWarehouses]);

  useEffect(() => {
    loadMyProducts();
  }, [loadMyProducts]);

  const myWarehouse = warehouses.items.find((w) => w.id === session?.almacen_id);
  const totalProducts = warehouseProducts.items.length;

  if (warehouses.loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <Spinner /> Cargando tu panel…
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">
          ¡Hola, {session?.usuario}!
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Gestiona el inventario de tu almacén desde aquí.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat
          label="Tu almacén"
          value={myWarehouse?.name || session?.almacen_id || "—"}
          hint="Almacén asignado"
          icon="warehouse"
        />
        <Stat
          label="Productos registrados"
          value={warehouseProducts.loading ? "…" : totalProducts}
          hint="En tu inventario"
          icon="package"
        />
        <Stat
          label="Total de almacenes"
          value={warehouses.items.length}
          hint="En el sistema"
          icon="database"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Tu inventario"
          description={`${totalProducts} productos en ${myWarehouse?.name || "tu almacén"}`}
          actions={
            <Button size="sm" variant="secondary" icon="warehouse" onClick={() => onNavigate("almacenes")}>
              Ver todo
            </Button>
          }
        >
          {warehouseProducts.loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
              <Spinner /> Cargando productos…
            </div>
          ) : warehouseProducts.error ? (
            <EmptyState
              icon="alert"
              title="No se pudo cargar el inventario"
              description={errorText(warehouseProducts.error)}
              action={<Button size="sm" icon="refresh" onClick={loadMyProducts}>Reintentar</Button>}
            />
          ) : totalProducts === 0 ? (
            <EmptyState
              icon="package"
              title="No hay productos aún"
              description="Importa productos desde un archivo CSV o agrégalos manualmente."
              action={
                <Button size="sm" icon="settings" onClick={() => onNavigate("admin")}>
                  Gestionar inventario
                </Button>
              }
            />
          ) : (
            <div className="divide-y divide-slate-100">
              {warehouseProducts.items.slice(0, 5).map((product) => (
                <div key={product.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-800">
                      {product.nombre}
                    </p>
                    <p className="text-xs text-slate-400">{product.tipo}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Money value={product.precio} />
                    <Badge tone="slate">{product.stock || 0} uds</Badge>
                  </div>
                </div>
              ))}
              {totalProducts > 5 && (
                <p className="pt-2 text-xs text-slate-400">
                  +{totalProducts - 5} productos más…
                </p>
              )}
            </div>
          )}
        </Card>

        <Card
          title="Todos los almacenes"
          description={`${warehouses.items.length} almacenes en el sistema`}
        >
          {warehouses.error ? (
            <EmptyState
              icon="alert"
              title="No se pudieron cargar los almacenes"
              description={errorText(warehouses.error)}
              action={<Button size="sm" icon="refresh" onClick={loadWarehouses}>Reintentar</Button>}
            />
          ) : warehouses.items.length === 0 ? (
            <EmptyState icon="warehouse" title="No hay almacenes" description="Contacta al administrador." />
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
                      {warehouse.id === session?.almacen_id && (
                        <Badge tone="indigo">Tu almacén</Badge>
                      )}
                    </div>
                  </div>
                  <Badge tone="slate">{warehouse.products} productos</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="Accesos rápidos">
        <div className="grid gap-3 sm:grid-cols-3">
          <Button variant="secondary" icon="warehouse" onClick={() => onNavigate("almacenes")}>
            Ver inventario
          </Button>
          <Button variant="secondary" icon="settings" onClick={() => onNavigate("admin")}>
            Gestionar productos
          </Button>
          <Button variant="secondary" icon="upload" onClick={() => onNavigate("admin")}>
            Importar CSV
          </Button>
        </div>
      </Card>
    </div>
  );
}
