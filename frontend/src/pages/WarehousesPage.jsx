import { useCallback, useEffect, useState } from "react";
import Icon from "../components/Icon";
import {
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

export default function WarehousesPage() {
  const { token, notify, notifyError } = useApp();
  const [almacenes, setAlmacenes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [nombre, setNombre] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const datos = await api.listWarehouses(token);
      setAlmacenes(datos ?? []);
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
    if (!nombre.trim()) return;
    setGuardando(true);
    try {
      await api.createWarehouse(token, nombre.trim());
      setNombre("");
      await cargar();
      notify("Almacén creado. Ahora puedes asignarle un administrador.", "success", "Almacenes");
    } catch (error) {
      notifyError(error);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr] lg:items-start">
      <Card
        title="Crear almacén"
        description="La creación de un almacén no genera productos ni cupones automáticamente."
      >
        <form onSubmit={crear} className="space-y-3">
          <Field label="Nombre del almacén" htmlFor="almacen-nombre">
            <Input
              id="almacen-nombre"
              value={nombre}
              onChange={(evento) => setNombre(evento.target.value)}
              maxLength={120}
              placeholder="Ej. Almacén Central"
              required
            />
          </Field>
          <Button type="submit" icon="plus" loading={guardando} className="w-full">
            Crear almacén
          </Button>
        </form>
        <p className="mt-3 text-xs leading-relaxed text-slate-500">
          El nombre debe ser único. No se incluyen funciones para editar o eliminar almacenes.
        </p>
      </Card>

      <Card
        title={`Almacenes registrados · ${almacenes.length}`}
        description="Cada administrador de almacén se vincula a un único almacén."
      >
        {cargando ? (
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
            <Spinner /> Cargando almacenes…
          </div>
        ) : almacenes.length === 0 ? (
          <EmptyState
            icon="warehouse"
            title="Todavía no hay almacenes"
            description="Crea el primer almacén para poder asignarle un administrador y comenzar a registrar productos."
          />
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {almacenes.map((almacen) => (
              <li key={almacen.almacen_id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-500">
                  <Icon name="warehouse" size={17} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-slate-900">{almacen.nombre}</p>
                  <p className="text-xs text-slate-500">Creado el {fecha(almacen.creado_en)}</p>
                </div>
                <Badge tone="slate">
                  {almacen.productos} {almacen.productos === 1 ? "producto" : "productos"}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
