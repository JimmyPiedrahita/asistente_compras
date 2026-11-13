import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorText } from "../api";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Money,
  NeedPermission,
  NeedSession,
  ProductTypeBadge,
  Select,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";

const SORT_OPTIONS = [
  { value: "precio_asc", label: "Precio más bajo primero" },
  { value: "precio_desc", label: "Precio más alto primero" },
  { value: "nombre", label: "Nombre A-Z" },
  { value: "almacen", label: "Por almacén" },
];

export default function StorePage({ onNavigate }) {
  const { session, token, can, notify, notifyError } = useApp();

  // Fase actual: 1 = crear lista, 2 = ver productos y carrito
  const [phase, setPhase] = useState(1);

  // Lista de compras
  const [lista, setLista] = useState({ loading: false, items: [], error: null });
  const [nombre, setNombre] = useState("");
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState(null);

  // Búsqueda de productos basada en la lista
  const [products, setProducts] = useState({ loading: false, data: null, error: null });
  const [sort, setSort] = useState("precio_asc");

  // Carrito
  const [cart, setCart] = useState({ loading: false, data: null, error: null });
  const [addingToCart, setAddingToCart] = useState(null);
  const [removingFromCart, setRemovingFromCart] = useState(null);

  // Referencia para evitar búsquedas duplicadas
  const initialLoad = useRef(false);

  // Cargar lista de compras
  const loadLista = useCallback(async () => {
    if (!token || !can("crear_lista")) return;
    setLista((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.getShoppingList(token);
      setLista({ loading: false, items: data?.lista || [], error: null });
    } catch (error) {
      setLista({ loading: false, items: [], error });
    }
  }, [can, token]);

  // Cargar carrito
  const loadCart = useCallback(async () => {
    if (!token || !can("agregar_producto")) return;
    setCart((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.getCart(token);
      setCart({ loading: false, data, error: null });
    } catch (error) {
      setCart({ loading: false, data: null, error });
    }
  }, [can, token]);

  // Buscar productos basados en la lista
  const searchProducts = useCallback(async () => {
    if (!token || !can("comparar")) return;
    if (lista.items.length === 0) {
      notify("Agrega al menos un producto a tu lista.", "info", "Lista vacía");
      return;
    }
    setProducts((current) => ({ ...current, loading: true, error: null }));
    try {
      const { data } = await api.search(token, { modo: "mejor_precio", limit: 200, offset: 0 });
      setProducts({ loading: false, data, error: null });
      setPhase(2);
    } catch (error) {
      setProducts({ loading: false, data: null, error });
    }
  }, [can, token, lista.items.length]);

  // Carga inicial
  useEffect(() => {
    if (!token || initialLoad.current) return;
    initialLoad.current = true;
    loadLista();
    loadCart();
  }, [loadLista, loadCart, token]);

  // Si no hay sesión
  if (!session) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Tienda</h2>
          <p className="mt-1 text-sm text-slate-500">Encuentra los mejores precios para tus compras.</p>
        </div>
        <NeedSession />
      </div>
    );
  }

  // Si no tiene permiso
  if (!can("crear_lista")) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Tienda</h2>
          <p className="mt-1 text-sm text-slate-500">La tienda está disponible para cuentas de cliente.</p>
        </div>
        <NeedPermission
          session={session}
          permission="crear_lista"
          title="La tienda no está disponible para tu cuenta"
        />
      </div>
    );
  }

  // Acciones de la lista
  const addToList = async (event) => {
    event.preventDefault();
    const value = nombre.trim();
    if (!value) {
      notify("Escribe el nombre del producto.", "info", "Datos incompletos");
      return;
    }
    setAdding(true);
    try {
      const { data } = await api.addShoppingListItem(token, value);
      const newItems = data?.lista || [];
      setLista({ loading: false, items: newItems, error: null });
      setNombre("");
      notify(`"${value}" se agregó a tu lista.`, "success", "Lista de compras");
      // Si ya estamos en fase 2, actualizar productos
      if (phase === 2) {
        searchProducts();
      }
    } catch (error) {
      notifyError(error);
    } finally {
      setAdding(false);
    }
  };

  const removeFromList = async (item) => {
    setRemoving(item);
    try {
      const { data } = await api.removeShoppingListItem(token, item);
      const newItems = data?.lista || [];
      setLista({ loading: false, items: newItems, error: null });
      notify(`"${item}" se eliminó de tu lista.`, "success", "Lista de compras");
      // Si ya estamos en fase 2, actualizar productos
      if (phase === 2) {
        searchProducts();
      }
    } catch (error) {
      notifyError(error);
    } finally {
      setRemoving(null);
    }
  };

  // Acciones del carrito
  const addToCart = async (row) => {
    const key = `${row.almacen_id}-${row.producto.producto_id}`;
    setAddingToCart(key);
    try {
      await api.addCartItem(token, row.almacen_id, row.producto.producto_id);
      notify(`"${row.producto.nombre}" agregado desde ${row.almacen}.`, "success", "Carrito");
      loadCart();
    } catch (error) {
      notifyError(error);
    } finally {
      setAddingToCart(null);
    }
  };

  const removeFromCart = async (index) => {
    setRemovingFromCart(index);
    try {
      const { data } = await api.removeCartItem(token, index);
      setCart({ loading: false, data, error: null });
      notify("Producto eliminado del carrito.", "success", "Carrito");
    } catch (error) {
      notifyError(error);
    } finally {
      setRemovingFromCart(null);
    }
  };

  // Filtrar y ordenar productos
  const rows = products.data?.resultados || [];
  const sortedRows = [...rows].sort((a, b) => {
    switch (sort) {
      case "precio_asc":
        return (a.producto.precio_final || 0) - (b.producto.precio_final || 0);
      case "precio_desc":
        return (b.producto.precio_final || 0) - (a.producto.precio_final || 0);
      case "nombre":
        return (a.producto.nombre || "").localeCompare(b.producto.nombre || "");
      case "almacen":
        return (a.almacen || "").localeCompare(b.almacen || "");
      default:
        return 0;
    }
  });

  // Agrupar por almacén
  const groupedByWarehouse = {};
  sortedRows.forEach((row) => {
    const key = row.almacen;
    if (!groupedByWarehouse[key]) {
      groupedByWarehouse[key] = { id: row.almacen_id, nombre: row.almacen, productos: [] };
    }
    groupedByWarehouse[key].productos.push(row);
  });

  // Productos del carrito
  const cartItems = cart.data?.productos || [];
  const cartTotal = cart.data?.total || 0;
  const cartSubtotal = cart.data?.subtotal || 0;
  const cartDiscount = cart.data?.descuento || "sin";

  // Verificar si un producto ya está en el carrito
  const isInCart = (almacenId, productoId) => {
    return cartItems.some(
      (item) => item.almacen_id === almacenId && item.producto_id === productoId
    );
  };

  return (
    <div className="space-y-6">
      {/* Header con progreso */}
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">Tienda</h2>
        <p className="mt-1 text-sm text-slate-500">
          {phase === 1
            ? "Crea tu lista de compras con lo que necesitas."
            : "Encuentra los mejores precios y agrega al carrito."}
        </p>
      </div>

      {/* Indicador de pasos */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`grid h-8 w-8 place-items-center rounded-full text-xs font-semibold ${
              phase >= 1
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-400"
            }`}
          >
            1
          </span>
          <span className="text-sm font-medium text-slate-700">Mi lista</span>
        </div>
        <div className="flex-1 h-0.5 bg-slate-200 rounded-full" />
        <div className="flex items-center gap-2">
          <span
            className={`grid h-8 w-8 place-items-center rounded-full text-xs font-semibold ${
              phase >= 2
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-400"
            }`}
          >
            2
          </span>
          <span className="text-sm font-medium text-slate-700">Productos y carrito</span>
        </div>
      </div>

      {/* Fase 1: Crear lista */}
      {phase === 1 && (
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <div className="space-y-6">
            {/* Formulario para agregar */}
            <Card title="¿Qué necesitas comprar?">
              <form className="space-y-4" onSubmit={addToList}>
                <Field label="Producto" hint="Escribe el nombre y presiona agregar.">
                  <div className="flex gap-2">
                    <Input
                      value={nombre}
                      onChange={(event) => setNombre(event.target.value)}
                      placeholder="Arroz, café, leche..."
                      maxLength={200}
                      autoComplete="off"
                    />
                    <Button type="submit" icon="plus" loading={adding}>
                      Agregar
                    </Button>
                  </div>
                </Field>
              </form>
            </Card>

            {/* Lista de items */}
            <Card
              title="Tu lista de compras"
              description={`${lista.items.length} producto${lista.items.length === 1 ? "" : "s"}`}
              actions={<Badge tone="slate">{lista.items.length}</Badge>}
            >
              {lista.loading ? (
                <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
                  <Spinner /> Cargando lista…
                </div>
              ) : lista.error ? (
                <Alert tone="error" title="No se pudo cargar la lista">
                  {errorText(lista.error)}
                </Alert>
              ) : lista.items.length === 0 ? (
                <EmptyState
                  icon="list"
                  title="Tu lista está vacía"
                  description="Agrega los productos que necesitas comprar."
                />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {lista.items.map((item, index) => (
                    <li key={item} className="flex items-center justify-between gap-3 py-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-slate-100 font-mono text-xs font-semibold text-slate-500">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-800">{item}</p>
                          <p className="text-xs text-slate-400">Pendiente de compra</p>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="dangerSoft"
                        icon="trash"
                        loading={removing === item}
                        onClick={() => removeFromList(item)}
                      >
                        Quitar
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          {/* Panel lateral - resumen */}
          <div className="space-y-6">
            <Card title="¿Cómo funciona?">
              <div className="space-y-3 text-sm text-slate-600">
                <div className="flex gap-3">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-semibold text-slate-500">1</span>
                  <p>Agrega los productos que necesitas comprar.</p>
                </div>
                <div className="flex gap-3">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-semibold text-slate-500">2</span>
                  <p>Verás los productos disponibles en cada almacén con sus precios.</p>
                </div>
                <div className="flex gap-3">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-semibold text-slate-500">3</span>
                  <p>Selecciona los que más te gusten y agrégalos al carrito.</p>
                </div>
              </div>
            </Card>

            <Button
              icon="search"
              iconRight="arrow"
              className="w-full"
              onClick={searchProducts}
              disabled={lista.items.length === 0}
            >
              Buscar productos
            </Button>
          </div>
        </div>
      )}

      {/* Fase 2: Productos y carrito */}
      {phase === 2 && (
        <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
          <div className="space-y-6">
            {/* Lista de compras - editable */}
            <Card
              title="Mi lista de compras"
              description={`${lista.items.length} productos buscados`}
              actions={
                <div className="flex items-center gap-2">
                  <Badge tone="slate">{lista.items.length}</Badge>
                  <Button
                    size="sm"
                    variant="secondary"
                    icon="arrow-left"
                    onClick={() => setPhase(1)}
                  >
                    Volver
                  </Button>
                </div>
              }
            >
              <div className="flex flex-wrap gap-2">
                {lista.items.map((item) => (
                  <span
                    key={item}
                    className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
                  >
                    {item}
                    <button
                      onClick={() => removeFromList(item)}
                      className="ml-0.5 text-slate-400 hover:text-rose-500"
                      disabled={removing === item}
                    >
                      {removing === item ? <Spinner size={10} /> : "×"}
                    </button>
                  </span>
                ))}
                <form onSubmit={addToList} className="flex items-center gap-1">
                  <Input
                    value={nombre}
                    onChange={(event) => setNombre(event.target.value)}
                    placeholder="+ Agregar"
                    maxLength={200}
                    autoComplete="off"
                    className="w-28 py-1 text-xs"
                  />
                  <Button
                    type="submit"
                    size="sm"
                    variant="secondary"
                    icon="plus"
                    loading={adding}
                    className="p-1"
                  />
                </form>
              </div>
            </Card>

            {/* Controles de búsqueda */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <Select
                  value={sort}
                  onChange={(event) => setSort(event.target.value)}
                  className="w-48"
                >
                  {SORT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
                <Badge tone="slate">{sortedRows.length} resultados</Badge>
              </div>
              <Button
                size="sm"
                variant="secondary"
                icon="refresh"
                onClick={searchProducts}
                loading={products.loading}
              >
                Actualizar
              </Button>
            </div>

            {/* Resultados de productos */}
            {products.loading ? (
              <Card>
                <div className="flex items-center gap-2 py-10 text-sm text-slate-500">
                  <Spinner /> Buscando productos en los almacenes…
                </div>
              </Card>
            ) : products.error ? (
              <Alert tone="error" title="No se pudieron buscar productos">
                {errorText(products.error)}
              </Alert>
            ) : sortedRows.length === 0 ? (
              <Card>
                <EmptyState
                  icon="search"
                  title="No se encontraron productos"
                  description="Intenta agregar otros productos a tu lista o verifica que estén disponibles."
                  action={
                    <Button size="sm" variant="secondary" icon="arrow-left" onClick={() => setPhase(1)}>
                      Modificar lista
                    </Button>
                  }
                />
              </Card>
            ) : (
              <div className="space-y-6">
                {Object.values(groupedByWarehouse).map((warehouse) => (
                  <Card
                    key={warehouse.id}
                    title={warehouse.nombre}
                    description={`${warehouse.productos.length} producto${warehouse.productos.length === 1 ? "" : "s"} disponible${warehouse.productos.length === 1 ? "" : "s"}`}
                  >
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-100 text-sm">
                        <thead>
                          <tr className="bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
                            <th className="px-4 py-3 font-semibold">Producto</th>
                            <th className="px-4 py-3 font-semibold">Tipo</th>
                            <th className="px-4 py-3 text-right font-semibold">Precio</th>
                            <th className="px-4 py-3 text-right font-semibold">Precio final</th>
                            <th className="px-4 py-3 text-right font-semibold">Acción</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {warehouse.productos.map((row) => {
                            const key = `${row.almacen_id}-${row.producto.producto_id}`;
                            const inCart = isInCart(row.almacen_id, row.producto.producto_id);
                            return (
                              <tr key={key} className="transition hover:bg-slate-50/70">
                                <td className="px-4 py-3">
                                  <p className="font-medium text-slate-800">{row.producto.nombre}</p>
                                  <p className="text-xs text-slate-400">
                                    {row.producto.marca} · {row.producto.categoria}
                                  </p>
                                </td>
                                <td className="px-4 py-3">
                                  <ProductTypeBadge tipo={row.producto.tipo} />
                                </td>
                                <td className="px-4 py-3 text-right text-slate-600">
                                  <Money value={row.producto.precio} />
                                </td>
                                <td className="px-4 py-3 text-right font-semibold text-slate-900">
                                  <Money value={row.producto.precio_final} />
                                </td>
                                <td className="px-4 py-3 text-right">
                                  {inCart ? (
                                    <Badge tone="emerald">En carrito</Badge>
                                  ) : (
                                    <Button
                                      size="sm"
                                      variant="secondary"
                                      icon="cart"
                                      loading={addingToCart === key}
                                      onClick={() => addToCart(row)}
                                    >
                                      Agregar
                                    </Button>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Panel lateral - Carrito */}
          <div className="space-y-6">
            <Card
              title="Mi carrito"
              description={`${cartItems.length} producto${cartItems.length === 1 ? "" : "s"}`}
              actions={<Badge tone="slate">{cartItems.length}</Badge>}
            >
              {cart.loading && !cart.data ? (
                <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
                  <Spinner /> Cargando carrito…
                </div>
              ) : cartItems.length === 0 ? (
                <EmptyState
                  icon="cart"
                  title="Carrito vacío"
                  description="Agrega productos desde la lista de arriba."
                />
              ) : (
                <>
                  <ul className="divide-y divide-slate-100">
                    {cartItems.map((product, index) => (
                      <li
                        key={`${product.producto_id}-${index}`}
                        className="flex items-center gap-2 py-3"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <p className="truncate text-xs font-medium text-slate-800">
                              {product.nombre}
                            </p>
                            <ProductTypeBadge tipo={product.tipo} />
                          </div>
                          <p className="mt-0.5 text-[11px] text-slate-400">
                            {product.marca}
                            {product.almacen ? ` · ${product.almacen}` : ""}
                          </p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-xs font-semibold text-slate-900">
                            <Money value={product.precio_final} />
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="dangerSoft"
                          icon="x"
                          loading={removingFromCart === index}
                          onClick={() => removeFromCart(index)}
                          className="p-1 h-6 w-6"
                        />
                      </li>
                    ))}
                  </ul>

                  {/* Resumen */}
                  <div className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-xs">
                    <div className="flex justify-between text-slate-500">
                      <span>Subtotal</span>
                      <span className="font-medium text-slate-700">
                        <Money value={cartSubtotal} />
                      </span>
                    </div>
                    {cartDiscount && cartDiscount !== "sin" && (
                      <div className="flex justify-between text-slate-500">
                        <span>Descuento</span>
                        <span className="font-medium text-slate-700">{cartDiscount}</span>
                      </div>
                    )}
                    <div className="flex justify-between border-t border-dashed border-slate-200 pt-2 text-sm font-semibold text-slate-900">
                      <span>Total</span>
                      <Money value={cartTotal} />
                    </div>
                  </div>

                  <Button
                    size="sm"
                    variant="secondary"
                    icon="cart"
                    className="w-full mt-4"
                    onClick={() => onNavigate("carrito")}
                  >
                    Ver carrito completo
                  </Button>
                </>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}