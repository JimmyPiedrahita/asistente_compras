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
  Money,
  NeedPermission,
  NeedSession,
  ProductTypeBadge,
  Select,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";

const DISCOUNTS = [
  { value: "sin", label: "Sin descuento" },
  { value: "porcentaje", label: "Porcentaje (%)" },
  { value: "fijo", label: "Monto fijo" },
];

export default function CartPage({ onNavigate }) {
  const { session, token, can, notify, notifyError } = useApp();
  const [cart, setCart] = useState({ loading: false, data: null, error: null });
  const [removing, setRemoving] = useState(null);
  const [clearing, setClearing] = useState(false);
  const [discount, setDiscount] = useState({ tipo: "porcentaje", valor: 10 });
  const [applying, setApplying] = useState(false);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async () => {
    if (!token || !can("agregar_producto")) return;
    setCart((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.getCart(token);
      setCart({ loading: false, data, error: null });
    } catch (error) {
      setCart({ loading: false, data: null, error });
    }
  }, [can, token]);

  useEffect(() => {
    load();
  }, [load]);

  if (!session) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Carrito</h2>
          <p className="mt-1 text-sm text-slate-500">
            Ítems, subtotal, descuento y total de la sesión.
          </p>
        </div>
        <NeedSession onNavigate={onNavigate} />
      </div>
    );
  }

  if (!can("agregar_producto")) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Carrito</h2>
          <p className="mt-1 text-sm text-slate-500">
            El carrito pertenece al flujo de compra del cliente.
          </p>
        </div>
        <NeedPermission
          onNavigate={onNavigate}
          session={session}
          permission="agregar_producto"
          title="Tu rol no usa carrito"
        />
      </div>
    );
  }

  const productos = cart.data?.productos || [];

  const remove = async (index) => {
    setRemoving(index);
    try {
      const { data } = await api.removeCartItem(token, index);
      setCart({ loading: false, data, error: null });
      notify("Ítem eliminado del carrito.", "success", "Carrito");
    } catch (error) {
      notifyError(error);
    } finally {
      setRemoving(null);
    }
  };

  const clear = async () => {
    if (!window.confirm("¿Vaciar todos los productos del carrito?")) return;
    setClearing(true);
    try {
      const { data } = await api.clearCart(token);
      setCart({ loading: false, data, error: null });
      notify("Carrito vaciado.", "success", "Carrito");
    } catch (error) {
      notifyError(error);
    } finally {
      setClearing(false);
    }
  };

  const apply = async (event) => {
    event.preventDefault();
    if (discount.tipo !== "sin" && (discount.valor === "" || Number(discount.valor) < 0)) {
      notify("Indica un valor de descuento válido.", "info", "Datos incompletos");
      return;
    }
    setApplying(true);
    try {
      const { data } = await api.applyDiscount(token, discount.tipo, discount.valor);
      setCart({ loading: false, data, error: null });
      notify(
        discount.tipo === "sin" ? "Descuento eliminado." : "Descuento aplicado al carrito.",
        "success",
        "Carrito",
      );
    } catch (error) {
      notifyError(error);
    } finally {
      setApplying(false);
    }
  };

  const exportCsv = async () => {
    setExporting(true);
    try {
      const filename = await api.exportCart(token);
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
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Carrito</h2>
          <p className="mt-1 text-sm text-slate-500">
            <span className="font-mono text-xs">
              GET · POST · DELETE /sessions/{"{token}"}/cart
            </span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" icon="search" onClick={() => onNavigate("busqueda")}>
            Buscar productos
          </Button>
          <Button size="sm" variant="secondary" icon="download" onClick={exportCsv} loading={exporting}>
            Exportar CSV
          </Button>
          <Button size="sm" variant="dangerSoft" icon="trash" onClick={clear} loading={clearing} disabled={productos.length === 0}>
            Vaciar
          </Button>
        </div>
      </div>

      {cart.error && (
        <Alert tone="error" title="No se pudo obtener el carrito">
          {errorText(cart.error)}
        </Alert>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Card
          title="Ítems del carrito"
          description={cart.data ? `${productos.length} producto(s)` : "GET /cart"}
          bodyClassName="p-0 sm:p-0"
          actions={
            <Button size="sm" variant="secondary" icon="refresh" onClick={load} loading={cart.loading}>
              Actualizar
            </Button>
          }
        >
          {cart.loading && !cart.data ? (
            <div className="flex items-center gap-2 px-5 py-10 text-sm text-slate-500 sm:px-6">
              <Spinner /> Cargando carrito…
            </div>
          ) : productos.length === 0 ? (
            <div className="px-5 py-6 sm:px-6">
              <EmptyState
                icon="cart"
                title="El carrito está vacío"
                description="Agrega productos desde el inventario o desde los resultados de búsqueda."
                action={
                  <Button size="sm" icon="search" onClick={() => onNavigate("busqueda")}>
                    Buscar productos
                  </Button>
                }
              />
            </div>
          ) : (
            <>
              <ul className="divide-y divide-slate-100">
                {productos.map((product, index) => (
                  <li key={`${product.producto_id}-${index}`} className="flex items-center gap-3 px-5 py-4 sm:px-6">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-100 font-mono text-xs font-semibold text-slate-500">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-semibold text-slate-800">{product.nombre}</p>
                        <ProductTypeBadge tipo={product.tipo} />
                      </div>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {product.marca} · {product.categoria}
                        {product.costo_envio != null ? ` · envío ${product.costo_envio}` : ""}
                        {product.meses != null ? ` · ${product.meses} meses` : ""}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-slate-900">
                        <Money value={product.precio_final} />
                      </p>
                      <p className="text-[11px] text-slate-400">
                        base <Money value={product.precio} />
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="dangerSoft"
                      icon="trash"
                      loading={removing === index}
                      onClick={() => remove(index)}
                    >
                      <span className="sr-only sm:not-sr-only">Quitar</span>
                    </Button>
                  </li>
                ))}
              </ul>
              <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-xs text-slate-400 sm:px-6">
                <span className="inline-flex items-center gap-1.5">
                  <Icon name="cart" size={13} /> DELETE /cart/items/{"{indice}"} usa el índice mostrado
                </span>
                <Badge tone="slate">{productos.length} ítems</Badge>
              </div>
            </>
          )}
        </Card>

        <div className="space-y-6">
          <Card title="Resumen" description="Calculado por el backend.">
            {cart.data ? (
              <div className="space-y-2.5 text-sm">
                <div className="flex justify-between text-slate-500">
                  <span>Subtotal</span>
                  <span className="font-medium text-slate-700">
                    <Money value={cart.data.subtotal} />
                  </span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Descuento</span>
                  <span className="font-medium text-slate-700">{cart.data.descuento || "sin"}</span>
                </div>
                <div className="flex justify-between border-t border-dashed border-slate-200 pt-3 text-base font-semibold text-slate-900">
                  <span>Total</span>
                  <Money value={cart.data.total} />
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-400">Sin datos todavía.</p>
            )}
          </Card>

          <Card title="Descuento" description="POST /cart/discount">
            <form className="space-y-4" onSubmit={apply}>
              <Field label="Tipo">
                <Select
                  value={discount.tipo}
                  onChange={(event) => setDiscount({ ...discount, tipo: event.target.value })}
                >
                  {DISCOUNTS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </Select>
              </Field>
              {discount.tipo !== "sin" && (
                <Field
                  label={discount.tipo === "porcentaje" ? "Porcentaje" : "Monto fijo"}
                  hint={
                    discount.tipo === "porcentaje"
                      ? "Ejemplo: 15 aplica 15 %."
                      : "Valor absoluto en la moneda del backend."
                  }
                >
                  <Input
                    type="number"
                    min={0}
                    step="0.01"
                    value={discount.valor}
                    onChange={(event) => setDiscount({ ...discount, valor: event.target.value })}
                  />
                </Field>
              )}
              <Button type="submit" icon="sparkles" loading={applying} className="w-full">
                Aplicar descuento
              </Button>
            </form>
          </Card>
        </div>
      </div>

      <JsonBlock data={cart.data} label="GET /cart · respuesta" />
    </div>
  );
}
