import { useEffect, useMemo, useState } from "react";
import Icon from "./components/Icon";
import Toasts from "./components/Toasts";
import { Button } from "./components/ui";
import { AppProvider, useApp } from "./context/AppContext";
import AdminsPage from "./pages/AdminsPage";
import AuthPage from "./pages/AuthPage";
import CartPage from "./pages/CartPage";
import CouponsPage from "./pages/CouponsPage";
import ProductsPage from "./pages/ProductsPage";
import PurchasesPage from "./pages/PurchasesPage";
import ShoppingListPage from "./pages/ShoppingListPage";
import StatsPage from "./pages/StatsPage";
import WarehousesPage from "./pages/WarehousesPage";

const NAV = {
  CLIENTE: [
    { id: "lista", label: "Lista de compras", icon: "list" },
    { id: "carrito", label: "Carrito", icon: "cart" },
  ],
  ADMINISTRADOR_ALMACEN: [
    { id: "productos", label: "Productos", icon: "package" },
    { id: "cupones", label: "Cupones", icon: "sparkles" },
    { id: "compras", label: "Compras de mi almacén", icon: "cart" },
    { id: "estadisticas", label: "Estadísticas", icon: "dashboard" },
  ],
  ADMINISTRADOR_APP: [
    { id: "almacenes", label: "Almacenes", icon: "warehouse" },
    { id: "administradores", label: "Administradores", icon: "shield" },
  ],
};

const PAGES = {
  lista: ShoppingListPage,
  carrito: CartPage,
  productos: ProductsPage,
  cupones: CouponsPage,
  compras: PurchasesPage,
  estadisticas: StatsPage,
  almacenes: WarehousesPage,
  administradores: AdminsPage,
};

function Header({ page, onNavigate }) {
  const { session, logout } = useApp();
  const items = NAV[session.rol] || [];
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 bg-[#ffe600] shadow-sm">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-2.5 sm:px-6">
        <button
          onClick={() => onNavigate(items[0]?.id)}
          className="flex items-center gap-2 text-left"
          aria-label="Ir al inicio"
        >
          <span className="grid h-9 w-9 place-items-center rounded-full bg-[#3483fa] text-white">
            <Icon name="cart" size={18} />
          </span>
          <span>
            <span className="block text-sm font-bold leading-tight text-stone-900">
              Asistente de Compras
            </span>
            <span className="block text-[11px] font-medium text-stone-700">
              Compara entre almacenes y ahorra
            </span>
          </span>
        </button>

        <div className="ml-auto flex items-center gap-2">
          <div className="hidden text-right sm:block">
            <p className="text-sm font-medium text-stone-900">{session.usuario}</p>
          </div>
          <Button variant="secondary" size="sm" icon="x" onClick={logout}>
            Salir
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon="menu"
            className="lg:hidden"
            onClick={() => setMenuOpen((valor) => !valor)}
          >
            Menú
          </Button>
        </div>
      </div>

      <nav className={`border-t border-yellow-300 bg-[#fff45c] ${menuOpen ? "block" : "hidden"} lg:block`}>
        <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-1.5 sm:flex-row sm:px-6">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                onNavigate(item.id);
                setMenuOpen(false);
              }}
              className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                page === item.id
                  ? "bg-white/90 text-stone-900 shadow-sm"
                  : "text-stone-800 hover:bg-white/60"
              }`}
            >
              <Icon name={item.icon} size={16} />
              {item.label}
            </button>
          ))}
        </div>
      </nav>
    </header>
  );
}

function Shell() {
  const { session } = useApp();
  const items = useMemo(() => NAV[session?.rol] || [], [session?.rol]);
  const [page, setPage] = useState(items[0]?.id || "");

  useEffect(() => {
    setPage(items[0]?.id || "");
  }, [items]);

  if (!session) {
    return (
      <div className="min-h-screen bg-stone-100">
        <AuthPage />
        <Toasts />
      </div>
    );
  }

  const Page = PAGES[page] || PAGES[items[0]?.id];
  return (
    <div className="min-h-screen bg-stone-100">
      <Header page={page} onNavigate={setPage} />
      <main className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:py-6">
        <div key={page} className="animate-fade">
          {Page ? <Page onNavigate={setPage} /> : null}
        </div>
        <footer className="mt-10 border-t border-stone-200 py-6 text-center text-xs text-stone-500">
          Compras y pagos. Cada almacén coordina la entrega de sus productos por separado.
        </footer>
      </main>
      <Toasts />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
