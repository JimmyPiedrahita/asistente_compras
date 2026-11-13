import { useCallback, useEffect, useMemo, useState } from "react";
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
  Select,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";

const ROLE_ORDER = ["INVITADO", "CLIENTE", "PROVEEDOR", "ADMIN"];

const ROLE_TONES = {
  INVITADO: "slate",
  CLIENTE: "slate",
  PROVEEDOR: "dark",
  ADMIN: "dark",
};

function RoleCard({ rol, descripciones }) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-slate-900">{rol.rol}</h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-500">{rol.descripcion}</p>
        </div>
        <Badge tone={ROLE_TONES[rol.rol] || "slate"}>{rol.permisos.length} permisos</Badge>
      </div>
      <ul className="mt-4 space-y-2 border-t border-slate-100 pt-4">
        {rol.permisos.map((permiso) => (
          <li key={permiso} className="flex gap-2 text-xs">
            <Icon name="check" size={13} className="mt-0.5 shrink-0 text-slate-400" />
            <span>
              <span className="font-mono font-medium text-slate-700">{permiso}</span>
              {descripciones[permiso] && (
                <span className="mt-0.5 block leading-relaxed text-slate-500">
                  {descripciones[permiso]}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function UserRow({ usuario, warehouses, busy, onSave, onToggle }) {
  const [draft, setDraft] = useState({
    rol: usuario.rol,
    almacen_id: usuario.almacen_id ?? "",
  });

  useEffect(() => {
    setDraft({ rol: usuario.rol, almacen_id: usuario.almacen_id ?? "" });
  }, [usuario]);

  const dirty =
    draft.rol !== usuario.rol || String(draft.almacen_id ?? "") !== String(usuario.almacen_id ?? "");
  const needsWarehouse = draft.rol === "PROVEEDOR";

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">{usuario.nombre}</p>
          <p className="mt-0.5 font-mono text-[11px] text-slate-400">{usuario.usuario_id}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={ROLE_TONES[usuario.rol] || "slate"}>{usuario.rol}</Badge>
          <Badge tone={usuario.activo ? "emerald" : "rose"}>
            {usuario.activo ? "activo" : "inactivo"}
          </Badge>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-end gap-2">
        <Field label="Rol" className="w-full sm:w-40">
          <Select
            value={draft.rol}
            onChange={(event) => setDraft({ ...draft, rol: event.target.value })}
            disabled={busy || usuario.rol === "ADMIN"}
          >
            <option value="CLIENTE">CLIENTE</option>
            <option value="PROVEEDOR">PROVEEDOR</option>
          </Select>
        </Field>
        <Field label="Almacén" className="w-full sm:w-56">
          <Select
            value={needsWarehouse ? String(draft.almacen_id ?? "") : ""}
            onChange={(event) =>
              setDraft({
                ...draft,
                almacen_id: event.target.value === "" ? null : Number(event.target.value),
              })
            }
            disabled={busy || !needsWarehouse}
          >
            <option value="">— sin almacén —</option>
            {warehouses.map((warehouse) => (
              <option key={warehouse.id} value={warehouse.id}>
                {warehouse.name} (ID {warehouse.id})
              </option>
            ))}
          </Select>
        </Field>
        <Button
          size="sm"
          icon="check"
          loading={busy}
          disabled={!dirty || (needsWarehouse && draft.almacen_id === null)}
          onClick={() =>
            onSave(usuario, {
              rol: draft.rol,
              almacen_id: draft.almacen_id === "" ? null : draft.almacen_id,
            })
          }
        >
          Guardar
        </Button>
        <Button
          size="sm"
          variant="secondary"
          icon={usuario.activo ? "x" : "check"}
          disabled={busy}
          onClick={() => onToggle(usuario)}
        >
          {usuario.activo ? "Desactivar" : "Activar"}
        </Button>
      </div>
    </div>
  );
}

export default function RolesPage({ onNavigate }) {
  const { session, token, can, notify, notifyError } = useApp();
  const [catalog, setCatalog] = useState({ loading: true, data: null, error: null });
  const [users, setUsers] = useState({ loading: false, items: [], error: null });
  const [warehouses, setWarehouses] = useState([]);
  const [providerForm, setProviderForm] = useState({ nombre: "", almacen_id: "" });
  const [creating, setCreating] = useState(false);
  const [busyUser, setBusyUser] = useState(null);

  const gestionaUsuarios = Boolean(session && can("gestionar_usuarios"));

  const loadCatalog = useCallback(async () => {
    setCatalog((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.listRoles();
      setCatalog({ loading: false, data, error: null });
    } catch (error) {
      setCatalog({ loading: false, data: null, error });
    }
  }, []);

  const loadUsers = useCallback(async () => {
    if (!token || !gestionaUsuarios) return;
    setUsers((current) => ({ ...current, loading: true, error: null }));
    try {
      const [usuarios, almacenes] = await Promise.all([
        api.listUsers(token),
        api.listWarehouses(),
      ]);
      setUsers({ loading: false, items: usuarios.data || [], error: null });
      setWarehouses(almacenes.data || []);
    } catch (error) {
      setUsers({ loading: false, items: [], error });
    }
  }, [gestionaUsuarios, token]);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const roles = useMemo(() => {
    const items = [...(catalog.data?.roles || [])];
    items.sort(
      (a, b) => ROLE_ORDER.indexOf(a.rol) - ROLE_ORDER.indexOf(b.rol),
    );
    return items;
  }, [catalog.data]);

  const descripciones = useMemo(
    () =>
      Object.fromEntries(
        (catalog.data?.permisos || []).map((permiso) => [
          permiso.codigo,
          permiso.descripcion,
        ]),
      ),
    [catalog.data],
  );

  const createProvider = async (event) => {
    event.preventDefault();
    if (!providerForm.nombre.trim() || !providerForm.almacen_id) {
      notify("Indica el nombre y el almacén del proveedor.", "info", "Datos incompletos");
      return;
    }
    setCreating(true);
    try {
      const { data } = await api.createProvider(token, {
        nombre: providerForm.nombre.trim(),
        almacenId: providerForm.almacen_id,
      });
      setProviderForm({ nombre: "", almacen_id: "" });
      notify(
        `Proveedor ${data.nombre} creado para el almacén ${data.almacen_id}.`,
        "success",
        "Proveedor",
      );
      loadUsers();
    } catch (error) {
      notifyError(error);
    } finally {
      setCreating(false);
    }
  };

  const saveUser = async (usuario, payload) => {
    setBusyUser(usuario.usuario_id);
    try {
      await api.updateUser(token, usuario.usuario_id, payload);
      notify(`Usuario ${usuario.nombre} actualizado.`, "success", "Usuarios");
      loadUsers();
    } catch (error) {
      notifyError(error);
    } finally {
      setBusyUser(null);
    }
  };

  const toggleUser = async (usuario) => {
    setBusyUser(usuario.usuario_id);
    try {
      await api.updateUser(token, usuario.usuario_id, { activo: !usuario.activo });
      notify(
        `Usuario ${usuario.nombre} ${usuario.activo ? "desactivado" : "activado"}.`,
        "success",
        "Usuarios",
      );
      loadUsers();
    } catch (error) {
      notifyError(error);
    } finally {
      setBusyUser(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Roles y permisos
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Catálogo persistido en MongoDB. Cada sesión recibe solo los permisos de su rol y la
            interfaz oculta las acciones que no puede ejecutar.
          </p>
        </div>
        <Button size="sm" variant="secondary" icon="refresh" onClick={loadCatalog} loading={catalog.loading}>
          Actualizar catálogo
        </Button>
      </div>

      {catalog.error ? (
        <Alert tone="error" title="No se pudo cargar el catálogo">
          {errorText(catalog.error)}
        </Alert>
      ) : catalog.loading && !catalog.data ? (
        <Card>
          <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
            <Spinner /> Consultando GET /roles…
          </div>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
          {roles.map((rol) => (
            <RoleCard key={rol.rol} rol={rol} descripciones={descripciones} />
          ))}
        </div>
      )}

      {!session ? (
        <Card title="Gestión de usuarios" description="Requiere una sesión ADMIN.">
          <EmptyState
            icon="key"
            title="Inicia sesión como administrador"
            description="El catálogo de roles es público, pero crear proveedores y cambiar usuarios requiere el permiso gestionar_usuarios."
            action={
              <Button icon="key" onClick={() => onNavigate?.("sesion")}>
                Ir a sesiones
              </Button>
            }
          />
        </Card>
      ) : !gestionaUsuarios ? (
        <Card title="Gestión de usuarios" description="Solo el rol ADMIN puede administrarla.">
          <Alert tone="info" title="Acceso de solo lectura">
            La sesión de {session.usuario} es {session.rol} y no incluye{" "}
            <span className="font-mono">gestionar_usuarios</span>. Puedes consultar el catálogo,
            pero no crear ni modificar usuarios.
          </Alert>
        </Card>
      ) : (
        <div className="space-y-6">
          <Card
            title="Nuevo proveedor"
            description="POST /sessions/{token}/users/providers"
            actions={<Badge tone="dark">PROVEEDOR</Badge>}
          >
            <form className="grid gap-4 sm:grid-cols-[1fr_16rem_auto]" onSubmit={createProvider}>
              <Field label="Nombre del proveedor">
                <Input
                  value={providerForm.nombre}
                  onChange={(event) =>
                    setProviderForm({ ...providerForm, nombre: event.target.value })
                  }
                  placeholder="Distribuidora Norte"
                  maxLength={120}
                  required
                />
              </Field>
              <Field label="Almacén asignado">
                <Select
                  value={providerForm.almacen_id}
                  onChange={(event) =>
                    setProviderForm({ ...providerForm, almacen_id: event.target.value })
                  }
                  required
                >
                  <option value="">Selecciona un almacén</option>
                  {warehouses.map((warehouse) => (
                    <option key={warehouse.id} value={warehouse.id}>
                      {warehouse.name} (ID {warehouse.id})
                    </option>
                  ))}
                </Select>
              </Field>
              <div className="flex items-end">
                <Button type="submit" icon="plus" loading={creating} className="w-full">
                  Crear proveedor
                </Button>
              </div>
            </form>
            <p className="mt-3 text-xs leading-relaxed text-slate-500">
              El proveedor inicia sesión con su nombre en{" "}
              <span className="font-mono">POST /sessions/provider</span> y solo puede operar el
              almacén asignado.
            </p>
          </Card>

          <Card
            title="Usuarios"
            description="GET /sessions/{token}/users · activar, desactivar y reasignar almacén."
            actions={
              <Button size="sm" variant="secondary" icon="refresh" onClick={loadUsers} loading={users.loading}>
                Recargar
              </Button>
            }
          >
            {users.error ? (
              <Alert tone="error" title="No se pudieron cargar los usuarios">
                {errorText(users.error)}
              </Alert>
            ) : users.loading && users.items.length === 0 ? (
              <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
                <Spinner /> Consultando usuarios…
              </div>
            ) : users.items.length === 0 ? (
              <EmptyState
                icon="shield"
                title="Sin usuarios persistidos"
                description="Crea el primer proveedor o inicia sesión como cliente para registrar un usuario CLIENTE."
              />
            ) : (
              <div className="space-y-3">
                {users.items.map((usuario) => (
                  <UserRow
                    key={usuario.usuario_id}
                    usuario={usuario}
                    warehouses={warehouses}
                    busy={busyUser === usuario.usuario_id}
                    onSave={saveUser}
                    onToggle={toggleUser}
                  />
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
