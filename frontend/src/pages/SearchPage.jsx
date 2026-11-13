import { useEffect, useRef, useState } from "react";
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
  NeedPermission,
  NeedSession,
  ProductTypeBadge,
  Select,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";

const MODES = [
  {
    value: "mejor_precio",
    label: "Mejor precio por almacén",
    hint: "Un resultado por almacén usando el comparador.",
  },
  {
    value: "catalogo",
    label: "Catálogo completo",
    hint: "Todos los productos integrados, con paginación.",
  },
  {
    value: "global",
    label: "Mejor precio global",
    hint: "El producto más barato entre todos los almacenes.",
  },
];

export default function SearchPage({ onNavigate }) {
  const { session, token, can, notify, notifyError } = useApp();
  const [form, setForm] = useState({ modo: "mejor_precio", limit: 20, offset: 0 });
  const [result, setResult] = useState({ loading: false, data: null, error: null });
  const [adding, setAdding] = useState(null);
  const initialSearch = useRef(false);

  const runSearch = async (event) => {
    event?.preventDefault();
    if (!token) return;
    setResult((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.search(token, {
        modo: form.modo,
        limit: Number(form.limit),
        offset: Number(form.offset),
      });
      setResult({ loading: false, data, error: null });
    } catch (error) {
      setResult({ loading: false, data: null, error });
    }
  };

  useEffect(() => {
    if (!token || !can("comparar")) {
      initialSearch.current = false;
      setResult({ loading: false, data: null, error: null });
      return;
    }
    if (initialSearch.current) return;
    initialSearch.current = true;
    const initial = { modo: "mejor_precio", limit: 20, offset: 0 };
    setResult({ loading: true, data: null, error: null });
    api
      .search(token, initial)
      .then(({ data }) => setResult({ loading: false, data, error: null }))
      .catch((error) => setResult({ loading: false, data: null, error }));
  }, [can, token]);

  if (!session) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Buscar productos
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Encuentra y compara precios entre almacenes.
          </p>
        </div>
        <NeedSession />
      </div>
    );
  }

  if (!can("comparar")) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Buscar productos
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Esta función está disponible para clientes.
          </p>
        </div>
        <NeedPermission
          session={session}
          permission="comparar"
          title="Esta función no está disponible para tu cuenta"
        />
      </div>
    );
  }

  const rows = result.data?.resultados || [];

  const addToCart = async (row) => {
    const key = `${row.almacen_id}-${row.producto.producto_id}`;
    setAdding(key);
    try {
      await api.addCartItem(token, row.almacen_id, row.producto.producto_id);
      notify(`"${row.producto.nombre}" agregado desde ${row.almacen}.`, "success", "Carrito");
    } catch (error) {
      notifyError(error);
    } finally {
      setAdding(null);
    }
  };

  const modeInfo = MODES.find((item) => item.value === form.modo);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Buscar productos
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Encuentra productos y compara precios entre almacenes.
          </p>
        </div>
        <Button size="sm" variant="secondary" icon="cart" onClick={() => onNavigate("carrito")}>
          Ver carrito
        </Button>
      </div>

      <Card title="Buscar">
        <form className="grid gap-4 lg:grid-cols-[1.5fr_auto] lg:items-end" onSubmit={runSearch}>
          <Field label="Estrategia de búsqueda" hint={modeInfo?.hint}>
            <Select
              value={form.modo}
              onChange={(event) => setForm({ ...form, modo: event.target.value, offset: 0 })}
            >
              {MODES.map((mode) => (
                <option key={mode.value} value={mode.value}>
                  {mode.label}
                </option>
              ))}
            </Select>
          </Field>
          <Button type="submit" icon="search" loading={result.loading} className="lg:mb-[1px]">
            Buscar
          </Button>
        </form>
      </Card>

      <Card
        title="Resultados"
        description={
          result.data
            ? `Modo ${result.data.modo} · ${rows.length} resultados`
            : "Ejecuta una búsqueda para ver resultados"
        }
        actions={
          result.data && (
            <Badge tone="slate">{result.data.modo}</Badge>
          )
        }
        bodyClassName="p-0 sm:p-0"
      >
        {result.loading ? (
          <div className="flex items-center gap-2 px-5 py-10 text-sm text-slate-500 sm:px-6">
            <Spinner /> Buscando en el comparador…
          </div>
        ) : result.error ? (
          <div className="px-5 py-6 sm:px-6">
            <Alert tone="error" title="Error en la búsqueda">
              {errorText(result.error)}
            </Alert>
          </div>
        ) : rows.length === 0 ? (
          <div className="px-5 py-6 sm:px-6">
            <EmptyState
              icon="search"
              title="Sin resultados"
              description="Prueba otro modo o revisa que el listener haya sincronizado el comparador."
              action={
                <Button
                  size="sm"
                  variant="secondary"
                  icon="shield"
                  onClick={() => onNavigate("admin")}
                >
                  Ver estado del comparador
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead>
                <tr className="bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
                  <th className="px-5 py-3 font-semibold sm:px-6">Almacén</th>
                  <th className="px-4 py-3 font-semibold">Producto</th>
                  <th className="px-4 py-3 font-semibold">Tipo</th>
                  <th className="px-4 py-3 text-right font-semibold">Precio</th>
                  <th className="px-4 py-3 text-right font-semibold">Final</th>
                  <th className="px-5 py-3 text-right font-semibold sm:px-6">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => {
                  const key = `${row.almacen_id}-${row.producto.producto_id}`;
                  return (
                    <tr key={key} className="transition hover:bg-slate-50/70">
                      <td className="px-5 py-3 sm:px-6">
                        <div className="flex items-center gap-2">
                          <span className="grid h-7 w-7 place-items-center rounded-md bg-slate-100 text-slate-500">
                            <Icon name="warehouse" size={13} />
                          </span>
                          <div>
                            <p className="text-sm font-medium text-slate-700">{row.almacen}</p>
                            <p className="font-mono text-[11px] text-slate-400">
                              id {row.almacen_id}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-800">{row.producto.nombre}</p>
                        <p className="text-xs text-slate-400">
                          {row.producto.marca} · {row.producto.categoria}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <ProductTypeBadge tipo={row.producto.tipo} />
                      </td>
                      <td className="px-4 py-3 text-right text-slate-600">
                        <Money value={row.producto.precio} />
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-900">
                        <Money value={row.producto.precio_final} />
                      </td>
                      <td className="px-5 py-3 text-right sm:px-6">
                        <Button
                          size="sm"
                          variant="secondary"
                          icon="cart"
                          loading={adding === key}
                          onClick={() => addToCart(row)}
                        >
                          Agregar
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
