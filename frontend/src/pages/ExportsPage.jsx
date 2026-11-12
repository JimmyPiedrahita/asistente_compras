import { useState } from "react";
import { ENDPOINTS, api } from "../api";
import Icon from "../components/Icon";
import { Badge, Button, Card, NeedPermission, NeedSession } from "../components/ui";
import { useApp } from "../context/AppContext";

const METHOD_TONES = { GET: "slate", POST: "dark", PATCH: "slate", DELETE: "slate" };

const EXPORTS = [
  {
    key: "list",
    title: "Lista de compras",
    description: "Descarga los productos pendientes de la sesión en formato CSV.",
    path: "/sessions/{token}/export/shopping-list",
    filename: "lista_compra.csv",
    icon: "list",
    action: (token) => api.exportShoppingList(token),
  },
  {
    key: "cart",
    title: "Carrito",
    description: "Descarga el contenido del carrito y sus precios en formato CSV.",
    path: "/sessions/{token}/export/cart",
    filename: "carrito.csv",
    icon: "cart",
    action: (token) => api.exportCart(token),
  },
];

export default function ExportsPage({ onNavigate }) {
  const { session, token, can, notify, notifyError } = useApp();
  const [exporting, setExporting] = useState(null);

  if (!session) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Exportar CSV</h2>
          <p className="mt-1 text-sm text-slate-500">
            Descarga la lista de compras y el carrito de la sesión.
          </p>
        </div>
        <NeedSession onNavigate={onNavigate} />
      </div>
    );
  }

  if (!can("exportar")) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">Exportar CSV</h2>
          <p className="mt-1 text-sm text-slate-500">
            La exportación de lista y carrito es exclusiva del rol comprador.
          </p>
        </div>
        <NeedPermission
          onNavigate={onNavigate}
          session={session}
          permission="exportar"
          title="Tu rol no puede exportar CSV"
        />
      </div>
    );
  }

  const download = async (item) => {
    setExporting(item.key);
    try {
      const filename = await item.action(token);
      notify(`Descargado ${filename}`, "success", "Exportación");
    } catch (error) {
      notifyError(error);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">Exportar CSV</h2>
        <p className="mt-1 text-sm text-slate-500">
          Los dos endpoints de exportación descargan archivos con el token de la sesión.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {EXPORTS.map((item) => (
          <Card key={item.key} className="h-full">
            <div className="flex h-full flex-col">
              <div className="flex items-start justify-between gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-slate-100 text-slate-500">
                  <Icon name={item.icon} size={18} />
                </span>
                <Badge tone="slate">GET</Badge>
              </div>
              <h3 className="mt-4 text-base font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-1 flex-1 text-sm leading-relaxed text-slate-500">
                {item.description}
              </p>
              <div className="mt-4 rounded-lg bg-slate-50 px-3 py-2 font-mono text-[11px] text-slate-500">
                {item.path}
              </div>
              <div className="mt-4 flex items-center justify-between gap-3">
                <span className="text-xs text-slate-400">{item.filename}</span>
                <Button
                  icon="download"
                  loading={exporting === item.key}
                  onClick={() => download(item)}
                >
                  Descargar
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card title="Mapa completo de endpoints" description={`${ENDPOINTS.length} rutas consumidas por esta interfaz.`}>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-slate-400">
                <th className="px-2 py-2 font-semibold">Método</th>
                <th className="px-3 py-2 font-semibold">Ruta</th>
                <th className="px-3 py-2 font-semibold">Grupo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {ENDPOINTS.map((endpoint) => (
                <tr key={`${endpoint.method}-${endpoint.path}`} className="hover:bg-slate-50/70">
                  <td className="px-2 py-2">
                    <Badge tone={METHOD_TONES[endpoint.method] || "slate"}>{endpoint.method}</Badge>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-slate-600">{endpoint.path}</td>
                  <td className="px-3 py-2 text-xs text-slate-400">{endpoint.group}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
