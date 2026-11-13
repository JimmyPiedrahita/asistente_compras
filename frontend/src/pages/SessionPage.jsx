import { useCallback, useEffect, useState } from "react";
import { api, errorText } from "../api";
import Icon from "../components/Icon";
import {
  Alert,
  Badge,
  Button,
  Card,
  CopyButton,
  EmptyState,
  Field,
  Input,
  JsonBlock,
  Money,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";

export default function SessionPage({ onNavigate }) {
  const { session, token, saveSession, closeSession, notify, notifyError } = useApp();
  const [userForm, setUserForm] = useState({ nombre: "" });
  const [providerForm, setProviderForm] = useState({ nombre: "" });
  const [adminForm, setAdminForm] = useState({ clave: "" });
  const [creatingUser, setCreatingUser] = useState(false);
  const [creatingProvider, setCreatingProvider] = useState(false);
  const [creatingAdmin, setCreatingAdmin] = useState(false);
  const [closing, setClosing] = useState(false);
  const [info, setInfo] = useState({ loading: false, data: null, error: null });

  const refresh = useCallback(async () => {
    if (!token) {
      setInfo({ loading: false, data: null, error: null });
      return;
    }
    setInfo((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.getSession(token);
      setInfo({ loading: false, data, error: null });
    } catch (error) {
      setInfo({ loading: false, data: null, error });
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const createUser = async (event) => {
    event.preventDefault();
    if (!userForm.nombre.trim()) {
      notify("Escribe un nombre de usuario.", "info", "Datos incompletos");
      return;
    }
    setCreatingUser(true);
    try {
      const { data } = await api.createUserSession(userForm.nombre.trim());
      saveSession(data);
      setUserForm({ nombre: "" });
      notify(`Bienvenido, ${data.usuario}. Sesión de cliente creada.`, "success", "Sesión");
    } catch (error) {
      notifyError(error);
    } finally {
      setCreatingUser(false);
    }
  };

  const createProvider = async (event) => {
    event.preventDefault();
    if (!providerForm.nombre.trim()) {
      notify("Escribe el nombre del proveedor.", "info", "Datos incompletos");
      return;
    }
    setCreatingProvider(true);
    try {
      const { data } = await api.createProviderSession(providerForm.nombre.trim());
      saveSession(data);
      setProviderForm({ nombre: "" });
      notify(
        `Bienvenido, ${data.usuario}. Sesión de proveedor para el almacén ${data.almacen_id}.`,
        "success",
        "Sesión",
      );
    } catch (error) {
      notifyError(error);
    } finally {
      setCreatingProvider(false);
    }
  };

  const createAdmin = async (event) => {
    event.preventDefault();
    if (!adminForm.clave.trim()) {
      notify("Escribe la clave de administrador.", "info", "Datos incompletos");
      return;
    }
    setCreatingAdmin(true);
    try {
      const { data } = await api.createAdminSession(adminForm.clave);
      saveSession(data);
      setAdminForm({ clave: "" });
      notify("Sesión de administrador creada.", "success", "Sesión");
    } catch (error) {
      notifyError(error);
    } finally {
      setCreatingAdmin(false);
    }
  };

  const close = async () => {
    setClosing(true);
    try {
      await closeSession();
      setInfo({ loading: false, data: null, error: null });
    } finally {
      setClosing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">Sesiones</h2>
        <p className="mt-1 text-sm text-slate-500">
          Crea una sesión de cliente, proveedor o administrador. El token se guarda en el
          navegador y se envía como <span className="font-mono text-xs">Authorization: Bearer</span>.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card
          title="Sesión de cliente"
          description="POST /sessions/user"
          actions={<Badge tone="slate">CLIENTE</Badge>}
        >
          <form className="space-y-4" onSubmit={createUser}>
            <Field label="Nombre del usuario" hint="Entre 1 y 120 caracteres.">
              <Input
                value={userForm.nombre}
                onChange={(event) => setUserForm({ nombre: event.target.value })}
                placeholder="Ana"
                maxLength={120}
                autoComplete="off"
              />
            </Field>
            <Button type="submit" icon="key" loading={creatingUser} className="w-full">
              Iniciar sesión de cliente
            </Button>
          </form>
          <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
            Permisos: lista de compras, búsqueda, carrito y descuentos. Sin acceso a
            administración.
          </div>
        </Card>

        <Card
          title="Sesión de proveedor"
          description="POST /sessions/provider"
          actions={<Badge tone="dark">PROVEEDOR</Badge>}
        >
          <form className="space-y-4" onSubmit={createProvider}>
            <Field
              label="Nombre del proveedor"
              hint="Debe haber sido creado por un administrador y estar activo."
            >
              <Input
                value={providerForm.nombre}
                onChange={(event) => setProviderForm({ nombre: event.target.value })}
                placeholder="Distribuidora Norte"
                maxLength={120}
                autoComplete="off"
              />
            </Field>
            <Button
              type="submit"
              variant="dark"
              icon="warehouse"
              loading={creatingProvider}
              className="w-full"
            >
              Iniciar sesión de proveedor
            </Button>
          </form>
          <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
            Permisos: inventario del almacén asignado, precios, altas, bajas e importación CSV.
            Sin carrito, búsquedas ni gestión de usuarios.
          </div>
        </Card>

        <Card
          title="Sesión de administrador"
          description="POST /sessions/admin"
          actions={<Badge tone="dark">ADMIN</Badge>}
        >
          <form className="space-y-4" onSubmit={createAdmin}>
            <Field label="Clave administrativa" hint="Es la variable ADMIN_CLAVE del backend.">
              <Input
                type="password"
                value={adminForm.clave}
                onChange={(event) => setAdminForm({ clave: event.target.value })}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </Field>
            <Button
              type="submit"
              variant="dark"
              icon="shield"
              loading={creatingAdmin}
              className="w-full"
            >
              Iniciar sesión de administrador
            </Button>
          </form>
          <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
            Permisos adicionales: alta/baja de productos, edición de precios, importación
            CSV y reconciliación del comparador.
          </div>
        </Card>
      </div>

      <Card
        title="Sesión actual"
        description={session ? `GET /sessions/${session.session_id.slice(0, 12)}…` : "GET /sessions/{token}"}
        actions={
          session && (
            <>
              <Button size="sm" variant="secondary" icon="refresh" onClick={refresh} loading={info.loading}>
                Actualizar
              </Button>
              <Button size="sm" variant="dangerSoft" icon="x" onClick={close} loading={closing}>
                Cerrar sesión
              </Button>
            </>
          )
        }
      >
        {!session ? (
          <EmptyState
            icon="key"
            title="No hay una sesión activa"
            description="Usa cualquiera de los formularios anteriores para obtener un token e iniciar a consumir los endpoints protegidos."
          />
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <span className="grid h-9 w-9 place-items-center rounded-md bg-slate-100 text-slate-500">
                <Icon name="key" size={18} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Token de sesión
                </p>
                <p className="truncate font-mono text-sm text-slate-700">{session.session_id}</p>
              </div>
              <CopyButton value={session.session_id} label="Copiar" />
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Usuario
                </p>
                <p className="mt-1 truncate text-sm font-semibold text-slate-800">
                  {info.data?.usuario ?? session.usuario}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Rol
                </p>
                <p className="mt-1">
                  <Badge tone={session.rol === "ADMIN" ? "dark" : "slate"}>
                    {info.data?.rol ?? session.rol}
                  </Badge>
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Almacén asignado
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-800">
                  {info.data?.almacen_id ?? session.almacen_id ?? "—"}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Token activo hasta
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-800">
                  {info.error ? "Expirado o inválido" : "TTL del backend (1 h por defecto)"}
                </p>
              </div>
            </div>

            {(info.data?.descripcion_rol || session.descripcion_rol) && (
              <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 text-xs leading-relaxed text-slate-600">
                <p className="font-semibold text-slate-800">Alcance del rol</p>
                <p className="mt-1">{info.data?.descripcion_rol || session.descripcion_rol}</p>
              </div>
            )}

            {Array.isArray(info.data?.permisos) && (
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-slate-800">Permisos efectivos</p>
                  <Badge tone="slate">{info.data.permisos.length}</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {info.data.permisos.map((permiso) => (
                    <Badge key={permiso} tone="slate">
                      <span className="font-mono">{permiso}</span>
                    </Badge>
                  ))}
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  icon="shield"
                  className="mt-3"
                  onClick={() => onNavigate("roles")}
                >
                  Ver catálogo de roles
                </Button>
              </div>
            )}

            {info.error && (
              <Alert tone="error" title="No se pudo consultar el estado de la sesión">
                {errorText(info.error)}
              </Alert>
            )}

            {info.loading && !info.data ? (
              <div className="flex items-center gap-2 py-4 text-sm text-slate-500">
                <Spinner /> Consultando estado…
              </div>
            ) : info.data ? (
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-800">
                      Lista de compras
                    </p>
                    <Badge tone="slate">{info.data.lista?.length || 0}</Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {(info.data.lista || []).length === 0 ? (
                      <p className="text-xs text-slate-400">La lista está vacía.</p>
                    ) : (
                      info.data.lista.map((name) => (
                        <Badge key={name} tone="slate">
                          {name}
                        </Badge>
                      ))
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    icon="list"
                    className="mt-3"
                    onClick={() => onNavigate("lista")}
                  >
                    Gestionar lista
                  </Button>
                </div>

                <div className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-800">Carrito</p>
                    <Badge tone="slate">{info.data.carrito?.productos?.length || 0} ítems</Badge>
                  </div>
                  <div className="mt-3 space-y-1.5 text-xs text-slate-500">
                    <div className="flex justify-between">
                      <span>Subtotal</span>
                      <Money value={info.data.carrito?.subtotal} />
                    </div>
                    <div className="flex justify-between">
                      <span>Descuento</span>
                      <span className="font-medium text-slate-700">
                        {info.data.carrito?.descuento || "sin"}
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-slate-100 pt-1.5 text-sm font-semibold text-slate-800">
                      <span>Total</span>
                      <Money value={info.data.carrito?.total} />
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    icon="cart"
                    className="mt-3"
                    onClick={() => onNavigate("carrito")}
                  >
                    Abrir carrito
                  </Button>
                </div>
              </div>
            ) : null}

            <JsonBlock data={info.data} label="GET /sessions/{token} · respuesta" />
          </div>
        )}
      </Card>
    </div>
  );
}
