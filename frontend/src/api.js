const STORAGE_KEY = "asistente_compras_api_base";
const DEFAULT_API_BASE = (
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

export function getApiBase() {
  if (typeof window === "undefined") return DEFAULT_API_BASE;
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_API_BASE;
}

export function normalizeApiBase(raw) {
  let value = String(raw || "").trim();
  if (!value) return DEFAULT_API_BASE;
  value = value.replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(value)) {
    value = `http://${value}`;
  }
  if (!/\/(api\/v1|api)$/i.test(value)) {
    value = `${value}/api/v1`;
  }
  return value;
}

export function saveApiBase(raw) {
  const value = normalizeApiBase(raw);
  localStorage.setItem(STORAGE_KEY, value);
  return value;
}

export function docsUrl() {
  return `${getApiBase().replace(/\/api(\/v1)?$/, "")}/docs`;
}

export class ApiError extends Error {
  constructor(message, status = 0, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
    this.details = payload?.detalles ?? payload?.detail ?? null;
  }
}

export function errorText(error) {
  if (!error) return "";
  if (error instanceof ApiError) {
    if (Array.isArray(error.details)) {
      const items = error.details
        .slice(0, 3)
        .map((item) => item?.msg || item?.message || String(item))
        .join(" · ");
      return items ? `${error.message}: ${items}` : error.message;
    }
    if (typeof error.details === "string" && error.details) {
      return `${error.message}: ${error.details}`;
    }
  }
  return error.message || "Error inesperado";
}

function buildUrl(path, query) {
  const base = getApiBase();
  const params = new URLSearchParams();
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const qs = params.toString();
  return `${base}${path}${qs ? `?${qs}` : ""}`;
}

async function request(path, options = {}) {
  const {
    method = "GET",
    body,
    token,
    query,
    responseType = "json",
    signal,
  } = options;

  const headers = {
    Accept: responseType === "blob" ? "*/*" : "application/json",
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const init = { method, headers, signal };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(buildUrl(path, query), init);
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new ApiError(
      `No se pudo conectar con ${getApiBase()}. Verifica que la API esté activa y que CORS permita este origen.`,
      0,
    );
  }

  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      /* respuesta no JSON */
    }
    throw new ApiError(
      payload?.error || payload?.detail || `Error HTTP ${response.status}`,
      response.status,
      payload,
    );
  }

  if (responseType === "blob") {
    const blob = await response.blob();
    return { data: blob, headers: response.headers, status: response.status };
  }

  if (response.status === 204) {
    return { data: null, headers: response.headers, status: response.status };
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  return { data, headers: response.headers, status: response.status };
}

async function download(path, token, fallbackName) {
  const { data, headers } = await request(path, { token, responseType: "blob" });
  const disposition = headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || fallbackName;
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return filename;
}

export const api = {
  // Salud
  health: () => request("/health"),
  healthLive: () => request("/health/live"),
  healthReady: () => request("/health/ready"),

  // Almacenes
  listWarehouses: () => request("/warehouses"),
  listProducts: (warehouseId, { limit = 100, offset = 0 } = {}) =>
    request(`/warehouses/${encodeURIComponent(warehouseId)}/products`, {
      query: { limit, offset },
    }),

  // Sesiones
  createUserSession: (nombre) =>
    request("/sessions/user", { method: "POST", body: { nombre } }),
  createProviderSession: (nombre) =>
    request("/sessions/provider", { method: "POST", body: { nombre } }),
  createAdminSession: (clave) =>
    request("/sessions/admin", { method: "POST", body: { clave } }),
  getSession: (token) => request(`/sessions/${encodeURIComponent(token)}`, { token }),
  deleteSession: (token) =>
    request(`/sessions/${encodeURIComponent(token)}`, { method: "DELETE", token }),

  // Seguridad: catálogo de roles y gestión de usuarios
  listRoles: () => request("/roles"),
  getRole: (rol) => request(`/roles/${encodeURIComponent(rol)}`),
  listUsers: (token) =>
    request(`/sessions/${encodeURIComponent(token)}/users`, { token }),
  createProvider: (token, { nombre, almacenId }) =>
    request(`/sessions/${encodeURIComponent(token)}/users/providers`, {
      method: "POST",
      token,
      body: { nombre, almacen_id: Number(almacenId) },
    }),
  updateUser: (token, usuarioId, payload) =>
    request(
      `/sessions/${encodeURIComponent(token)}/users/${encodeURIComponent(usuarioId)}`,
      { method: "PATCH", token, body: payload },
    ),

  // Lista de compras
  getShoppingList: (token) =>
    request(`/sessions/${encodeURIComponent(token)}/shopping-list`, { token }),
  addShoppingListItem: (token, nombre) =>
    request(`/sessions/${encodeURIComponent(token)}/shopping-list`, {
      method: "POST",
      token,
      body: { nombre },
    }),
  removeShoppingListItem: (token, nombre) =>
    request(
      `/sessions/${encodeURIComponent(token)}/shopping-list/${encodeURIComponent(nombre)}`,
      { method: "DELETE", token },
    ),

  // Búsqueda
  search: (token, { modo = "mejor_precio", limit = 100, offset = 0 } = {}) =>
    request(`/sessions/${encodeURIComponent(token)}/search`, {
      method: "POST",
      token,
      body: { modo, limit, offset },
    }),

  // Carrito
  getCart: (token) =>
    request(`/sessions/${encodeURIComponent(token)}/cart`, { token }),
  addCartItem: (token, almacenId, productoId) =>
    request(`/sessions/${encodeURIComponent(token)}/cart/items`, {
      method: "POST",
      token,
      body: { almacen_id: Number(almacenId), producto_id: productoId },
    }),
  removeCartItem: (token, indice) =>
    request(
      `/sessions/${encodeURIComponent(token)}/cart/items/${encodeURIComponent(indice)}`,
      { method: "DELETE", token },
    ),
  clearCart: (token) =>
    request(`/sessions/${encodeURIComponent(token)}/cart`, {
      method: "DELETE",
      token,
    }),
  applyDiscount: (token, tipo, valor) =>
    request(`/sessions/${encodeURIComponent(token)}/cart/discount`, {
      method: "POST",
      token,
      body: tipo === "sin" ? { tipo } : { tipo, valor: Number(valor) },
    }),

  // Administración
  createProduct: (token, almacenId, payload) =>
    request(
      `/sessions/${encodeURIComponent(token)}/admin/warehouses/${encodeURIComponent(almacenId)}/products`,
      { method: "POST", token, body: payload },
    ),
  updatePrice: (token, almacenId, productoId, precio) =>
    request(
      `/sessions/${encodeURIComponent(token)}/admin/warehouses/${encodeURIComponent(almacenId)}/products`,
      {
        method: "PATCH",
        token,
        body: { producto_id: productoId, precio: Number(precio) },
      },
    ),
  deleteProduct: (token, almacenId, productoId) =>
    request(
      `/sessions/${encodeURIComponent(token)}/admin/warehouses/${encodeURIComponent(almacenId)}/products/${encodeURIComponent(productoId)}`,
      { method: "DELETE", token },
    ),
  importCsv: (token, contenido) =>
    request(`/sessions/${encodeURIComponent(token)}/admin/csv`, {
      method: "POST",
      token,
      body: { contenido },
    }),
  comparadorStatus: (token) =>
    request(`/sessions/${encodeURIComponent(token)}/admin/comparador/status`, { token }),
  reconcileComparador: (token) =>
    request(`/sessions/${encodeURIComponent(token)}/admin/comparador/reconciliar`, {
      method: "POST",
      token,
    }),
  reload: (token) =>
    request(`/sessions/${encodeURIComponent(token)}/admin/reload`, {
      method: "POST",
      token,
    }),

  // Exportación
  exportShoppingList: (token) =>
    download(
      `/sessions/${encodeURIComponent(token)}/export/shopping-list`,
      token,
      "lista_compra.csv",
    ),
  exportCart: (token) =>
    download(`/sessions/${encodeURIComponent(token)}/export/cart`, token, "carrito.csv"),
};

