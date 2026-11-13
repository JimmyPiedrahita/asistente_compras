import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Select,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";
import { api } from "../api";

const VACIO = { nombre: "", email: "", password: "", almacen_id: "" };

function Credenciales({ admin, onGuardado }) {
  const { token, notify, notifyError } = useApp();
  const [abierto, setAbierto] = useState(false);
  const [email, setEmail] = useState(admin.email);
  const [password, setPassword] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    setEmail(admin.email);
  }, [admin.email]);

  const guardar = async (evento) => {
    evento.preventDefault();
    const datos = {};
    if (email.trim() && email.trim() !== admin.email) datos.email = email.trim();
    if (password) datos.password = password;
    if (!Object.keys(datos).length) {
      notify("Indica un correo nuevo o una contraseña nueva.", "info");
      return;
    }
    setGuardando(true);
    try {
      await api.updateAdminCredentials(token, admin.usuario_id, datos);
      setPassword("");
      setAbierto(false);
      notify("Credenciales actualizadas.", "success", "Administradores");
      onGuardado();
    } catch (error) {
      notifyError(error);
    } finally {
      setGuardando(false);
    }
  };

  if (!abierto) {
    return (
      <Button size="sm" variant="secondary" icon="key" onClick={() => setAbierto(true)}>
        Actualizar credenciales
      </Button>
    );
  }

  return (
    <form
      onSubmit={guardar}
      className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50/60 p-3"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Correo electrónico" htmlFor={`admin-email-${admin.usuario_id}`}>
          <Input
            id={`admin-email-${admin.usuario_id}`}
            type="email"
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
          />
        </Field>
        <Field
          label="Nueva contraseña"
          htmlFor={`admin-pass-${admin.usuario_id}`}
          hint="Déjala vacía para no cambiarla."
        >
          <Input
            id={`admin-pass-${admin.usuario_id}`}
            type="password"
            minLength={6}
            autoComplete="new-password"
            value={password}
            onChange={(evento) => setPassword(evento.target.value)}
          />
        </Field>
      </div>
      <div className="mt-3 flex gap-2">
        <Button type="submit" size="sm" icon="check" loading={guardando}>
          Guardar
        </Button>
        <Button
          size="sm"
          variant="secondary"
          icon="x"
          onClick={() => {
            setAbierto(false);
            setEmail(admin.email);
            setPassword("");
          }}
        >
          Cancelar
        </Button>
      </div>
    </form>
  );
}

export default function AdminsPage() {
  const { token, notify, notifyError } = useApp();
  const [admins, setAdmins] = useState([]);
  const [almacenes, setAlmacenes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const [listaAdmins, listaAlmacenes] = await Promise.all([
        api.listAdmins(token),
        api.listWarehouses(token),
      ]);
      setAdmins(listaAdmins ?? []);
      setAlmacenes(listaAlmacenes ?? []);
      setForm((actual) => ({
        ...actual,
        almacen_id: actual.almacen_id || listaAlmacenes?.[0]?.almacen_id || "",
      }));
    } catch (error) {
      notifyError(error);
    } finally {
      setCargando(false);
    }
  }, [notifyError, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const cambiar = (campo) => (evento) =>
    setForm((actual) => ({ ...actual, [campo]: evento.target.value }));

  const crear = async (evento) => {
    evento.preventDefault();
    if (!form.nombre.trim() || !form.email.trim() || !form.password || !form.almacen_id) {
      notify("Completa el nombre, el correo, la contraseña y el almacén.", "error");
      return;
    }
    if (form.password.length < 6) {
      notify("La contraseña debe tener al menos 6 caracteres.", "error");
      return;
    }
    setGuardando(true);
    try {
      await api.createAdmin(token, {
        nombre: form.nombre.trim(),
        email: form.email.trim(),
        password: form.password,
        almacen_id: form.almacen_id,
      });
      setForm((actual) => ({ ...VACIO, almacen_id: actual.almacen_id }));
      await cargar();
      notify("Administrador de almacén creado y vinculado.", "success", "Administradores");
    } catch (error) {
      notifyError(error);
    } finally {
      setGuardando(false);
    }
  };

  if (cargando) {
    return (
      <Card>
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
          <Spinner /> Cargando administradores…
        </div>
      </Card>
    );
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[380px_1fr] lg:items-start">
      <Card
        title="Crear administrador de almacén"
        description="La cuenta quedará vinculada a un único almacén."
      >
        {almacenes.length === 0 ? (
          <Alert tone="warning" title="Primero crea un almacén">
            Para crear un administrador de almacén debe existir al menos un almacén registrado.
          </Alert>
        ) : (
          <form onSubmit={crear} className="space-y-3">
            <Field label="Nombre" htmlFor="admin-nombre">
              <Input
                id="admin-nombre"
                value={form.nombre}
                onChange={cambiar("nombre")}
                maxLength={120}
                required
              />
            </Field>
            <Field label="Correo electrónico" htmlFor="admin-nuevo-email">
              <Input
                id="admin-nuevo-email"
                type="email"
                autoComplete="off"
                value={form.email}
                onChange={cambiar("email")}
                required
              />
            </Field>
            <Field label="Contraseña" htmlFor="admin-nuevo-pass" hint="Mínimo 6 caracteres.">
              <Input
                id="admin-nuevo-pass"
                type="password"
                minLength={6}
                autoComplete="new-password"
                value={form.password}
                onChange={cambiar("password")}
                required
              />
            </Field>
            <Field label="Almacén asignado" htmlFor="admin-almacen">
              <Select
                id="admin-almacen"
                value={form.almacen_id}
                onChange={cambiar("almacen_id")}
                required
              >
                <option value="">Selecciona un almacén</option>
                {almacenes.map((almacen) => (
                  <option key={almacen.almacen_id} value={almacen.almacen_id}>
                    {almacen.nombre}
                  </option>
                ))}
              </Select>
            </Field>
            <Button type="submit" icon="plus" loading={guardando} className="w-full">
              Crear administrador
            </Button>
          </form>
        )}
        <p className="mt-3 text-xs leading-relaxed text-slate-500">
          El correo no puede repetirse entre cuentas. No se incluyen funciones para eliminar
          administradores ni para crear otros administradores de la aplicación.
        </p>
      </Card>

      <Card
        title={`Administradores de almacén · ${admins.length}`}
        description="Puedes actualizar el correo y la contraseña de cada cuenta."
      >
        {admins.length === 0 ? (
          <EmptyState
            icon="shield"
            title="Todavía no hay administradores de almacén"
            description="Crea un almacén y luego asígnale un administrador para que pueda gestionar su catálogo."
          />
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {admins.map((admin) => (
              <li key={admin.usuario_id} className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-100 text-slate-500">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="17"
                      height="17"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <circle cx="12" cy="8" r="4" />
                      <path d="M4 21a8 8 0 0 1 16 0" />
                    </svg>
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-900">{admin.nombre}</p>
                    <p className="truncate text-xs text-slate-500">{admin.email}</p>
                  </div>
                  <Badge tone={admin.activo ? "emerald" : "rose"}>
                    {admin.activo ? "Activo" : "Inactivo"}
                  </Badge>
                  <Badge tone="slate">{admin.almacen_nombre || "Sin almacén"}</Badge>
                  <Credenciales admin={admin} onGuardado={cargar} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
