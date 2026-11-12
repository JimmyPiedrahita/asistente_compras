import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, errorText, getApiBase, saveApiBase } from "../api";

const SESSION_KEY = "asistente_compras_session";
const AppContext = createContext(null);

// Respaldo local únicamente para sesiones antiguas creadas antes de que la
// API devolviera los permisos. La fuente de verdad sigue siendo el backend.
const ROLE_FALLBACK = {
  INVITADO: ["ver_menu"],
  CLIENTE: [
    "ver_menu",
    "crear_lista",
    "agregar_producto",
    "eliminar_producto",
    "comparar",
    "exportar",
    "aplicar_descuento",
  ],
  PROVEEDOR: [
    "ver_menu",
    "ver_inventario",
    "gestionar_inventario",
    "editar_precio",
    "importar_csv",
  ],
  ADMIN: [
    "ver_menu",
    "crear_lista",
    "agregar_producto",
    "eliminar_producto",
    "comparar",
    "exportar",
    "aplicar_descuento",
    "login_admin",
    "ver_inventario",
    "gestionar_inventario",
    "editar_precio",
    "importar_csv",
    "gestionar_almacenes",
    "gestionar_comparador",
    "gestionar_usuarios",
  ],
};

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AppProvider({ children }) {
  const [session, setSession] = useState(loadSession);
  const [toasts, setToasts] = useState([]);
  const [apiBase, setApiBaseState] = useState(getApiBase);
  const timers = useRef(new Map());
  const refreshingSession = useRef(false);

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const notify = useCallback(
    (message, type = "success", title) => {
      const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      setToasts((current) => [
        ...current.slice(-3),
        { id, message, type, title: title || (type === "error" ? "Error" : "Listo") },
      ]);
      const timer = setTimeout(() => dismissToast(id), type === "error" ? 7000 : 4200);
      timers.current.set(id, timer);
    },
    [dismissToast],
  );

  const notifyError = useCallback(
    (error) => {
      const status = error?.status;
      if (status === 401) {
        notify(
          `${errorText(error)} La sesión puede haber expirado.`,
          "error",
          "Sesión inválida",
        );
        return;
      }
      if (status === 403) {
        notify(errorText(error), "error", "Acción no permitida");
        return;
      }
      notify(errorText(error), "error");
    },
    [notify],
  );

  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach((timer) => clearTimeout(timer));
      pending.clear();
    };
  }, []);

  const saveSession = useCallback((value) => {
    setSession(value);
    if (value) {
      localStorage.setItem(SESSION_KEY, JSON.stringify(value));
    } else {
      localStorage.removeItem(SESSION_KEY);
    }
  }, []);

  // Las sesiones guardadas antes de existir los permisos se actualizan una vez
  // contra GET /sessions/{token}; así la interfaz nunca inventa autorizaciones.
  useEffect(() => {
    if (!session?.session_id || Array.isArray(session.permisos)) return undefined;
    if (refreshingSession.current) return undefined;
    refreshingSession.current = true;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.getSession(session.session_id);
        if (cancelled || !data) return;
        saveSession({
          ...session,
          usuario: data.usuario ?? session.usuario,
          rol: data.rol ?? session.rol,
          permisos: data.permisos || [],
          almacen_id: data.almacen_id ?? null,
          usuario_id: data.usuario_id ?? null,
          descripcion_rol: data.descripcion_rol || "",
        });
      } catch (error) {
        if (error?.status === 401) saveSession(null);
      } finally {
        refreshingSession.current = false;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [saveSession, session]);

  const permissions = useMemo(() => {
    if (!session) return [];
    if (Array.isArray(session.permisos)) return session.permisos;
    return ROLE_FALLBACK[session.rol] || ["ver_menu"];
  }, [session]);

  const can = useCallback(
    (permiso) => {
      if (!session) return false;
      if (!permiso) return true;
      return permissions.includes(permiso);
    },
    [permissions, session],
  );

  const closeSession = useCallback(
    async ({ silent = false } = {}) => {
      const current = session;
      saveSession(null);
      if (!current?.session_id) return;
      try {
        await api.deleteSession(current.session_id);
        if (!silent) notify("Sesión cerrada correctamente.", "success", "Sesión");
      } catch (error) {
        if (!silent) notifyError(error);
      }
    },
    [notify, notifyError, saveSession, session],
  );

  const changeApiBase = useCallback(
    (value) => {
      const normalized = saveApiBase(value);
      setApiBaseState(normalized);
      notify(`API configurada en ${normalized}`, "success", "Configuración");
      return normalized;
    },
    [notify],
  );

  const value = useMemo(
    () => ({
      session,
      token: session?.session_id || "",
      isAdmin: session?.rol === "ADMIN",
      isProvider: session?.rol === "PROVEEDOR",
      isClient: session?.rol === "CLIENTE",
      permissions,
      can,
      saveSession,
      closeSession,
      toasts,
      notify,
      notifyError,
      dismissToast,
      apiBase,
      changeApiBase,
      docs: `${apiBase.replace(/\/api(\/v1)?$/, "")}/docs`,
    }),
    [
      apiBase,
      can,
      changeApiBase,
      closeSession,
      dismissToast,
      notify,
      notifyError,
      permissions,
      saveSession,
      session,
      toasts,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp debe usarse dentro de AppProvider");
  }
  return context;
}
