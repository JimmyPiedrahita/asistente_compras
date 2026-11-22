import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, errorText } from "../api";

const SESSION_KEY = "asistente_compras_session";
const AppContext = createContext(null);

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
  const timers = useRef(new Map());
  const validando = useRef(false);

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
      const timer = setTimeout(() => dismissToast(id), type === "error" ? 7000 : 4000);
      timers.current.set(id, timer);
    },
    [dismissToast],
  );

  const notifyError = useCallback(
    (error) => {
      const status = error?.status;
      if (status === 401) {
        saveSession(null);
        notify("Credenciales incorrectas o sesión expirada.", "error", "Sesión");
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

  const saveSession = useCallback((value) => {
    setSession(value);
    if (value) localStorage.setItem(SESSION_KEY, JSON.stringify(value));
    else localStorage.removeItem(SESSION_KEY);
  }, []);

  useEffect(() => {
    const pendientes = timers.current;
    return () => {
      pendientes.forEach((timer) => clearTimeout(timer));
      pendientes.clear();
    };
  }, []);

  useEffect(() => {
    if (!session?.session_id || validando.current) return;
    validando.current = true;
    let cancelado = false;
    (async () => {
      try {
        const actual = await api.me(session.session_id);
        if (!cancelado && actual) saveSession(actual);
      } catch (error) {
        if (!cancelado && error?.status === 401) saveSession(null);
      } finally {
        validando.current = false;
      }
    })();
    return () => {
      cancelado = true;
    };
  }, [saveSession, session?.session_id]);

  const login = useCallback(
    async (email, password) => {
      const nueva = await api.login(email, password);
      saveSession(nueva);
      notify(`Bienvenido, ${nueva.usuario}.`, "success", "Sesión iniciada");
      return nueva;
    },
    [notify, saveSession],
  );

  const register = useCallback(
    async (payload) => {
      const nueva = await api.register(payload);
      saveSession(nueva);
      notify("Tu cuenta fue creada correctamente.", "success", "Registro");
      return nueva;
    },
    [notify, saveSession],
  );

  const logout = useCallback(async () => {
    const actual = session;
    saveSession(null);
    if (!actual?.session_id) return;
    try {
      await api.logout(actual.session_id);
    } catch {
      /* la sesión local ya se cerró */
    }
  }, [saveSession, session]);

  const value = useMemo(
    () => ({
      session,
      token: session?.session_id || "",
      isCliente: session?.rol === "CLIENTE",
      isAdminAlmacen: session?.rol === "ADMINISTRADOR_ALMACEN",
      isAdminApp: session?.rol === "ADMINISTRADOR_APP",
      saveSession,
      login,
      register,
      logout,
      toasts,
      notify,
      notifyError,
      dismissToast,
    }),
    [
      session,
      saveSession,
      login,
      register,
      logout,
      toasts,
      notify,
      notifyError,
      dismissToast,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp debe usarse dentro de AppProvider");
  return context;
}
