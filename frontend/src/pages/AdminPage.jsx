import { useCallback, useEffect, useRef, useState } from "react";
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
  Select,
  Spinner,
  Textarea,
} from "../components/ui";
import { useApp } from "../context/AppContext";

const EMPTY_PRODUCT = {
  nombre: "",
  precio: "",
  marca: "Generica",
  categoria: "General",
  tipo: "normal",
  costo_envio: "",
  meses: "",
};

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

export default function AdminPage({ onNavigate }) {
  const { session, token, can, isProvider, notify, notifyError } = useApp();
  const puedeInventario = Boolean(session && can("ver_inventario"));
  const puedeGestionar = Boolean(session && can("gestionar_inventario"));
  const puedePrecio = Boolean(session && can("editar_precio"));
  const puedeCsv = Boolean(session && can("importar_csv"));
  const puedeComparador = Boolean(session && can("gestionar_comparador"));
  const [warehouses, setWarehouses] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [loadingWarehouses, setLoadingWarehouses] = useState(false);
  const [product, setProduct] = useState(EMPTY_PRODUCT);
  const [creating, setCreating] = useState(false);
  const [priceForm, setPriceForm] = useState({ producto_id: "", precio: "" });
  const [updatingPrice, setUpdatingPrice] = useState(false);
  const [deleteForm, setDeleteForm] = useState({ producto_id: "" });
  const [deleting, setDeleting] = useState(false);
  const [csv, setCsv] = useState({ contenido: "", filename: "" });
  const [importing, setImporting] = useState(false);
  const [csvResult, setCsvResult] = useState(null);
  const [comparador, setComparador] = useState({ loading: false, data: null, error: null });
  const [syncing, setSyncing] = useState(null);
  const fileInput = useRef(null);

  const loadWarehouses = useCallback(async () => {
    setLoadingWarehouses(true);
    try {
      const { data } = await api.listWarehouses();
      const items = data || [];
      setWarehouses(items);
      setSelectedId((current) =>
        current && items.some((item) => String(item.id) === String(current))
          ? current
          : items[0]
            ? String(items[0].id)
            : "",
      );
    } catch (error) {
      notifyError(error);
    } finally {
      setLoadingWarehouses(false);
    }
  }, [notifyError]);

  const loadComparador = useCallback(async () => {
    if (!token) return;
    setComparador((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.comparadorStatus(token);
      setComparador({ loading: false, data, error: null });
    } catch (error) {
      setComparador({ loading: false, data: null, error });
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;
    if (puedeInventario) loadWarehouses();
    if (puedeComparador) loadComparador();
  }, [puedeComparador, puedeInventario, loadComparador, loadWarehouses, token]);

  useEffect(() => {
    if (isProvider && session?.almacen_id != null) {
      setSelectedId(String(session.almacen_id));
    }
  }, [isProvider, session?.almacen_id]);

  if (!session) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Administración</h2>
          <p className="mt-1 text-sm text-slate-500">
            Inventarios, precios, CSV y comparador.
          </p>
        </div>
        <NeedSession onNavigate={onNavigate} title="Necesitas una sesión de proveedor o administrador" />
      </div>
    );
  }

  if (!puedeInventario) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Administración</h2>
          <p className="mt-1 text-sm text-slate-500">
            Inventarios, precios, CSV y comparador.
          </p>
        </div>
        <NeedPermission
          onNavigate={onNavigate}
          session={session}
          permission="ver_inventario"
          title="Esta sección requiere un rol con inventario"
        />
      </div>
    );
  }

  const create = async (event) => {
    event.preventDefault();
    if (!selectedId) {
      notify("Selecciona un almacén de trabajo.", "info", "Datos incompletos");
      return;
    }
    if (!product.nombre.trim() || product.precio === "") {
      notify("El nombre y el precio son obligatorios.", "info", "Datos incompletos");
      return;
    }
    const payload = {
      nombre: product.nombre.trim(),
      precio: Number(product.precio),
      marca: product.marca.trim() || "Generica",
      categoria: product.categoria.trim() || "General",
      tipo: product.tipo,
    };
    if (product.tipo === "fisico" && product.costo_envio !== "") {
      payload.costo_envio = Number(product.costo_envio);
    }
    if (product.tipo === "suscripcion" && product.meses !== "") {
      payload.meses = Number(product.meses);
    }
    setCreating(true);
    try {
      await api.createProduct(token, selectedId, payload);
      notify(`Producto "${payload.nombre}" creado en el almacén ${selectedId}.`, "success", "Alta");
      setProduct(EMPTY_PRODUCT);
      loadWarehouses();
    } catch (error) {
      notifyError(error);
    } finally {
      setCreating(false);
    }
  };

  const updatePrice = async (event) => {
    event.preventDefault();
    if (!selectedId || !priceForm.producto_id.trim() || priceForm.precio === "") {
      notify("Completa almacén, producto_id y precio.", "info", "Datos incompletos");
      return;
    }
    setUpdatingPrice(true);
    try {
      await api.updatePrice(token, selectedId, priceForm.producto_id.trim(), priceForm.precio);
      notify(
        `Precio de ${priceForm.producto_id.trim()} actualizado a ${priceForm.precio}.`,
        "success",
        "Edición de precio",
      );
      setPriceForm({ producto_id: "", precio: "" });
    } catch (error) {
      notifyError(error);
    } finally {
      setUpdatingPrice(false);
    }
  };

  const deleteProduct = async (event) => {
    event.preventDefault();
    const productId = deleteForm.producto_id.trim();
    if (!selectedId || !productId) {
      notify("Indica el almacén y el producto_id.", "info", "Datos incompletos");
      return;
    }
    if (!window.confirm(`¿Eliminar el producto ${productId} del almacén ${selectedId}?`)) return;
    setDeleting(true);
    try {
      await api.deleteProduct(token, selectedId, productId);
      notify(`Producto ${productId} eliminado.`, "success", "Baja de producto");
      setDeleteForm({ producto_id: "" });
      loadWarehouses();
    } catch (error) {
      notifyError(error);
    } finally {
      setDeleting(false);
    }
  };

  const loadExampleCsv = () => {
    const almacen = selectedId || "1";
    const sample = [
      "almacen,nombre,marca,categoria,tipo,precio,extra",
      `${almacen},Leche,La Serenisima,Lacteos,normal,1200,`,
      `${almacen},Mouse,Logitech,Tecnologia,fisico,15000,500`,
      `${almacen},Netflix,Netflix,Streaming,suscripcion,3500,12`,
    ].join("\n");
    setCsv({ contenido: sample, filename: "" });
    if (fileInput.current) fileInput.current.value = "";
  };

  const importCsv = async (event) => {
    event.preventDefault();
    if (!csv.contenido.trim()) {
      notify("Pega o carga un CSV antes de importar.", "info", "Datos incompletos");
      return;
    }
    setImporting(true);
    setCsvResult(null);
    try {
      const { data } = await api.importCsv(token, csv.contenido);
      setCsvResult(data);
      notify(
        `CSV importado: ${data.importados} aceptados, ${data.rechazados} rechazados.`,
        data.rechazados > 0 ? "info" : "success",
        "Importación CSV",
      );
      loadWarehouses();
    } catch (error) {
      notifyError(error);
    } finally {
      setImporting(false);
    }
  };

  const runComparadorAction = async (action) => {
    setSyncing(action);
    try {
      if (action === "reconciliar") {
        await api.reconcileComparador(token);
        notify("Reconciliación del comparador solicitada.", "success", "Comparador");
      } else {
        await api.reload(token);
        notify("Recarga de inventarios solicitada.", "success", "Comparador");
      }
      await loadComparador();
    } catch (error) {
      notifyError(error);
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Administración</h2>
          <p className="mt-1 text-sm text-slate-500">
            {isProvider
              ? "Alta, precios, bajas e importación CSV limitados a tu almacén asignado."
              : "Alta, precios, bajas, CSV y estado del comparador en todos los almacenes."}
          </p>
        </div>
        <Badge tone="dark">{isProvider ? `PROVEEDOR · ALMACÉN ${session.almacen_id ?? "—"}` : "ADMIN"}</Badge>
      </div>

      <Card
        title="Almacén de trabajo"
        description={
          isProvider
            ? "Fijado por el administrador: no puedes operar otro almacén."
            : "Se usa en las operaciones de alta, edición y baja."
        }
        actions={
          <Button size="sm" variant="secondary" icon="refresh" onClick={loadWarehouses} loading={loadingWarehouses}>
            Recargar
          </Button>
        }
      >
        <div className="flex flex-wrap items-end gap-4">
          <Field label="Almacén" className="w-full sm:w-72">
            <Select
              value={selectedId}
              onChange={(event) => setSelectedId(event.target.value)}
              disabled={loadingWarehouses || isProvider}
            >
              {warehouses.length === 0 && <option value="">Sin almacenes</option>}
              {(isProvider
                ? warehouses.filter(
                    (warehouse) => String(warehouse.id) === String(session.almacen_id),
                  )
                : warehouses
              ).map((warehouse) => (
                <option key={warehouse.id} value={warehouse.id}>
                  {warehouse.name} (ID {warehouse.id}) · {warehouse.products} productos
                </option>
              ))}
            </Select>
          </Field>
          <div className="mb-1.5 flex items-center gap-2 text-xs text-slate-400">
            <Icon name="database" size={14} />
            <span className="font-mono">warehouse_{selectedId || "?"}</span>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        {puedeGestionar && (
        <Card
          title="Alta de producto"
          description="POST /admin/warehouses/{id}/products"
          actions={<Badge tone="slate">create</Badge>}
        >
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={create}>
            <Field label="Nombre" className="sm:col-span-2">
              <Input
                value={product.nombre}
                onChange={(event) => setProduct({ ...product, nombre: event.target.value })}
                placeholder="Leche"
                maxLength={200}
                required
              />
            </Field>
            <Field label="Precio">
              <Input
                type="number"
                min={0}
                step="0.01"
                value={product.precio}
                onChange={(event) => setProduct({ ...product, precio: event.target.value })}
                placeholder="1200"
                required
              />
            </Field>
            <Field label="Tipo">
              <Select
                value={product.tipo}
                onChange={(event) =>
                  setProduct({
                    ...product,
                    tipo: event.target.value,
                    costo_envio: "",
                    meses: "",
                  })
                }
              >
                <option value="normal">normal</option>
                <option value="fisico">fisico</option>
                <option value="digital">digital</option>
                <option value="suscripcion">suscripcion</option>
              </Select>
            </Field>
            <Field label="Marca">
              <Input
                value={product.marca}
                onChange={(event) => setProduct({ ...product, marca: event.target.value })}
                maxLength={120}
              />
            </Field>
            <Field label="Categoría">
              <Input
                value={product.categoria}
                onChange={(event) => setProduct({ ...product, categoria: event.target.value })}
                maxLength={120}
              />
            </Field>
            {product.tipo === "fisico" && (
              <Field label="Costo de envío" hint="Solo productos físicos." className="sm:col-span-2">
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  value={product.costo_envio}
                  onChange={(event) => setProduct({ ...product, costo_envio: event.target.value })}
                  placeholder="500"
                />
              </Field>
            )}
            {product.tipo === "suscripcion" && (
              <Field label="Meses" hint="Solo suscripciones." className="sm:col-span-2">
                <Input
                  type="number"
                  min={1}
                  value={product.meses}
                  onChange={(event) => setProduct({ ...product, meses: event.target.value })}
                  placeholder="12"
                />
              </Field>
            )}
            <div className="sm:col-span-2">
              <Button type="submit" icon="plus" loading={creating} className="w-full">
                Crear producto
              </Button>
            </div>
          </form>
        </Card>
        )}

        <div className="space-y-6">
          {puedePrecio && (
          <Card title="Editar precio" description="PATCH /admin/warehouses/{id}/products">
            <form className="space-y-4" onSubmit={updatePrice}>
              <Field label="producto_id" hint="Identificador del producto en el almacén.">
                <Input
                  value={priceForm.producto_id}
                  onChange={(event) => setPriceForm({ ...priceForm, producto_id: event.target.value })}
                  placeholder="p-001"
                  required
                />
              </Field>
              <Field label="Nuevo precio">
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  value={priceForm.precio}
                  onChange={(event) => setPriceForm({ ...priceForm, precio: event.target.value })}
                  placeholder="1500"
                  required
                />
              </Field>
              <Button type="submit" icon="settings" loading={updatingPrice} className="w-full">
                Actualizar precio
              </Button>
            </form>
          </Card>
          )}

          {puedeGestionar && (
          <Card title="Eliminar producto" description="DELETE /admin/warehouses/{id}/products/{producto_id}">
            <form className="space-y-4" onSubmit={deleteProduct}>
              <Field label="producto_id">
                <Input
                  value={deleteForm.producto_id}
                  onChange={(event) => setDeleteForm({ producto_id: event.target.value })}
                  placeholder="p-001"
                  required
                />
              </Field>
              <Button type="submit" variant="dangerSoft" icon="trash" loading={deleting} className="w-full">
                Eliminar producto
              </Button>
            </form>
          </Card>
          )}
        </div>
      </div>

      {puedeCsv && (
      <Card
        title="Importar inventario CSV"
        description="POST /admin/csv · cabecera: almacen,nombre,marca,categoria,tipo,precio,extra"
        actions={
          <Button size="sm" variant="secondary" icon="file" onClick={loadExampleCsv}>
            Usar ejemplo
          </Button>
        }
      >
        <form className="space-y-4" onSubmit={importCsv}>
          <div className="flex flex-wrap items-center gap-3">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-2.5 text-xs font-medium text-slate-600 transition hover:border-slate-400 hover:bg-slate-100">
              <Icon name="file" size={15} />
              Elegir archivo .csv
              <input
                ref={fileInput}
                type="file"
                accept=".csv,text/csv"
                className="sr-only"
                onChange={async (event) => {
                  const file = event.target.files?.[0];
                  if (!file) return;
                  try {
                    const contenido = await file.text();
                    setCsv({ contenido, filename: file.name });
                    notify(`${file.name} cargado en el editor.`, "success", "Archivo");
                  } catch {
                    notify("No se pudo leer el archivo.", "error");
                  }
                }}
              />
            </label>
            {csv.filename && (
              <Badge tone="slate">
                <Icon name="file" size={11} /> {csv.filename}
              </Badge>
            )}
            <span className="text-xs text-slate-400">
              {csv.contenido.length.toLocaleString("es-CO")} caracteres
            </span>
          </div>
          <Field label="Contenido CSV">
            <Textarea
              rows={7}
              value={csv.contenido}
              onChange={(event) => setCsv({ ...csv, contenido: event.target.value, filename: "" })}
              placeholder={"almacen,nombre,marca,categoria,tipo,precio,extra\n1,Leche,La Serenisima,Lacteos,normal,1200,"}
              spellCheck={false}
            />
          </Field>
          <Button type="submit" icon="download" loading={importing}>
            Importar CSV
          </Button>
        </form>

        {csvResult && (
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap gap-2">
              <Badge tone="slate">{csvResult.importados} importados</Badge>
              <Badge tone={csvResult.rechazados > 0 ? "rose" : "slate"}>
                {csvResult.rechazados} rechazados
              </Badge>
            </div>
            {csvResult.errores?.length > 0 ? (
              <Alert tone="warning" title="Filas rechazadas">
                <ul className="list-inside list-disc space-y-0.5">
                  {csvResult.errores.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </Alert>
            ) : (
              <Alert tone="success" title="Importación sin errores">
                Todas las filas fueron aceptadas.
              </Alert>
            )}
            <JsonBlock data={csvResult} label="POST /admin/csv · respuesta" />
          </div>
        )}
      </Card>
      )}

      {puedeComparador && (
      <Card
        title="Comparador"
        description="Estado de la proyección integrada y reconciliación."
        actions={
          <>
            <Button size="sm" variant="secondary" icon="refresh" onClick={loadComparador} loading={comparador.loading}>
              Estado
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon="settings"
              loading={syncing === "reconciliar"}
              onClick={() => runComparadorAction("reconciliar")}
            >
              Reconciliar
            </Button>
            <Button
              size="sm"
              variant="dark"
              icon="refresh"
              loading={syncing === "reload"}
              onClick={() => runComparadorAction("reload")}
            >
              Reload
            </Button>
          </>
        }
      >
        {comparador.loading && !comparador.data ? (
          <div className="flex items-center gap-2 py-4 text-sm text-slate-500">
            <Spinner /> Consultando estado del comparador…
          </div>
        ) : comparador.error ? (
          <Alert tone="error" title="No se pudo consultar el comparador">
            {errorText(comparador.error)}
          </Alert>
        ) : comparador.data ? (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {[
                ["Estado", comparador.data.estado],
                ["Documentos", comparador.data.documentos],
                ["Última sincronización", formatDate(comparador.data.ultima_sincronizacion)],
                ["Último evento", comparador.data.ultimo_evento || "—"],
                ["Resume token", comparador.data.tiene_resume_token ? "Sí" : "No"],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    {label}
                  </p>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-800" title={String(value)}>
                    {value}
                  </p>
                </div>
              ))}
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">
              <Icon name="database" size={15} className="mt-0.5 shrink-0 text-slate-400" />
              <p>
                La sincronización es eventual. Tras crear o editar un producto, el listener
                actualiza el comparador. Si no aparece en búsquedas, usa{" "}
                <span className="font-semibold">Reconciliar</span> o revisa el servicio{" "}
                <span className="font-mono">listener</span>.
              </p>
            </div>
            <JsonBlock data={comparador.data} label="GET /admin/comparador/status · respuesta" />
          </div>
        ) : (
          <EmptyState icon="database" title="Sin datos del comparador" />
        )}
      </Card>
      )}
    </div>
  );
}
