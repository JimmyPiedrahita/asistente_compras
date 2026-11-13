import { useState } from "react";
import { api } from "../api";
import Icon from "../components/Icon";
import { Button, Card, Field, Input, Select } from "../components/ui";
import { useApp } from "../context/AppContext";

const ROLES = [
  { value: "cliente", label: "Cliente", icon: "user", hint: "Busca productos, gestiona tu lista y carrito de compras." },
  { value: "proveedor", label: "Proveedor", icon: "warehouse", hint: "Gestiona tu inventario, precios e importación CSV." },
  { value: "admin", label: "Administrador", icon: "shield", hint: "Acceso completo: usuarios, inventario, comparador y más." },
];

export default function LoginPage({ onNavigate }) {
  const { saveSession, notify, notifyError } = useApp();
  const [tipo, setTipo] = useState("cliente");
  const [nombre, setNombre] = useState("");
  const [clave, setClave] = useState("");
  const [loading, setLoading] = useState(false);

  const role = ROLES.find((r) => r.value === tipo);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (tipo === "cliente" && !nombre.trim()) {
      notify("Escribe tu nombre para continuar.", "info", "Datos incompletos");
      return;
    }
    if (tipo === "proveedor" && !nombre.trim()) {
      notify("Escribe el nombre de tu empresa.", "info", "Datos incompletos");
      return;
    }
    if (tipo === "admin" && !clave.trim()) {
      notify("Escribe la clave de administrador.", "info", "Datos incompletos");
      return;
    }

    setLoading(true);
    try {
      let data;
      if (tipo === "cliente") {
        const response = await api.createUserSession(nombre.trim());
        data = response.data;
        notify(`¡Bienvenido, ${data.usuario}!`, "success", "Sesión iniciada");
      } else if (tipo === "proveedor") {
        const response = await api.createProviderSession(nombre.trim());
        data = response.data;
        notify(`¡Bienvenido, ${data.usuario}! Almacén: ${data.almacen_id}.`, "success", "Sesión iniciada");
      } else {
        const response = await api.createAdminSession(clave);
        data = response.data;
        notify("Sesión de administrador iniciada.", "success", "Sesión iniciada");
      }
      saveSession(data);
      setNombre("");
      setClave("");
      if (onNavigate) {
        onNavigate("inicio");
      }
    } catch (error) {
      notifyError(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center">
          <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-slate-900 text-white">
            <Icon name="sparkles" size={28} />
          </div>
          <h1 className="mt-6 text-2xl font-semibold tracking-tight text-slate-900">
            Asistente de Compras
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Inicia sesión para acceder a tu panel
          </p>
        </div>

        <Card className="mt-8">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <Field label="Tipo de cuenta">
              <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </Field>

            {tipo !== "admin" ? (
              <Field
                label={tipo === "cliente" ? "Tu nombre" : "Nombre de la empresa"}
                hint={role?.hint}
              >
                <Input
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder={tipo === "cliente" ? "Ana" : "Distribuidora Norte"}
                  maxLength={120}
                  autoComplete="off"
                />
              </Field>
            ) : (
              <Field
                label="Clave de administrador"
                hint={role?.hint}
              >
                <Input
                  type="password"
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </Field>
            )}

            <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3">
              <span className="grid h-8 w-8 place-items-center rounded-md bg-slate-100 text-slate-500">
                <Icon name={role?.icon} size={16} />
              </span>
              <p className="text-xs text-slate-500">{role?.hint}</p>
            </div>

            <Button type="submit" loading={loading} className="w-full">
              Iniciar sesión como {role?.label.toLowerCase()}
            </Button>
          </form>
        </Card>

        <p className="mt-6 text-center text-xs text-slate-400">
          ¿No tienes cuenta? Contacta al administrador para que te registre.
        </p>
      </div>
    </div>
  );
}
