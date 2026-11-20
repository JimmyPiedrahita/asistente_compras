import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";
import { api } from "../api";

function Listado({ titulo, descripcion, filas, tone }) {
  if (!filas.length) {
    return (
      <Card title={titulo} description={descripcion}>
        <p className="py-6 text-center text-sm text-stone-500">Sin productos para calcular.</p>
      </Card>
    );
  }
  return (
    <Card title={titulo} description={descripcion}>
      <ol className="divide-y divide-stone-100 rounded-lg border border-stone-200">
        {filas.map((fila, indice) => (
          <li key={fila.producto_id} className="flex items-center gap-3 px-4 py-2.5">
            <span className="w-6 text-xs font-semibold tabular-nums text-stone-400">
              {indice + 1}.
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-stone-900">{fila.nombre}</p>
              <p className="truncate text-xs text-stone-500">
                {fila.marca_variedad ? `${fila.marca_variedad} · ` : ""}
                {fila.presentacion}
              </p>
            </div>
            <Badge tone={tone}>
              {fila.unidades_vendidas}{" "}
              {fila.unidades_vendidas === 1 ? "unidad" : "unidades"}
            </Badge>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export default function StatsPage() {
  const { token, notifyError } = useApp();
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const resultado = await api.stats(token);
      setDatos(resultado);
    } catch (error) {
      notifyError(error);
    } finally {
      setCargando(false);
    }
  }, [notifyError, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (cargando) {
    return (
      <Card>
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-stone-500">
          <Spinner /> Calculando estadísticas…
        </div>
      </Card>
    );
  }

  if (!datos?.hay_productos) {
    return (
      <Card>
        <EmptyState
          icon="dashboard"
          title="Todavía no tienes productos"
          description="Cuando agregues productos a tu almacén, aquí verás cuáles se venden más y cuáles menos."
        />
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card
        title="Estadísticas de mi almacén"
        description="Medidas por unidades vendidas en compras con pago completado. Sin filtros por fecha."
        actions={
          <Button size="sm" variant="secondary" icon="refresh" onClick={cargar}>
            Actualizar
          </Button>
        }
      >
        {!datos.hay_ventas ? (
          <Alert tone="info">
            Aún no existen ventas registradas. Todos los productos aparecen con cero unidades
            vendidas.
          </Alert>
        ) : (
          <p className="text-sm text-stone-600">
            Los listados incluyen todos los productos actuales; los empates se ordenan
            alfabéticamente por nombre.
          </p>
        )}
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Listado
          titulo="Productos más vendidos"
          descripcion="Orden descendente por unidades vendidas."
          filas={datos.mas_vendidos}
          tone="emerald"
        />
        <Listado
          titulo="Productos menos vendidos"
          descripcion="Orden ascendente por unidades vendidas."
          filas={datos.menos_vendidos}
          tone="slate"
        />
      </div>
    </div>
  );
}
