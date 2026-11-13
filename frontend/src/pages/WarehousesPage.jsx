import { useCallback, useEffect, useState } from "react";
import { api, errorText } from "../api";
import Icon from "../components/Icon";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Money,
  ProductTypeBadge,
  Select,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";

export default function WarehousesPage({ onNavigate }) {
  const { session, token, notify, notifyError } = useApp();
  const [warehouses, setWarehouses] = useState({ loading: true, items: [], error: null });
  const [selectedId, setSelectedId] = useState(null);
  const [limit, setLimit] = useState(20);
  const [offset, setOffset] = useState(0);
  const [products, setProducts] = useState({
    loading: false,
    items: [],
    total: 0,
    error: null,
  });
  const [addingId, setAddingId] = useState(null);

  const loadWarehouses = useCallback(async () => {
    setWarehouses((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.listWarehouses();
      const items = data || [];
      setWarehouses({ loading: false, items, error: null });
      setSelectedId((current) =>
        current != null && items.some((item) => item.id === current)
          ? current
          : (items[0]?.id ?? null),
      );
    } catch (error) {
      setWarehouses({ loading: false, items: [], error });
    }
  }, []);

  useEffect(() => {
    loadWarehouses();
  }, [loadWarehouses]);

  const loadProducts = useCallback(async () => {
    if (selectedId == null) return;
    setProducts((current) => ({ ...current, loading: true, error: null }));
    try {
      const result = await api.listProducts(selectedId, { limit, offset });
      const total = Number(result.headers.get("X-Total-Count") || result.data?.length || 0);
      setProducts({ loading: false, items: result.data || [], total, error: null });
    } catch (error) {
      setProducts({ loading: false, items: [], total: 0, error });
    }
  }, [limit, offset, selectedId]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  const selectedWarehouse = warehouses.items.find((item) => item.id === selectedId);
  const totalPages = Math.max(1, Math.ceil(products.total / limit));
  const currentPage = Math.floor(offset / limit) + 1;

  const addToCart = async (product) => {
    if (!session) {
      notify("Inicia una sesión para agregar productos al carrito.", "info", "Sesión requerida");
      onNavigate("sesion");
      return;
    }
    setAddingId(product.producto_id);
    try {
      await api.addCartItem(token, selectedId, product.producto_id);
      notify(`"${product.nombre}" se agregó al carrito.`, "success", "Carrito");
    } catch (error) {
      notifyError(error);
    } finally {
      setAddingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Almacenes e inventarios
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Consulta <span className="font-mono text-xs">GET /warehouses</span> y el catálogo
            paginado de cada almacén.
          </p>
        </div>
        <Button variant="secondary" icon="refresh" onClick={loadWarehouses} loading={warehouses.loading}>
          Recargar almacenes
        </Button>
      </div>

      {warehouses.error && (
        <Alert tone="error" title="No se pudieron cargar los almacenes">
          {errorText(warehouses.error)}
        </Alert>
      )}

      {warehouses.loading ? (
        <Card>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner /> Consultando almacenes…
          </div>
        </Card>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {warehouses.items.map((warehouse) => {
              const active = warehouse.id === selectedId;
              return (
                <button
                  key={warehouse.id}
                  onClick={() => {
                    setSelectedId(warehouse.id);
                    setOffset(0);
                  }}
                  className={`flex items-center justify-between gap-3 rounded-xl border p-4 text-left transition ${
                    active
                      ? "border-slate-900 bg-white ring-1 ring-slate-900"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span
                      className={`grid h-9 w-9 shrink-0 place-items-center rounded-md ${
                        active ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      <Icon name="warehouse" size={16} />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-800">
                        {warehouse.name}
                      </p>
                      <p className="font-mono text-xs text-slate-400">id: {warehouse.id}</p>
                    </div>
                  </div>
                  <Badge tone={active ? "dark" : "slate"}>{warehouse.products}</Badge>
                </button>
              );
            })}
          </div>

          <Card
            title={selectedWarehouse ? `Inventario · ${selectedWarehouse.name}` : "Inventario"}
            description={
              selectedWarehouse
                ? `GET /warehouses/${selectedWarehouse.id}/products · página ${currentPage} de ${totalPages}`
                : "Selecciona un almacén"
            }
            actions={
              <Button size="sm" variant="secondary" icon="refresh" onClick={loadProducts} loading={products.loading}>
                Actualizar
              </Button>
            }
            bodyClassName="p-0 sm:p-0"
          >
            <div className="flex flex-wrap items-end gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
              <Field label="Productos por página" className="w-32">
                <Select
                  value={limit}
                  onChange={(event) => {
                    setLimit(Number(event.target.value));
                    setOffset(0);
                  }}
                >
                  {[10, 20, 50, 100].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Offset" className="w-28">
                <Input
                  type="number"
                  min={0}
                  value={offset}
                  onChange={(event) => setOffset(Math.max(0, Number(event.target.value) || 0))}
                />
              </Field>
              <div className="mb-1 flex-1 text-xs text-slate-400">
                {products.total > 0
                  ? `Mostrando ${offset + 1}–${Math.min(offset + limit, products.total)} de ${products.total}`
                  : "Sin resultados"}
              </div>
            </div>

            {products.loading ? (
              <div className="flex items-center gap-2 px-5 py-10 text-sm text-slate-500 sm:px-6">
                <Spinner /> Cargando productos…
              </div>
            ) : products.error ? (
              <div className="px-5 py-6 sm:px-6">
                <Alert tone="error" title="No se pudo consultar el inventario">
                  {errorText(products.error)}
                </Alert>
              </div>
            ) : products.items.length === 0 ? (
              <div className="px-5 py-6 sm:px-6">
                <EmptyState
                  icon="package"
                  title="Este almacén no tiene productos"
                  description="Importa un CSV o crea productos desde Administración."
                  action={
                    <Button size="sm" variant="secondary" icon="shield" onClick={() => onNavigate("admin")}>
                      Ir a administración
                    </Button>
                  }
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100 text-sm">
                  <thead>
                    <tr className="bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
                      <th className="px-5 py-3 font-semibold sm:px-6">Producto</th>
                      <th className="px-4 py-3 font-semibold">Categoría</th>
                      <th className="px-4 py-3 font-semibold">Tipo</th>
                      <th className="px-4 py-3 text-right font-semibold">Precio</th>
                      <th className="px-4 py-3 text-right font-semibold">Final</th>
                      <th className="px-5 py-3 text-right font-semibold sm:px-6">Acción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {products.items.map((product) => (
                      <tr key={product.producto_id} className="transition hover:bg-slate-50/70">
                        <td className="px-5 py-3 sm:px-6">
                          <p className="font-medium text-slate-800">{product.nombre}</p>
                          <p className="text-xs text-slate-400">
                            {product.marca} · <span className="font-mono">{product.producto_id}</span>
                          </p>
                        </td>
                        <td className="px-4 py-3 text-slate-600">{product.categoria}</td>
                        <td className="px-4 py-3">
                          <ProductTypeBadge tipo={product.tipo} />
                          {product.tipo === "fisico" && product.costo_envio != null && (
                            <p className="mt-1 text-[11px] text-slate-400">
                              envío <Money value={product.costo_envio} />
                            </p>
                          )}
                          {product.tipo === "suscripcion" && product.meses != null && (
                            <p className="mt-1 text-[11px] text-slate-400">{product.meses} meses</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-600">
                          <Money value={product.precio} />
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-slate-900">
                          <Money value={product.precio_final} />
                        </td>
                        <td className="px-5 py-3 text-right sm:px-6">
                          <Button
                            size="sm"
                            variant="secondary"
                            icon="cart"
                            loading={addingId === product.producto_id}
                            onClick={() => addToCart(product)}
                          >
                            Agregar
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-5 py-3 sm:px-6">
              <span className="text-xs text-slate-400">
                {products.total} productos · limit {limit} · offset {offset}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={offset === 0 || products.loading}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  Anterior
                </Button>
                <span className="min-w-16 text-center text-xs font-semibold text-slate-500">
                  {currentPage} / {totalPages}
                </span>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={offset + limit >= products.total || products.loading}
                  onClick={() => setOffset(offset + limit)}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
