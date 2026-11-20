import { useCallback, useEffect, useState } from "react";
import Icon from "../components/Icon";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Money,
  Spinner,
} from "../components/ui";
import { useApp } from "../context/AppContext";
import { api } from "../api";

const MODOS = [
  { id: "catalogo", label: "Todo el catálogo" },
  { id: "mejor_precio", label: "Más barato por almacén" },
  { id: "global", label: "Más barato global" },
];

export default function ShoppingListPage({ onNavigate }) {
  const { token, notify, notifyError } = useApp();
  const [lista, setLista] = useState([]);
  const [texto, setTexto] = useState("");
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [modo, setModo] = useState("catalogo");
  const [buscando, setBuscando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [agregando, setAgregando] = useState("");

  const cargar = useCallback(async () => {
    try {
      const datos = await api.getShoppingList(token);
      setLista(datos?.lista ?? []);
    } catch (error) {
      notifyError(error);
    } finally {
      setCargando(false);
    }
  }, [notifyError, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const agregar = async (evento) => {
    evento.preventDefault();
    const nombre = texto.trim();
    if (!nombre) return;
    setGuardando(true);
    try {
      const datos = await api.addShoppingListItem(token, nombre);
      setLista(datos?.lista ?? []);
      setTexto("");
      setResultado(null);
      notify(`“${nombre}” se agregó a tu lista.`, "success", "Lista de compras");
    } catch (error) {
      notifyError(error);
    } finally {
      setGuardando(false);
    }
  };

  const quitar = async (nombre) => {
    try {
      const datos = await api.removeShoppingListItem(token, nombre);
      setLista(datos?.lista ?? []);
      setResultado(null);
      notify(`“${nombre}” se quitó de tu lista.`, "success", "Lista de compras");
    } catch (error) {
      notifyError(error);
    }
  };

  const buscar = async (nuevoModo = modo) => {
    if (!lista.length) {
      notify("Agrega al menos un producto a tu lista antes de buscar.", "info");
      return;
    }
    setBuscando(true);
    try {
      const datos = await api.search(token, nuevoModo);
      setResultado(datos);
      setModo(nuevoModo);
    } catch (error) {
      notifyError(error);
    } finally {
      setBuscando(false);
    }
  };

  const agregarAlCarrito = async (fila) => {
    const clave = `${fila.almacen_id}:${fila.producto.producto_id}`;
    setAgregando(clave);
    try {
      await api.addCartItem(token, {
        almacen_id: fila.almacen_id,
        producto_id: fila.producto.producto_id,
        cantidad: 1,
      });
      notify(
        `${fila.producto.nombre} de ${fila.almacen} se agregó al carrito.`,
        "success",
        "Carrito",
      );
    } catch (error) {
      notifyError(error);
    } finally {
      setAgregando("");
    }
  };

  const sinCoincidenciasTotales =
    resultado && resultado.hay_productos && resultado.total_resultados === 0;

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr] lg:items-start">
      <Card
        title="Mi lista de compras"
        description="Anota los productos que necesitas y luego compáralos entre almacenes."
      >
        <form onSubmit={agregar} className="flex gap-2">
          <Input
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
            placeholder="Ej. arroz, leche, huevos"
            maxLength={200}
            aria-label="Producto para agregar a la lista"
          />
          <Button type="submit" icon="plus" loading={guardando} disabled={!texto.trim()}>
            Agregar
          </Button>
        </form>

        <div className="mt-4">
          {cargando ? (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-stone-500">
              <Spinner /> Cargando lista…
            </div>
          ) : lista.length === 0 ? (
            <EmptyState
              icon="list"
              title="Tu lista está vacía"
              description="Agrega los productos que quieres comprar. La lista no agrega nada al carrito."
            />
          ) : (
            <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200">
              {lista.map((nombre) => (
                <li key={nombre} className="flex items-center gap-3 px-3 py-2.5">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-stone-100 text-stone-500">
                    <Icon name="check" size={13} />
                  </span>
                  <span className="min-w-0 flex-1 break-words text-sm font-medium text-stone-800">
                    {nombre}
                  </span>
                  <button
                    onClick={() => quitar(nombre)}
                    className="rounded-md p-1.5 text-stone-400 transition hover:bg-rose-50 hover:text-rose-600"
                    aria-label={`Quitar ${nombre} de la lista`}
                  >
                    <Icon name="trash" size={15} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <Button
          size="lg"
          icon="search"
          className="mt-4 w-full"
          loading={buscando}
          disabled={!lista.length}
          onClick={() => buscar(modo)}
        >
          Buscar productos
        </Button>
        <p className="mt-2 text-center text-xs text-stone-500">
          Compara precios de la presentación estándar de cada producto.
        </p>
      </Card>

      <div className="space-y-4">
        <Card
          title="Resultados de la búsqueda"
          description="Los filtros comparan el precio registrado antes de cupones."
          actions={
            <div className="flex w-full min-w-0 flex-wrap gap-1.5 sm:w-auto">
              {MODOS.map((opcion) => (
                <Button
                  key={opcion.id}
                  size="sm"
                  variant={modo === opcion.id ? "primary" : "secondary"}
                  className="min-w-0 flex-1 whitespace-normal px-2 text-center sm:flex-none sm:px-3"
                  onClick={() => buscar(opcion.id)}
                  disabled={buscando || !lista.length}
                >
                  {opcion.label}
                </Button>
              ))}
            </div>
          }
        >
          {!resultado ? (
            <EmptyState
              icon="search"
              title="Aún no has buscado"
              description="Cuando tengas tu lista, pulsa “Buscar productos” para ver las opciones de los almacenes."
            />
          ) : buscando ? (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-stone-500">
              <Spinner /> Buscando…
            </div>
          ) : !resultado.hay_productos ? (
            <EmptyState
              icon="package"
              title="No hay productos disponibles por el momento."
              description="Los almacenes todavía no han registrado productos en la aplicación."
            />
          ) : sinCoincidenciasTotales ? (
            <EmptyState
              icon="search"
              title="No se encontraron productos para tu lista de compras."
              description="Prueba con otros nombres o revisa que el producto esté registrado por algún almacén."
            />
          ) : (
            <div className="space-y-6">
              {resultado.grupos.map((grupo) => (
                <section key={grupo.producto_buscado}>
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-bold capitalize text-stone-900">
                      {grupo.producto_buscado}
                    </h3>
                    <Badge tone="slate">
                      {grupo.resultados.length}{" "}
                      {grupo.resultados.length === 1 ? "opción" : "opciones"}
                    </Badge>
                  </div>
                  {grupo.sin_resultados ? (
                    <Alert tone="warning">
                      No se encontraron productos para “{grupo.producto_buscado}”.
                    </Alert>
                  ) : (
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      {grupo.resultados.map((fila) => {
                        const clave = `${fila.almacen_id}:${fila.producto.producto_id}`;
                        return (
                          <article
                            key={clave}
                            className="group overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm"
                          >
                            <div className="relative aspect-[4/3] overflow-hidden bg-stone-100">
                              {fila.producto.imagen_url ? (
                                <img
                                  src={fila.producto.imagen_url}
                                  alt={`Imagen de ${fila.producto.nombre}`}
                                  loading="lazy"
                                  className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.02]"
                                />
                              ) : (
                                <div
                                  className="grid h-full w-full place-items-center text-stone-300"
                                  aria-label={`Sin imagen de ${fila.producto.nombre}`}
                                >
                                  <Icon name="package" size={38} />
                                </div>
                              )}
                              <Badge
                                tone="dark"
                                className="absolute left-3 top-3 max-w-[calc(100%-1.5rem)] truncate shadow-sm"
                              >
                                {fila.almacen}
                              </Badge>
                            </div>
                            <div className="flex min-h-44 flex-col p-4">
                              <div className="min-w-0">
                                <p className="text-base font-bold leading-snug text-stone-900">
                                  {fila.producto.nombre}
                                </p>
                                {fila.producto.marca_variedad ? (
                                  <p className="mt-1 text-sm text-stone-500">
                                    {fila.producto.marca_variedad}
                                  </p>
                                ) : null}
                              </div>
                              <p className="mt-2 text-xs font-medium text-stone-500">
                                Presentación: {fila.producto.presentacion}
                              </p>
                              <div className="mt-auto pt-4">
                                <div className="mb-3 flex items-end justify-between gap-3 border-t border-stone-100 pt-3">
                                  <div>
                                    <p className="text-xl font-black tracking-tight text-stone-900">
                                      <Money value={fila.producto.precio} />
                                    </p>
                                    <p className="text-[11px] text-stone-400">por unidad</p>
                                  </div>
                                </div>
                                <Button
                                  size="lg"
                                  icon="cart"
                                  className="w-full"
                                  loading={agregando === clave}
                                  onClick={() => agregarAlCarrito(fila)}
                                >
                                  Agregar al carrito
                                </Button>
                              </div>
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  )}
                </section>
              ))}
            </div>
          )}
        </Card>

        {resultado && resultado.total_resultados > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-200 bg-white px-5 py-4">
            <p className="text-sm text-stone-600">
              ¿Ya elegiste? Revisa cantidades, aplica cupones y confirma el pago.
            </p>
            <Button icon="cart" onClick={() => onNavigate("carrito")}>
              Ir al carrito
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
