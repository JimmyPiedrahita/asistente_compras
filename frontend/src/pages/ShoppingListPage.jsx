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
  JsonBlock,
  NeedPermission,
  NeedSession,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";

export default function ShoppingListPage({ onNavigate }) {
  const { session, token, can, notify, notifyError } = useApp();
  const [state, setState] = useState({ loading: false, lista: [], error: null });
  const [nombre, setNombre] = useState("");
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async () => {
    if (!token || !can("crear_lista")) return;
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.getShoppingList(token);
      setState({ loading: false, lista: data?.lista || [], error: null });
    } catch (error) {
      setState({ loading: false, lista: [], error });
    }
  }, [can, token]);

  useEffect(() => {
    load();
  }, [load]);

  if (!session) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Lista de compras
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Productos pendientes del cliente en una lista sin duplicados.
          </p>
        </div>
        <NeedSession onNavigate={onNavigate} />
      </div>
    );
  }

  if (!can("crear_lista")) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Lista de compras
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Solo el rol CLIENTE (y ADMIN) gestiona una lista personal.
          </p>
        </div>
        <NeedPermission
          onNavigate={onNavigate}
          session={session}
          permission="crear_lista"
          title="Tu rol no tiene lista de compras"
        />
      </div>
    );
  }

  const add = async (event) => {
    event.preventDefault();
    const value = nombre.trim();
    if (!value) {
      notify("Escribe el nombre del producto.", "info", "Datos incompletos");
      return;
    }
    setAdding(true);
    try {
      const { data } = await api.addShoppingListItem(token, value);
      setState({ loading: false, lista: data?.lista || [], error: null });
      setNombre("");
      notify(`"${value}" se agregó a la lista.`, "success", "Lista de compras");
    } catch (error) {
      notifyError(error);
    } finally {
      setAdding(false);
    }
  };

  const remove = async (item) => {
    setRemoving(item);
    try {
      const { data } = await api.removeShoppingListItem(token, item);
      setState((current) => ({ ...current, lista: data?.lista || [] }));
      notify(`"${item}" se eliminó de la lista.`, "success", "Lista de compras");
    } catch (error) {
      notifyError(error);
    } finally {
      setRemoving(null);
    }
  };

  const exportCsv = async () => {
    setExporting(true);
    try {
      const filename = await api.exportShoppingList(token);
      notify(`Descargado ${filename}`, "success", "Exportación");
    } catch (error) {
      notifyError(error);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Lista de compras
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            <span className="font-mono text-xs">GET · POST · DELETE /sessions/{"{token}"}/shopping-list</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" icon="refresh" onClick={load} loading={state.loading}>
            Actualizar
          </Button>
          <Button size="sm" variant="secondary" icon="download" onClick={exportCsv} loading={exporting}>
            Exportar CSV
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card
          title="Productos en la lista"
          description={`${state.lista.length} elemento${state.lista.length === 1 ? "" : "s"}`}
          actions={<Badge tone="slate">{state.lista.length}</Badge>}
        >
          {state.loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
              <Spinner /> Cargando lista…
            </div>
          ) : state.error ? (
            <Alert tone="error" title="No se pudo cargar la lista">
              {errorText(state.error)}
            </Alert>
          ) : state.lista.length === 0 ? (
            <EmptyState
              icon="list"
              title="La lista está vacía"
              description="Agrega el primer producto desde el formulario o desde los resultados de búsqueda."
              action={
                <Button size="sm" variant="secondary" icon="search" onClick={() => onNavigate("busqueda")}>
                  Buscar productos
                </Button>
              }
            />
          ) : (
            <ul className="divide-y divide-slate-100">
              {state.lista.map((item, index) => (
                <li key={item} className="flex items-center justify-between gap-3 py-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-slate-100 font-mono text-xs font-semibold text-slate-500">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-800">{item}</p>
                      <p className="text-xs text-slate-400">Pendiente de compra</p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="dangerSoft"
                    icon="trash"
                    loading={removing === item}
                    onClick={() => remove(item)}
                  >
                    <span className="hidden sm:inline">Eliminar</span>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-6">
          <Card title="Agregar producto" description="POST /shopping-list">
            <form className="space-y-4" onSubmit={add}>
              <Field label="Nombre" hint="El backend rechaza duplicados con 409.">
                <Input
                  value={nombre}
                  onChange={(event) => setNombre(event.target.value)}
                  placeholder="Leche"
                  maxLength={200}
                  autoComplete="off"
                />
              </Field>
              <Button type="submit" icon="plus" loading={adding} className="w-full">
                Agregar a la lista
              </Button>
            </form>
          </Card>

          <Card title="Atajos">
            <div className="space-y-2">
              <button
                onClick={() => onNavigate("busqueda")}
                className="flex w-full items-center justify-between rounded-lg border border-slate-200 px-3.5 py-3 text-left text-sm transition hover:border-slate-300 hover:bg-slate-50"
              >
                <span className="flex items-center gap-2 text-slate-600">
                  <Icon name="search" size={15} className="text-slate-400" /> Buscar y agregar al carrito
                </span>
                <Icon name="arrow" size={14} className="text-slate-400" />
              </button>
              <button
                onClick={() => onNavigate("exportar")}
                className="flex w-full items-center justify-between rounded-lg border border-slate-200 px-3.5 py-3 text-left text-sm transition hover:border-slate-300 hover:bg-slate-50"
              >
                <span className="flex items-center gap-2 text-slate-600">
                  <Icon name="download" size={15} className="text-slate-400" /> Todas las exportaciones
                </span>
                <Icon name="arrow" size={14} className="text-slate-400" />
              </button>
            </div>
          </Card>
        </div>
      </div>

      <JsonBlock data={{ lista: state.lista }} label="GET /shopping-list · respuesta" />
    </div>
  );
}
