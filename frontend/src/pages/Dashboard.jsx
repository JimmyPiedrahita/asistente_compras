import { useApp } from "../context/AppContext";
import ClientDashboard from "./ClientDashboard";
import ProviderDashboard from "./ProviderDashboard";
import AdminDashboard from "./AdminDashboard";

export default function Dashboard({ onNavigate }) {
  const { session } = useApp();

  if (!session) {
    return null;
  }

  if (session.rol === "ADMIN") {
    return <AdminDashboard onNavigate={onNavigate} />;
  }

  if (session.rol === "PROVEEDOR") {
    return <ProviderDashboard onNavigate={onNavigate} />;
  }

  return <ClientDashboard onNavigate={onNavigate} />;
}
