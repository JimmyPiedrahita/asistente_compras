import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";
import { api } from "../api";

function fecha(valor) {
  if (!valor) return "";
  const date = new Date(valor);
  return Number.isNaN(date.getTime()) ? valor : date.toLocaleDateString("es-CO");
}

export default function CouponsPage() {
  const { token, notify, notifyError } = useApp();
  const [cupones, setCupones] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [codigo, setCodigo] = useState("");
  const [porcentaje, setPorcentaje] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [eliminando, setEliminando] = useState("");

  const cargar = useCallback(async () => {
    try {
      const datos = await api.listCoupons(token);
      setCupones(datos ?? []);
    } catch (error) {
      notifyError(error);
    } finally {
      setCargando(false);
    }
  }, [notifyError, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const crear = async (evento) => {
    evento.preventDefault();
    const valor = Number(porcentaje);
    if (!codigo.trim()) {
      notify("Escribe el código del cupón.", "error");
      return;
    }
    if (!Number.isFinite(valor) || valor <= 0 || valor > 100) {
      notify("El porcentaje debe ser mayor que 0 y menor o igual a 100.", "error");
      return;
    }
    setGuardando(true);
    try {
      await api.createCoupon(token, {
        codigo: codigo.trim().toUpperCase(),
        porcentaje: valor,
      });
      setCodigo("");
      setPorcentaje("");
      await cargar();
      notify("Cupón creado para tu almacén.", "success", "Cupones");
    } catch (error) {
      notifyError(error);
    } finally {
      setGuardando(false);
    }
  };

  const eliminar = async (cupon) => {
    if (
      !window.confirm(
        `¿Eliminar el cupón ${cupon.codigo}? Dejará de aplicarse en compras nuevas o no completadas.`,
      )
    ) {
      return;
    }
    setEliminando(cupon.cupon_id);
    try {
      await api.deleteCoupon(token, cupon.cupon_id);
      await cargar();
      notify("Cupón eliminado.", "success", "Cupones");
    } catch (error) {
      notifyError(error);
    } finally {
      setEliminando("");
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr] lg:items-start">
      <Card
        title="Crear cupón"
        description="El cupón pertenece automáticamente a tu almacén y no puede editarse después."
      >
        <form onSubmit={crear} className="space-y-3">
          <Field label="Código" htmlFor="cupon-codigo" hint="Debe ser único en toda la aplicación.">
            <Input
              id="cupon-codigo"
              value={codigo}
              onChange={(evento) => setCodigo(evento.target.value.toUpperCase())}
              maxLength={50}
              placeholder="Ej. ARROZ10"
              required
            />
          </Field>
          <Field
            label="Porcentaje de descuento"
            htmlFor="cupon-porcentaje"
            hint="Mayor que 0 y menor o igual a 100."
          >
            <Input
              id="cupon-porcentaje"
              type="number"
              min="0.01"
              max="100"
              step="0.01"
              value={porcentaje}
              onChange={(evento) => setPorcentaje(evento.target.value)}
              required
            />
          </Field>
          <Button type="submit" icon="plus" loading={guardando} className="w-full">
            Crear cupón
          </Button>
        </form>
        <Alert tone="info" className="mt-4">
          El descuento se aplica al subtotal de los productos de tu almacén. No hay cupones
          globales, fechas de vencimiento ni límites de uso.
        </Alert>
      </Card>

      <Card
        title={`Cupones de mi almacén · ${cupones.length}`}
        description="Los cupones eliminados no afectan compras ya completadas."
      >
        {cargando ? (
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-stone-500">
            <Spinner /> Cargando cupones…
          </div>
        ) : cupones.length === 0 ? (
          <EmptyState
            icon="sparkles"
            title="Todavía no tienes cupones"
            description="Crea un cupón para ofrecer un descuento sobre los productos de tu almacén."
          />
        ) : (
          <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200">
            {cupones.map((cupon) => (
              <li key={cupon.cupon_id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <Badge tone="emerald">{cupon.codigo}</Badge>
                <span className="text-sm font-semibold text-stone-900">
                  {cupon.porcentaje} % de descuento
                </span>
                <span className="ml-auto text-xs text-stone-400">
                  Creado el {fecha(cupon.creado_en)}
                </span>
                <Button
                  size="sm"
                  variant="dangerSoft"
                  icon="trash"
                  loading={eliminando === cupon.cupon_id}
                  onClick={() => eliminar(cupon)}
                >
                  Eliminar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
