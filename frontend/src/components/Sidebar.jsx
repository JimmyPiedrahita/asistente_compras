import { useEffect, useState } from "react";
import Icon from "./Icon";
import { useApp } from "../context/AppContext";

export const NAV_ITEMS = [
  { id: "inicio", label: "Inicio", icon: "dashboard", description: "Salud y resumen" },
  { id: "almacenes", label: "Almacenes", icon: "warehouse", description: "Inventarios" },
  { id: "sesion", label: "Sesión", icon: "key", description: "Cliente, proveedor y admin" },
  {
    id: "roles",
    label: "Roles y permisos",
    icon: "shield",
    description: "Qué puede hacer cada rol",
  },
  {
    id: "lista",
    label: "Lista de compras",
    icon: "list",
    description: "Lista personal",
    permission: "crear_lista",
  },
  {
    id: "busqueda",
    label: "Búsqueda",
    icon: "search",
    description: "Comparar precios",
    permission: "comparar",
  },
  {
    id: "carrito",
    label: "Carrito",
    icon: "cart",
    description: "Ítems y descuentos",
    permission: "agregar_producto",
  },
  {
    id: "admin",
    label: "Administración",
    icon: "settings",
    description: "Inventario del almacén",
    permission: "gestionar_inventario",
  },
  {
    id: "exportar",
    label: "Exportar CSV",
    icon: "download",
    description: "Descargas",
    permission: "exportar",
  },
];

function ApiSettings() {
  const { apiBase, changeApiBase, docs } = useApp();
  const [draft, setDraft] = useState(apiBase);

  useEffect(() => {
    setDraft(apiBase);
  }, [apiBase]);

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-slate-400">
          API conectada
        </p>
        <a
          href={docs}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-500 transition hover:text-slate-900"
        >
          Docs <Icon name="external" size={10} />
        </a>
      </div>
      <form
        className="mt-2 space-y-2"
        onSubmit={(event) => {
          event.preventDefault();
          changeApiBase(draft);
        }}
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          spellCheck={false}
          aria-label="URL base de la API"
          className="w-full rounded-md border border-slate-200 bg-white px-2.5 py-2 font-mono text-[11px] text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-900/5"
        />
        <button
          type="submit"
          className="w-full rounded-md bg-slate-900 px-2.5 py-1.5 text-[11px] font-medium text-white transition hover:bg-slate-800"
        >
          Guardar URL
        </button>
      </form>
      <p className="mt-2 text-[10px] leading-relaxed text-slate-400">
        Si omites la ruta se añade <span className="font-mono">/api/v1</span>.
      </p>
    </div>
  );
}

export function SidebarContent({ page, onNavigate, onClose }) {
  const { can } = useApp();
  const visibleItems = NAV_ITEMS.filter((item) => !item.permission || can(item.permission));

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 px-5 pb-5 pt-6">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-slate-900 text-white">
            <Icon name="cart" size={17} strokeWidth={1.8} />
          </span>
          <div>
            <p className="text-sm font-semibold tracking-tight text-slate-900">
              Asistente de Compras
            </p>
            <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-slate-400">
              Consola API v1
            </p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 lg:hidden"
            aria-label="Cerrar menú"
          >
            <Icon name="x" size={18} />
          </button>
        )}
      </div>

      <nav className="scroll-thin flex-1 space-y-1 overflow-y-auto px-3">
        {visibleItems.map((item) => {
          const active = page === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                active
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <span
                className={`grid h-7 w-7 shrink-0 place-items-center rounded-md transition ${
                  active
                    ? "bg-white/10 text-white"
                    : "bg-slate-100 text-slate-400 group-hover:text-slate-600"
                }`}
              >
                <Icon name={item.icon} size={14} />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">{item.label}</span>
                <span className="block truncate text-[11px] text-slate-400">
                  {item.description}
                </span>
              </span>
            </button>
          );
        })}
      </nav>

      <div className="space-y-3 border-t border-slate-200 p-4">
        <ApiSettings />
        <p className="px-1 text-[10px] leading-relaxed text-slate-400">
          FastAPI + MongoDB · v3.1.0
        </p>
      </div>
    </div>
  );
}

export default function Sidebar({ page, onNavigate }) {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-slate-200 bg-white lg:block">
      <SidebarContent page={page} onNavigate={onNavigate} />
    </aside>
  );
}
