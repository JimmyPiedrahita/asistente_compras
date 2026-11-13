import Icon from "./Icon";
import { useApp } from "../context/AppContext";

const ALL_ITEMS = [
  { id: "inicio", label: "Inicio", icon: "dashboard", description: "Tu panel principal" },
  {
    id: "roles",
    label: "Roles y permisos",
    icon: "shield",
    description: "Qué puede hacer cada rol",
  },
  {
    id: "tienda",
    label: "Tienda",
    icon: "cart",
    description: "Compra productos",
    roles: ["CLIENTE", "ADMIN"],
  },
  {
    id: "carrito",
    label: "Mi carrito",
    icon: "cart",
    description: "Ítems y descuentos",
    roles: ["CLIENTE", "ADMIN"],
  },
  {
    id: "almacenes",
    label: "Inventario",
    icon: "warehouse",
    description: "Productos disponibles",
    roles: ["PROVEEDOR", "ADMIN"],
  },
  {
    id: "admin",
    label: "Gestión",
    icon: "settings",
    description: "Productos y precios",
    roles: ["PROVEEDOR", "ADMIN"],
  },
];

export const NAV_ITEMS = ALL_ITEMS;

export function SidebarContent({ page, onNavigate, onClose }) {
  const { session } = useApp();
  const rol = session?.rol;
  const visibleItems = ALL_ITEMS.filter((item) => !item.roles || item.roles.includes(rol));

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
              {rol === "ADMIN" ? "Administración" : rol === "PROVEEDOR" ? "Proveedor" : "Cliente"}
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

      <div className="border-t border-slate-200 p-4">
        <p className="px-1 text-[10px] leading-relaxed text-slate-400">
          Asistente de Compras · v3.1.0
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
