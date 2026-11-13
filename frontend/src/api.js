const BASE = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/+$/, "");

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
      return `${error.message}: ${error.details
        .slice(0, 3)
        .map((item) => item?.msg || item?.message || String(item))
        .join(" · ")}`;
    }
    if (typeof error.details === "string" && error.details) {
      return `${error.message}: ${error.details}`;
    }
    return error.message;
  }
  return error.message || "Error inesperado";
}

async function request(path, { method = "GET", body, token, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const init = { method, headers, signal };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${BASE}${path}`, init);
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new ApiError("No se pudo conectar con el servidor. Verifica que la API esté activa.");
  }

  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(
      payload?.error || payload?.detail || `Error HTTP ${response.status}`,
      response.status,
      payload,
    );
  }
  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

const q = (value) => encodeURIComponent(value);

export const api = {
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: { email, password } }),
  register: (payload) => request("/auth/register", { method: "POST", body: payload }),
  me: (token) => request("/auth/me", { token }),
  logout: (token) => request("/auth/session", { method: "DELETE", token }),

  getShoppingList: (token) => request("/shopping-list", { token }),
  addShoppingListItem: (token, nombre) =>
    request("/shopping-list", { method: "POST", token, body: { nombre } }),
  removeShoppingListItem: (token, nombre) =>
    request(`/shopping-list/${q(nombre)}`, { method: "DELETE", token }),
  search: (token, modo) => request("/search", { method: "POST", token, body: { modo } }),

  getCart: (token) => request("/cart", { token }),
  addCartItem: (token, payload) =>
    request("/cart/items", { method: "POST", token, body: payload }),
  updateCartItem: (token, itemId, cantidad) =>
    request(`/cart/items/${q(itemId)}`, { method: "PATCH", token, body: { cantidad } }),
  removeCartItem: (token, itemId) =>
    request(`/cart/items/${q(itemId)}`, { method: "DELETE", token }),
  clearCart: (token) => request("/cart", { method: "DELETE", token }),
  applyCoupon: (token, codigo) =>
    request("/cart/coupons", { method: "POST", token, body: { codigo } }),
  removeCoupon: (token, codigo) =>
    request(`/cart/coupons/${q(codigo)}`, { method: "DELETE", token }),
  checkout: (token, payload) => request("/checkout", { method: "POST", token, body: payload }),

  listProducts: (token) => request("/admin-almacen/productos", { token }),
  createProduct: (token, payload) =>
    request("/admin-almacen/productos", { method: "POST", token, body: payload }),
  updateProduct: (token, productId, payload) =>
    request(`/admin-almacen/productos/${q(productId)}`, {
      method: "PATCH",
      token,
      body: payload,
    }),
  deleteProduct: (token, productId) =>
    request(`/admin-almacen/productos/${q(productId)}`, { method: "DELETE", token }),
  importCsv: (token, contenido, nombre_archivo) =>
    request("/admin-almacen/productos/importar", {
      method: "POST",
      token,
      body: { contenido, nombre_archivo },
    }),
  listCoupons: (token) => request("/admin-almacen/cupones", { token }),
  createCoupon: (token, payload) =>
    request("/admin-almacen/cupones", { method: "POST", token, body: payload }),
  deleteCoupon: (token, couponId) =>
    request(`/admin-almacen/cupones/${q(couponId)}`, { method: "DELETE", token }),
  listPurchases: (token) => request("/admin-almacen/compras", { token }),
  stats: (token) => request("/admin-almacen/estadisticas", { token }),

  listWarehouses: (token) => request("/admin-app/almacenes", { token }),
  createWarehouse: (token, nombre) =>
    request("/admin-app/almacenes", { method: "POST", token, body: { nombre } }),
  listAdmins: (token) => request("/admin-app/administradores", { token }),
  createAdmin: (token, payload) =>
    request("/admin-app/administradores", { method: "POST", token, body: payload }),
  updateAdminCredentials: (token, usuarioId, payload) =>
    request(`/admin-app/administradores/${q(usuarioId)}/credenciales`, {
      method: "PATCH",
      token,
      body: payload,
    }),
};
