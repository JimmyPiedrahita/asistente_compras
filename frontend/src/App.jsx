import { useState } from "react";
import Icon from "./components/Icon";
import Sidebar, { NAV_ITEMS, SidebarContent } from "./components/Sidebar";
import Toasts from "./components/Toasts";
import { Badge, Button, CopyButton } from "./components/ui";
import { AppProvider, useApp } from "./context/AppContext";
import AdminPage from "./pages/AdminPage";
import CartPage from "./pages/CartPage";
import Dashboard from "./pages/Dashboard";
import ExportsPage from "./pages/ExportsPage";
import RolesPage from "./pages/RolesPage";
import SearchPage from "./pages/SearchPage";
import SessionPage from "./pages/SessionPage";
import ShoppingListPage from "./pages/ShoppingListPage";
import WarehousesPage from "./pages/WarehousesPage";

const PAGES = {
  inicio: Dashboard,
  almacenes: WarehousesPage,
  sesion: SessionPage,
  roles: RolesPage,
  lista: ShoppingListPage,
  busqueda: SearchPage,
  carrito: CartPage,
  admin: AdminPage,
  exportar: ExportsPage,
};

function SessionChip({ onNavigate }) {
  const { session, closeSession } = useApp();
  const [closing, setClosing] = useState(false);

  if (!session) {
    return (
      <Button size="sm" variant="secondary" icon="key" onClick={() => onNavigate("sesion")}>
        <span className="hidden sm:inline">Iniciar sesión</span>
        <span className="sm:hidden">Sesión</span>
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 sm:flex">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        <span className="max-w-[11rem] truncate text-xs font-medium text-slate-700">
          {session.usuario}
        </span>
        <Badge tone="slate">{session.rol}</Badge>
      </div>
      <CopyButton value={session.session_id} label="Token" />
      <Button
        size="sm"
        variant="ghost"
        icon="x"
        loading={closing}
        onClick={async () => {
          setClosing(true);
          try {
            await closeSession();
          } finally {
            setClosing(false);
          }
        }}
      >
        <span className="hidden sm:inline">Salir</span>
      </Button>
    </div>
  );
}

function Topbar({ page, onNavigate, onOpenMenu }) {
  const { session, apiBase } = useApp();
  const meta = NAV_ITEMS.find((item) => item.id === page);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white">
      <div className="flex h-16 items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <button
            onClick={onOpenMenu}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 lg:hidden"
            aria-label="Abrir menú"
          >
            <Icon name="menu" size={20} />
          </button>
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
              Consola · {apiBase.replace(/^https?:\/\//, "")}
            </p>
            <h1 className="truncate text-base font-semibold tracking-tight text-slate-900">
              {meta?.label || "Inicio"}
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {session && (
            <div className="hidden lg:flex">
              <span
                className="inline-flex max-w-[18rem] items-center gap-1.5 truncate rounded-lg bg-slate-100 px-2.5 py-1.5 font-mono text-[10px] text-slate-500"
                title={session.session_id}
              >
                <Icon name="key" size={11} />
                {session.session_id.slice(0, 22)}
                {session.session_id.length > 22 ? "…" : ""}
              </span>
            </div>
          )}
          <SessionChip onNavigate={onNavigate} />
        </div>
      </div>
    </header>
  );
}

function Shell() {
  const [page, setPage] = useState(() => {
    const hash = window.location.hash.replace("#", "");
    return PAGES[hash] ? hash : "inicio";
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const navigate = (id) => {
    if (!PAGES[id]) return;
    setPage(id);
    setMobileOpen(false);
    window.location.hash = id;
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const Page = PAGES[page] || Dashboard;

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar page={page} onNavigate={navigate} />

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/20"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-72 border-r border-slate-200 bg-white">
            <SidebarContent
              page={page}
              onNavigate={navigate}
              onClose={() => setMobileOpen(false)}
            />
          </div>
        </div>
      )}

      <div className="lg:pl-72">
        <Topbar page={page} onNavigate={navigate} onOpenMenu={() => setMobileOpen(true)} />
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div key={page} className="animate-fade">
            <Page onNavigate={navigate} />
          </div>
          <footer className="mt-10 flex flex-col items-center justify-between gap-2 border-t border-slate-200 py-5 text-xs text-slate-400 sm:flex-row">
            <p>
              Interfaz React + Tailwind CSS · consume todas las rutas de{" "}
              <span className="font-mono text-slate-500">/api/v1</span>
            </p>
            <p className="font-mono">Asistente de Compras 3.1.0</p>
          </footer>
        </main>
      </div>

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
