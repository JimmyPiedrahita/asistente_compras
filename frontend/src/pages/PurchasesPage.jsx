import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Money,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";
import { api } from "../api";

function fecha(valor) {
  if (!valor) return "";
  const date = new Date(valor);
  if (Number.isNaN(date.getTime())) return valor;
  return date.toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

export default function PurchasesPage() {
  const { token, notifyError } = useApp();
  const [compras, setCompras] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [abierta, setAbierta] = useState("");

  const cargar = useCallback(async () => {
    try {
      const datos = await api.listPurchases(token);
      setCompras(datos ?? []);
    } catch (error) {
      notifyError(error);
    } finally {
      setCargando(false);
    }
  }, [notifyError, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  return (
    <div className="space-y-5">
      <Card
        title="Compras de mi almacén"
        description="Solo se muestran compras con pago simulado completado que incluyen productos de tu almacén."
        actions={
          <Button size="sm" variant="secondary" icon="refresh" onClick={cargar}>
            Actualizar
          </Button>
        }
      >
        {cargando ? (
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
            <Spinner /> Cargando compras…
          </div>
        ) : compras.length === 0 ? (
          <EmptyState
            icon="cart"
            title="Aún no hay compras de tu almacén"
            description="Cuando un cliente complete una compra con tus productos, aparecerá aquí con los datos para coordinar la entrega."
          />
        ) : (
          <div className="space-y-3">
            {compras.map((compra) => {
              const expandida = abierta === compra.compra_id;
              return (
                <article
                  key={compra.compra_id}
                  className="overflow-hidden rounded-lg border border-slate-200"
                >
                  <button
                    onClick={() => setAbierta(expandida ? "" : compra.compra_id)}
                    className="flex w-full flex-wrap items-center gap-3 bg-slate-50/60 px-4 py-3 text-left transition hover:bg-slate-50"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
                        Compra <span className="font-mono text-xs">{compra.compra_id}</span>
                        <Badge tone="emerald">Pagada (simulada)</Badge>
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {fecha(compra.fecha)} · {compra.cliente_nombre}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold tabular-nums text-slate-900">
                        <Money value={compra.total} />
                      </p>
                      <p className="text-[11px] text-slate-400">
                        {compra.items.length} {compra.items.length === 1 ? "producto" : "productos"}
                      </p>
                    </div>
                    <span className="text-slate-400">
                      {expandida ? "−" : "+"}
                    </span>
                  </button>

                  {expandida ? (
                    <div className="border-t border-slate-100 px-4 py-4">
                      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                            Productos de mi almacén
                          </p>
                          <div className="mt-2 overflow-x-auto">
                            <table className="w-full min-w-[480px] text-left text-sm">
                              <thead>
                                <tr className="border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-400">
                                  <th className="pb-2 pr-3 font-semibold">Producto</th>
                                  <th className="pb-2 pr-3 text-right font-semibold">Cantidad</th>
                                  <th className="pb-2 pr-3 text-right font-semibold">Precio</th>
                                  <th className="pb-2 text-right font-semibold">Importe</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {compra.items.map((item) => (
                                  <tr key={item.producto_id}>
                                    <td className="py-2 pr-3">
                                      <p className="font-medium text-slate-900">{item.nombre}</p>
                                      <p className="text-xs text-slate-500">
                                        {item.marca_variedad ? `${item.marca_variedad} · ` : ""}
                                        {item.presentacion}
                                      </p>
                                    </td>
                                    <td className="py-2 pr-3 text-right tabular-nums text-slate-700">
                                      {item.cantidad}
                                    </td>
                                    <td className="py-2 pr-3 text-right tabular-nums text-slate-700">
                                      <Money value={item.precio_unitario} />
                                    </td>
                                    <td className="py-2 text-right font-medium tabular-nums text-slate-900">
                                      <Money value={item.importe} />
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <dl className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-sm">
                            <div className="flex justify-between">
                              <dt className="text-slate-600">Subtotal de mi almacén</dt>
                              <dd className="tabular-nums text-slate-900">
                                <Money value={compra.subtotal} />
                              </dd>
                            </div>
                            {compra.cupon_codigo ? (
                              <div className="flex justify-between text-emerald-700">
                                <dt>
                                  Cupón {compra.cupon_codigo} ({compra.cupon_porcentaje} %)
                                </dt>
                                <dd className="tabular-nums">
                                  -<Money value={compra.descuento} />
                                </dd>
                              </div>
                            ) : null}
                            <div className="flex justify-between border-t border-slate-100 pt-1 text-base font-bold">
                              <dt>Total de mi parte</dt>
                              <dd className="tabular-nums text-slate-900">
                                <Money value={compra.total} />
                              </dd>
                            </div>
                          </dl>
                        </div>

                        <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 text-sm">
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                            Datos de entrega
                          </p>
                          <p className="mt-2 font-medium text-slate-900">{compra.cliente_nombre}</p>
                          <p className="text-slate-600">{compra.telefono}</p>
                          <p className="mt-1 text-slate-600">{compra.direccion}</p>
                          <p className="text-slate-600">{compra.ciudad}</p>
                          <p className="mt-3 text-xs leading-relaxed text-slate-500">
                            La entrega se coordina por fuera de la aplicación. Esta sección es
                            únicamente de consulta.
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