export const ENDPOINTS = [
  { method: "GET", path: "/health", group: "Salud" },
  { method: "GET", path: "/health/live", group: "Salud" },
  { method: "GET", path: "/health/ready", group: "Salud" },
  { method: "GET", path: "/warehouses", group: "Almacenes" },
  { method: "GET", path: "/warehouses/{id}/products", group: "Almacenes" },
  { method: "POST", path: "/sessions/user", group: "Sesiones" },
  { method: "POST", path: "/sessions/provider", group: "Sesiones" },
  { method: "POST", path: "/sessions/admin", group: "Sesiones" },
  { method: "GET", path: "/sessions/{token}", group: "Sesiones" },
  { method: "DELETE", path: "/sessions/{token}", group: "Sesiones" },
  { method: "GET", path: "/roles", group: "Seguridad" },
  { method: "GET", path: "/roles/{rol}", group: "Seguridad" },
  { method: "GET", path: "/sessions/{token}/users", group: "Seguridad" },
  { method: "POST", path: "/sessions/{token}/users/providers", group: "Seguridad" },
  { method: "PATCH", path: "/sessions/{token}/users/{usuario_id}", group: "Seguridad" },
  { method: "GET", path: "/sessions/{token}/shopping-list", group: "Lista" },
  { method: "POST", path: "/sessions/{token}/shopping-list", group: "Lista" },
  {
    method: "DELETE",
    path: "/sessions/{token}/shopping-list/{nombre}",
    group: "Lista",
  },
  { method: "POST", path: "/sessions/{token}/search", group: "Búsqueda" },
  { method: "GET", path: "/sessions/{token}/cart", group: "Carrito" },
  { method: "POST", path: "/sessions/{token}/cart/items", group: "Carrito" },
  {
    method: "DELETE",
    path: "/sessions/{token}/cart/items/{indice}",
    group: "Carrito",
  },
  { method: "DELETE", path: "/sessions/{token}/cart", group: "Carrito" },
  { method: "POST", path: "/sessions/{token}/cart/discount", group: "Carrito" },
  {
    method: "POST",
    path: "/sessions/{token}/admin/warehouses/{id}/products",
    group: "Administración",
  },
  {
    method: "PATCH",
    path: "/sessions/{token}/admin/warehouses/{id}/products",
    group: "Administración",
  },
  {
    method: "DELETE",
    path: "/sessions/{token}/admin/warehouses/{id}/products/{producto_id}",
    group: "Administración",
  },
  { method: "POST", path: "/sessions/{token}/admin/csv", group: "Administración" },
  {
    method: "GET",
    path: "/sessions/{token}/admin/comparador/status",
    group: "Administración",
  },
  {
    method: "POST",
    path: "/sessions/{token}/admin/comparador/reconciliar",
    group: "Administración",
  },
  { method: "POST", path: "/sessions/{token}/admin/reload", group: "Administración" },
  {
    method: "GET",
    path: "/sessions/{token}/export/shopping-list",
    group: "Exportación",
  },
  { method: "GET", path: "/sessions/{token}/export/cart", group: "Exportación" },
];
