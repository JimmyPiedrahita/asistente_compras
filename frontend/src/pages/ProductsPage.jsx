import { useCallback, useEffect, useRef, useState } from "react";
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
import { api, errorText } from "../api";

const VACIO = {
  tipo_producto: "",
  nombre: "",
  marca_variedad: "",
  precio: "",
  presentacion: "",
};

const CABECERAS = "tipo_producto,nombre,marca_variedad,precio,presentacion";

export default function ProductsPage() {
  const { token, notify, notifyError } = useApp();
  const [productos, setProductos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [form, setForm] = useState(VACIO);
  const [editandoId, setEditandoId] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [erroresCsv, setErroresCsv] = useState([]);
  const [csvMensaje, setCsvMensaje] = useState("");
  const [importando, setImportando] = useState(false);
  const [eliminando, setEliminando] = useState("");
  const archivoRef = useRef(null);

  const cargar = useCallback(async () => {
    try {
      const datos = await api.listProducts(token);
      setProductos(datos ?? []);
    } catch (error) {
      notifyError(error);
    } finally {
      setCargando(false);
    }
  }, [notifyError, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const cambiar = (campo) => (evento) =>
    setForm((actual) => ({ ...actual, [campo]: evento.target.value }));

  const limpiar = () => {
    setForm(VACIO);
    setEditandoId("");
  };

  const editar = (producto) => {
    setEditandoId(producto.producto_id);
    setForm({
      tipo_producto: producto.tipo_producto,
      nombre: producto.nombre,
      marca_variedad: producto.marca_variedad || "",
      precio: String(producto.precio),
      presentacion: producto.presentacion,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const guardar = async (evento) => {
    evento.preventDefault();
    const datos = {
      tipo_producto: form.tipo_producto.trim(),
      nombre: form.nombre.trim(),
      marca_variedad: form.marca_variedad.trim() || null,
      precio: Number(form.precio),
      presentacion: form.presentacion.trim(),
    };
    if (!datos.tipo_producto || !datos.nombre || !datos.presentacion) {
      notify("Completa el tipo de producto, el nombre y la presentación.", "error");
      return;
    }
    if (!Number.isFinite(datos.precio) || datos.precio <= 0) {
      notify("El precio debe ser mayor que cero.", "error");
      return;
    }
    setGuardando(true);
    try {
      if (editandoId) {
        await api.updateProduct(token, editandoId, datos);
        notify("Producto actualizado.", "success", "Productos");
      } else {
        await api.createProduct(token, datos);
        notify("Producto agregado al catálogo.", "success", "Productos");
      }
      limpiar();
      await cargar();
    } catch (error) {
      notifyError(error);
    } finally {
      setGuardando(false);
    }
  };

  const eliminar = async (producto) => {
    if (
      !window.confirm(
        `¿Eliminar “${producto.nombre}” del catálogo? Las compras ya registradas conservarán sus datos.`,
      )
    ) {
      return;
    }
    setEliminando(producto.producto_id);
    try {
      await api.deleteProduct(token, producto.producto_id);
      if (editandoId === producto.producto_id) limpiar();
      await cargar();
      notify("Producto eliminado.", "success", "Productos");
    } catch (error) {
      notifyError(error);
    } finally {
      setEliminando("");
    }
  };

  const importar = async (evento) => {
    const archivo = evento.target.files?.[0];
    evento.target.value = "";
    if (!archivo) return;
    setErroresCsv([]);
    setCsvMensaje("");
    setImportando(true);
    try {
      const contenido = await archivo.text();
      const datos = await api.importCsv(token, contenido, archivo.name);
      setCsvMensaje(
        `Se importaron ${datos.importados} ${
          datos.importados === 1 ? "producto" : "productos"
        } correctamente.`,
      );
      await cargar();
      notify(`Importación completada: ${datos.importados} productos.`, "success", "CSV");
    } catch (error) {
      const lista = error?.payload?.detalles?.errores;
      if (Array.isArray(lista)) {
        setErroresCsv(lista);
        setCsvMensaje("El archivo contiene errores. No se importó ningún producto.");
      } else {
        setCsvMensaje(errorText(error));
      }
    } finally {
      setImportando(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[340px_1fr] lg:items-start">
        <Card
          title={editandoId ? "Editar producto" : "Agregar producto"}
          description="El almacén propietario se asigna automáticamente a tu cuenta."
        >
          <form onSubmit={guardar} className="space-y-3">
            <Field label="Tipo de producto" htmlFor="prod-tipo" hint="Ej. arroz, leche, huevos.">
              <Input
                id="prod-tipo"
                value={form.tipo_producto}
                onChange={cambiar("tipo_producto")}
                maxLength={100}
                required
              />
            </Field>
            <Field label="Nombre comercial" htmlFor="prod-nombre">
              <Input
                id="prod-nombre"
                value={form.nombre}
                onChange={cambiar("nombre")}
                maxLength={200}
                required
              />
            </Field>
            <Field label="Marca o variedad" htmlFor="prod-marca" hint="Opcional.">
              <Input
                id="prod-marca"
                value={form.marca_variedad}
                onChange={cambiar("marca_variedad")}
                maxLength={120}
              />
            </Field>
            <Field label="Precio" htmlFor="prod-precio" hint="Mayor que cero. Sin símbolos ni separadores de miles.">
              <Input
                id="prod-precio"
                type="number"
                min="0.01"
                step="0.01"
                value={form.precio}
                onChange={cambiar("precio")}
                required
              />
            </Field>
            <Field
              label="Presentación"
              htmlFor="prod-presentacion"
              hint="Debe ser la presentación estándar del tipo de producto y coincidir entre almacenes."
            >
              <Input
                id="prod-presentacion"
                value={form.presentacion}
                onChange={cambiar("presentacion")}
                maxLength={100}
                placeholder="Ej. 500 g, 1 litro, docena"
                required
              />
            </Field>
            <div className="flex gap-2">
              <Button type="submit" icon={editandoId ? "check" : "plus"} loading={guardando}>
                {editandoId ? "Guardar cambios" : "Agregar producto"}
              </Button>
              {editandoId ? (
                <Button variant="secondary" icon="x" onClick={limpiar}>
                  Cancelar
                </Button>
              ) : null}
            </div>
          </form>
        </Card>

        <Card
          title={`Catálogo de mi almacén · ${productos.length}`}
          description="Los cambios no alteran las compras ya registradas."
        >
          {cargando ? (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-stone-500">
              <Spinner /> Cargando productos…
            </div>
          ) : productos.length === 0 ? (
            <EmptyState
              icon="package"
              title="Todavía no tienes productos"
              description="Agrega productos manualmente o impórtalos desde un archivo CSV."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 text-[11px] uppercase tracking-wider text-stone-400">
                    <th className="pb-2 pr-3 font-semibold">Producto</th>
                    <th className="pb-2 pr-3 font-semibold">Tipo</th>
                    <th className="pb-2 pr-3 font-semibold">Presentación</th>
                    <th className="pb-2 pr-3 text-right font-semibold">Precio</th>
                    <th className="pb-2 text-right font-semibold">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {productos.map((producto) => (
                    <tr key={producto.producto_id} className="align-middle">
                      <td className="py-2.5 pr-3">
                        <p className="font-medium text-stone-900">{producto.nombre}</p>
                        {producto.marca_variedad ? (
                          <p className="text-xs text-stone-500">{producto.marca_variedad}</p>
                        ) : null}
                      </td>
                      <td className="py-2.5 pr-3">
                        <Badge tone="slate">{producto.tipo_producto}</Badge>
                      </td>
                      <td className="py-2.5 pr-3 text-stone-600">{producto.presentacion}</td>
                      <td className="py-2.5 pr-3 text-right font-semibold tabular-nums text-stone-900">
                        <Money value={producto.precio} />
                      </td>
                      <td className="py-2.5 text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            size="sm"
                            variant="secondary"
                            icon="settings"
                            onClick={() => editar(producto)}
                          >
                            Editar
                          </Button>
                          <Button
                            size="sm"
                            variant="dangerSoft"
                            icon="trash"
                            loading={eliminando === producto.producto_id}
                            onClick={() => eliminar(producto)}
                          >
                            Eliminar
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Card
        title="Importar productos desde CSV"
        description="La importación es completa o no se realiza: si una fila tiene errores, no se guarda ningún producto."
      >
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
              Encabezados requeridos
            </p>
            <code className="mt-2 block break-all whitespace-normal rounded-lg border border-stone-200 bg-stone-50 px-3 py-2.5 text-xs text-stone-700">
              {CABECERAS}
            </code>
            <ul className="mt-3 break-words space-y-1 text-xs leading-relaxed text-stone-500">
              <li>· Archivo UTF-8 separado por comas, con encabezados en la primera fila.</li>
              <li>· <span className="font-medium text-stone-700">tipo_producto</span>, <span className="font-medium text-stone-700">nombre</span>, <span className="font-medium text-stone-700">precio</span> y <span className="font-medium text-stone-700">presentacion</span> son obligatorios.</li>
              <li>· <span className="font-medium text-stone-700">marca_variedad</span> es opcional.</li>
              <li>· Precios sin símbolos de moneda ni separadores de miles; decimales con punto.</li>
              <li>· No incluyas una columna de almacén: se asigna automáticamente.</li>
            </ul>
          </div>
          <div className="min-w-0 flex flex-col justify-center rounded-lg border border-dashed border-stone-200 bg-stone-50/40 p-5 text-center">
            <span className="mx-auto grid h-11 w-11 place-items-center rounded-lg border border-stone-200 bg-white text-stone-500">
              <Icon name="file" size={20} />
            </span>
            <p className="mt-3 text-sm font-medium text-stone-700">Selecciona un archivo .csv</p>
            <p className="mt-1 break-words text-xs text-stone-500">
              Solo se agregarán productos; no se actualizan ni eliminan los existentes.
            </p>
            <input
              ref={archivoRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={importar}
            />
            <Button
              className="mx-auto mt-3 max-w-full whitespace-normal"
              variant="secondary"
              icon="download"
              loading={importando}
              onClick={() => archivoRef.current?.click()}
            >
              Elegir archivo CSV
            </Button>
          </div>
        </div>

        {csvMensaje ? (
          <Alert tone={erroresCsv.length ? "error" : "success"} className="mt-4">
            {csvMensaje}
          </Alert>
        ) : null}

        {erroresCsv.length ? (
          <div className="mt-3 max-h-64 overflow-y-auto rounded-lg border border-rose-200">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-rose-50 text-rose-800">
                <tr>
                  <th className="px-3 py-2 font-semibold">Fila</th>
                  <th className="px-3 py-2 font-semibold">Qué debe corregirse</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rose-100 bg-white">
                {erroresCsv.map((error, indice) => (
                  <tr key={`${error.fila}-${indice}`}>
                    <td className="px-3 py-2 align-top font-mono text-rose-700">{error.fila}</td>
                    <td className="break-words px-3 py-2 text-stone-700">{error.mensaje}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
