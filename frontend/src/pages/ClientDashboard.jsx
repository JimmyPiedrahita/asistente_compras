import { useEffect } from "react";
import { Spinner } from "../components/ui";
import { useApp } from "../context/AppContext";

export default function ClientDashboard({ onNavigate }) {
  const { session } = useApp();

  // Redirigir automáticamente a la tienda
  useEffect(() => {
    if (session) {
      onNavigate("tienda");
    }
  }, [session, onNavigate]);

  return (
    <div className="flex items-center justify-center py-20">
      <div className="flex flex-col items-center gap-3 text-sm text-slate-500">
        <Spinner />
        <p>Redirigiendo a la tienda…</p>
      </div>
    </div>
  );
}
