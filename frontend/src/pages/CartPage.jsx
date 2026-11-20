import { useCallback, useEffect, useRef, useState } from "react";
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
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";
import { api } from "../api";

const AVISO_ENTREGA =
  "Cada almacén coordina la entrega de sus productos de forma independiente. " +
  "Compartiremos tu nombre, teléfono y dirección con los almacenes incluidos en esta " +
  "compra para que puedan gestionar la entrega. Una compra con productos de varios " +
  "almacenes puede implicar entregas separadas.";

function dinero(valor) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 2,
  }).format(Number(valor || 0));
}

function fecha(valor) {
  if (!valor) return "";
  const date = new Date(valor);
  if (Number.isNaN(date.getTime())) return valor;
  return date.toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

function nuevaClaveIdempotencia() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `compra-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function CartPage({ onNavigate }) {
  const { token, session, notify, notifyError } = useApp();
  const [resumen, setResumen] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [codigo, setCodigo] = useState("");
  const [aplicando, setAplicando] = useState(false);
  const [ocupado, setOcupado] = useState("");
  const [confirmando, setConfirmando] = useState(false);
  const [compra, setCompra] = useState(null);
  const [entrega, setEntrega] = useState({
    telefono: session?.telefono || "",
    direccion: session?.direccion || "",
    ciudad: session?.ciudad || "",
  });
  const claveRef = useRef(null);
  if (claveRef.current === null) claveRef.current = nuevaClaveIdempotencia();

  const cargar = useCallback(async () => {
    try {
      const datos = await api.getCart(token);
      setResumen(datos);
    } catch (error) {
      notifyError(error);
    } finally {
      setCargando(false);
    }
  }, [notifyError, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const ejecutar = async (clave, accion) => {
    setOcupado(clave);
    try {
      const datos = await accion();
      setResumen(datos);
    } catch (error) {
      notifyError(error);
    } finally {
      setOcupado("");
    }
  };

  const cambiarCantidad = (item, cantidad) => {
    if (cantidad < 1) return;
    ejecutar(`item-${item.item_id}`, () =>
      api.updateCartItem(token, item.item_id, cantidad),
    );
  };

  const quitarItem = (item) =>
    ejecutar(`item-${item.item_id}`, () => api.removeCartItem(token, item.item_id));

  const vaciar = () => ejecutar("vaciar", () => api.clearCart(token));

  const aplicarCupon = async (evento) => {
    evento.preventDefault();
    if (!codigo.trim()) return;
    setAplicando(true);
    try {
      const datos = await api.applyCoupon(token, codigo.trim());
      setResumen(datos);
      setCodigo("");
      notify("Cupón aplicado al almacén correspondiente.", "success", "Cupones");
    } catch (error) {
      notifyError(error);
    } finally {
      setAplicando(false);
    }
  };

  const quitarCupon = (cupon) =>
    ejecutar(`cupon-${cupon.codigo}`, () => api.removeCoupon(token, cupon.codigo));

  const confirmar = async () => {
    if (!resumen?.items?.length) return;
    if (!entrega.telefono.trim() || !entrega.direccion.trim() || !entrega.ciudad.trim()) {
      notify("Completa el teléfono, la dirección y la ciudad de entrega.", "error");
      return;
    }
    setConfirmando(true);
    try {
      const datos = await api.checkout(token, {
        telefono: entrega.telefono,
        direccion: entrega.direccion,
        ciudad: entrega.ciudad,
        total_esperado: resumen.total,
        clave_idempotencia: claveRef.current,
      });
      claveRef.current = nuevaClaveIdempotencia();
      setCompra(datos);
      setResumen(null);
      notify("Pago completado. La compra quedó registrada.", "success", "Compra");
    } catch (error) {
      if (error?.status === 409 && error.payload?.detalles?.resumen) {
        setResumen(error.payload.detalles.resumen);
        notify(
          "El total cambió porque un cupón ya no está disponible. Revisa el nuevo resumen y confirma otra vez.",
          "info",
          "Total actualizado",
        );
      } else {
        notifyError(error);
      }
    } finally {
      setConfirmando(false);
    }
  };

  if (cargando) {
    return (
      <Card>
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-stone-500">
          <Spinner /> Cargando carrito…
        </div>
      </Card>
    );
  }

  if (compra) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Card>
          <div className="flex flex-col items-center text-center">
            <span className="grid h-14 w-14 place-items-center rounded-full bg-emerald-50 text-emerald-600">
              <Icon name="check" size={26} />
            </span>
            <h1 className="mt-4 text-xl font-bold text-stone-900">Pago completado</h1>
            <p className="mt-1 max-w-xl text-sm text-stone-600">
              Tu compra quedó registrada y los datos de entrega fueron guardados.
            </p>
            <div className="mt-4 grid w-full gap-2 rounded-lg border border-stone-200 bg-stone-50/60 p-4 text-left text-sm sm:grid-cols-2">
              <p>
                <span className="text-stone-500">Identificador: </span>
                <span className="font-mono text-xs text-stone-800">{compra.compra_id}</span>
              </p>
              <p>
                <span className="text-stone-500">Fecha: </span>
                <span className="text-stone-800">{fecha(compra.fecha)}</span>
              </p>
              <p>
                <span className="text-stone-500">Total pagado: </span>
                <span className="font-semibold text-stone-900">{dinero(compra.total)}</span>
              </p>
              <p>
                <span className="text-stone-500">Almacenes: </span>
                <span className="text-stone-800">{compra.por_almacen.length}</span>
              </p>
            </div>
          </div>
        </Card>

        <Card title="Resumen de la compra" description="Conservado con los datos de entrega confirmados.">
          <div className="space-y-3">
            {compra.por_almacen.map((parte) => (
              <div key={parte.almacen_id} className="rounded-lg border border-stone-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-stone-900">{parte.almacen_nombre}</p>
                  <Badge tone="slate">Entrega independiente</Badge>
                </div>
                <ul className="mt-2 space-y-1 text-sm text-stone-600">
                  {compra.items
                    .filter((item) => item.almacen_id === parte.almacen_id)
                    .map((item) => (
                      <li key={item.producto_id} className="flex justify-between gap-3">
                        <span>
                          {item.cantidad} × {item.nombre}{" "}
                          <span className="text-xs text-stone-400">({item.presentacion})</span>
                        </span>
                        <span className="tabular-nums">{dinero(item.importe)}</span>
                      </li>
                    ))}
                </ul>
                <div className="mt-2 border-t border-stone-100 pt-2 text-xs text-stone-500">
                  <p className="flex justify-between">
                    <span>Subtotal</span>
                    <span>{dinero(parte.subtotal)}</span>
                  </p>
                  {parte.cupon_codigo ? (
                    <p className="flex justify-between">
                      <span>
                        Cupón {parte.cupon_codigo} ({parte.cupon_porcentaje} %)
                      </span>
                      <span>-{dinero(parte.descuento)}</span>
                    </p>
                  ) : null}
                  <p className="mt-1 flex justify-between text-sm font-semibold text-stone-900">
                    <span>Total del almacén</span>
                    <span>{dinero(parte.total)}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-lg border border-stone-200 bg-stone-50/60 p-4 text-sm">
            <p className="font-semibold text-stone-900">Datos de entrega confirmados</p>
            <p className="mt-1 text-stone-600">
              {compra.datos_entrega.nombre} · {compra.datos_entrega.telefono}
            </p>
            <p className="text-stone-600">
              {compra.datos_entrega.direccion}, {compra.datos_entrega.ciudad}
            </p>
          </div>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Button variant="secondary" icon="list" onClick={() => onNavigate("lista")}>
              Volver a la lista
            </Button>
            <Button icon="cart" onClick={() => setCompra(null)}>
              Nueva compra
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!resumen || !resumen.items.length) {
    return (
      <Card>
        <EmptyState
          icon="cart"
          title="Tu carrito está vacío"
          description="Busca productos desde tu lista y agrégalos al carrito para continuar."
          action={
            <Button icon="search" onClick={() => onNavigate("lista")}>
              Ir a mi lista
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_360px] lg:items-start">
      <div className="space-y-4">
        <Card
          title={`Carrito · ${resumen.cantidad_items} ${
            resumen.cantidad_items === 1 ? "unidad" : "unidades"
          }`}
          description="Revisa cantidades y el detalle por almacén."
          actions={
            <Button size="sm" variant="secondary" icon="trash" loading={ocupado === "vaciar"} onClick={vaciar}>
              Vaciar carrito
            </Button>
          }
        >
          {resumen.avisos?.length ? (
            <div className="mb-4 space-y-2">
              {resumen.avisos.map((aviso) => (
                <Alert key={aviso} tone="warning">
                  {aviso}
                </Alert>
              ))}
            </div>
          ) : null}

          <div className="space-y-4">
            {resumen.detalle_almacenes.map((parte) => (
              <section key={parte.almacen_id} className="rounded-lg border border-stone-200">
                <header className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-100 bg-stone-50/60 px-4 py-2.5">
                  <p className="flex items-center gap-2 text-sm font-semibold text-stone-900">
                    <Icon name="warehouse" size={15} className="text-stone-500" />
                    {parte.almacen}
                  </p>
                  <Badge tone="slate">Entrega independiente</Badge>
                </header>
                <ul className="divide-y divide-stone-100">
                  {parte.items.map((item) => (
                    <li key={item.item_id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                      {item.imagen_url ? (
                        <img
                          src={item.imagen_url}
                          alt={`Imagen de ${item.nombre}`}
                          loading="lazy"
                          className="h-11 w-11 shrink-0 rounded-lg object-cover ring-1 ring-stone-200"
                        />
                      ) : (
                        <span
                          className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-dashed border-stone-200 bg-stone-50 text-stone-300"
                          aria-hidden="true"
                        >
                          <Icon name="package" size={17} />
                        </span>
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-stone-900">{item.nombre}</p>
                        <p className="mt-0.5 text-xs text-stone-500">
                          {item.marca_variedad ? `${item.marca_variedad} · ` : ""}
                          {item.presentacion} · {dinero(item.precio_unitario)} c/u
                        </p>
                      </div>
                      <div className="flex items-center rounded-lg border border-stone-200">
                        <button
                          className="px-2.5 py-1.5 text-stone-500 transition hover:bg-stone-50 disabled:opacity-40"
                          onClick={() => cambiarCantidad(item, item.cantidad - 1)}
                          disabled={item.cantidad <= 1 || ocupado === `item-${item.item_id}`}
                          aria-label="Disminuir cantidad"
                        >
                          −
                        </button>
                        <span className="min-w-8 text-center text-sm font-semibold text-stone-900">
                          {item.cantidad}
                        </span>
                        <button
                          className="px-2.5 py-1.5 text-stone-500 transition hover:bg-stone-50 disabled:opacity-40"
                          onClick={() => cambiarCantidad(item, item.cantidad + 1)}
                          disabled={ocupado === `item-${item.item_id}`}
                          aria-label="Aumentar cantidad"
                        >
                          +
                        </button>
                      </div>
                      <p className="w-24 text-right text-sm font-bold tabular-nums text-stone-900">
                        {dinero(item.importe)}
                      </p>
                      <button
                        onClick={() => quitarItem(item)}
                        className="rounded-md p-1.5 text-stone-400 transition hover:bg-rose-50 hover:text-rose-600"
                        aria-label={`Quitar ${item.nombre}`}
                      >
                        <Icon name="trash" size={15} />
                      </button>
                    </li>
                  ))}
                </ul>
                <div className="border-t border-stone-100 px-4 py-2.5 text-sm">
                  <p className="flex justify-between text-stone-600">
                    <span>Subtotal del almacén</span>
                    <span className="tabular-nums">{dinero(parte.subtotal)}</span>
                  </p>
                  {parte.cupon_codigo ? (
                    <>
                      <p className="mt-1 flex justify-between text-emerald-700">
                        <span>
                          Cupón {parte.cupon_codigo} ({parte.cupon_porcentaje} %)
                        </span>
                        <span className="tabular-nums">-{dinero(parte.descuento)}</span>
                      </p>
                      <p className="mt-1 flex justify-between font-semibold text-stone-900">
                        <span>Total del almacén</span>
                        <span className="tabular-nums">{dinero(parte.total)}</span>
                      </p>
                    </>
                  ) : null}
                </div>
              </section>
            ))}
          </div>
        </Card>

        <Card
          title="Cupones"
          description="Hasta tres cupones por compra, uno por almacén. El descuento aplica solo a los productos de su almacén."
        >
          <form onSubmit={aplicarCupon} className="flex flex-wrap gap-2">
            <Input
              value={codigo}
              onChange={(evento) => setCodigo(evento.target.value.toUpperCase())}
              placeholder="Código del cupón"
              maxLength={50}
              className="max-w-xs flex-1"
              aria-label="Código del cupón"
            />
            <Button type="submit" icon="sparkles" loading={aplicando} disabled={!codigo.trim()}>
              Aplicar cupón
            </Button>
          </form>

          <div className="mt-4">
            {resumen.cupones_aplicados.length ? (
              <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200">
                {resumen.cupones_aplicados.map((cupon) => (
                  <li key={cupon.codigo} className="flex flex-wrap items-center gap-2 px-3 py-2.5">
                    <Badge tone="emerald">{cupon.codigo}</Badge>
                    <span className="min-w-0 flex-1 text-xs text-stone-500">
                      {cupon.almacen} · {cupon.porcentaje} % de descuento
                    </span>
                    <button
                      onClick={() => quitarCupon(cupon)}
                      className="rounded-md p-1.5 text-stone-400 transition hover:bg-rose-50 hover:text-rose-600"
                      aria-label={`Quitar cupón ${cupon.codigo}`}
                    >
                      <Icon name="x" size={14} />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-stone-500">
                No hay cupones aplicados. Ingresa el código que te haya dado un almacén.
              </p>
            )}
          </div>
        </Card>
      </div>

      <div className="space-y-4 lg:sticky lg:top-28">
        <Card title="Resumen de compra">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-stone-600">Subtotal general</dt>
              <dd className="font-medium tabular-nums text-stone-900">{dinero(resumen.subtotal)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-stone-600">Descuento total</dt>
              <dd className="font-medium tabular-nums text-emerald-700">
                -{dinero(resumen.descuento_total)}
              </dd>
            </div>
            <div className="flex justify-between border-t border-stone-200 pt-2 text-base font-bold">
              <dt>Total final</dt>
              <dd className="tabular-nums text-stone-900">{dinero(resumen.total)}</dd>
            </div>
          </dl>

          <div className="mt-4 space-y-3 border-t border-stone-100 pt-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
              Datos de entrega
            </p>
            <Field label="Nombre">
              <Input value={session?.usuario || ""} readOnly disabled />
            </Field>
            <Field label="Teléfono" htmlFor="entrega-telefono">
              <Input
                id="entrega-telefono"
                value={entrega.telefono}
                onChange={(evento) =>
                  setEntrega((actual) => ({ ...actual, telefono: evento.target.value }))
                }
                maxLength={30}
                autoComplete="tel"
              />
            </Field>
            <Field label="Dirección" htmlFor="entrega-direccion">
              <Input
                id="entrega-direccion"
                value={entrega.direccion}
                onChange={(evento) =>
                  setEntrega((actual) => ({ ...actual, direccion: evento.target.value }))
                }
                maxLength={300}
                autoComplete="street-address"
              />
            </Field>
            <Field label="Ciudad o municipio" htmlFor="entrega-ciudad">
              <Input
                id="entrega-ciudad"
                value={entrega.ciudad}
                onChange={(evento) =>
                  setEntrega((actual) => ({ ...actual, ciudad: evento.target.value }))
                }
                maxLength={120}
                autoComplete="address-level2"
              />
            </Field>
            <p className="text-xs text-stone-500">
              Puedes corregir estos datos antes de confirmar. Se guardarán con la compra.
            </p>
          </div>

          <Alert tone="info" className="mt-4">
            {AVISO_ENTREGA}
          </Alert>

          <Button
            size="lg"
            className="mt-4 w-full"
            icon="check"
            loading={confirmando}
            onClick={confirmar}
          >
            Confirmar pago · {dinero(resumen.total)}
          </Button>
        </Card>
      </div>
    </div>
  );
}
