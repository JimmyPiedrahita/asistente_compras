import { useState } from "react";
import Icon from "../components/Icon";
import { Alert, Button, Field, Input } from "../components/ui";
import { useApp } from "../context/AppContext";

const initialRegister = {
  nombre: "",
  email: "",
  password: "",
  password_confirmacion: "",
  telefono: "",
  direccion: "",
  ciudad: "",
  autoriza_datos: false,
};

export default function AuthPage() {
  const { login, register, notifyError } = useApp();
  const [modo, setModo] = useState("login");
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [registro, setRegistro] = useState(initialRegister);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const enviarLogin = async (evento) => {
    evento.preventDefault();
    setCargando(true);
    setError("");
    try {
      await login(loginForm.email, loginForm.password);
    } catch (err) {
      setError("Credenciales incorrectas");
      notifyError(err);
    } finally {
      setCargando(false);
    }
  };

  const enviarRegistro = async (evento) => {
    evento.preventDefault();
    setCargando(true);
    setError("");
    if (registro.password !== registro.password_confirmacion) {
      setError("La contraseña y su confirmación no coinciden");
      setCargando(false);
      return;
    }
    if (!registro.autoriza_datos) {
      setError("Debes autorizar el tratamiento de tus datos personales");
      setCargando(false);
      return;
    }
    try {
      await register(registro);
    } catch (err) {
      setError(err.message || "No se pudo completar el registro");
      notifyError(err);
    } finally {
      setCargando(false);
    }
  };

  const campo = (nombre) => ({
    value: registro[nombre],
    onChange: (evento) =>
      setRegistro((actual) => ({
        ...actual,
        [nombre]:
          evento.target.type === "checkbox" ? evento.target.checked : evento.target.value,
      })),
  });

  return (
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-8 px-4 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:py-16">
      <section>
        <div className="inline-flex items-center gap-2 rounded-full bg-[#ffe600] px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-slate-900">
          <Icon name="sparkles" size={14} /> Compra inteligente
        </div>
        <h1 className="mt-5 text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl">
          Arma tu lista, compara precios y compra en varios almacenes.
        </h1>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-slate-600">
          Busca cada producto en todos los almacenes registrados, elige la mejor opción,
          aplica cupones por almacén y finaliza con un pago simulado. Cada almacén coordina
          su propia entrega.
        </p>
        <div className="mt-7 grid gap-3 sm:grid-cols-3">
          {[
            { icon: "list", title: "Tu lista", text: "Anota lo que necesitas comprar." },
            { icon: "search", title: "Compara", text: "Filtra por precio y almacén." },
            { icon: "cart", title: "Compra", text: "Pago simulado, sin cobros reales." },
          ].map((item) => (
            <div key={item.title} className="rounded-xl border border-slate-200 bg-white p-4">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-[#e8f1ff] text-[#3483fa]">
                <Icon name={item.icon} size={18} />
              </span>
              <p className="mt-3 text-sm font-semibold text-slate-900">{item.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">{item.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
        <div className="mb-5 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
          <button
            onClick={() => {
              setModo("login");
              setError("");
            }}
            className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
              modo === "login" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
            }`}
          >
            Iniciar sesión
          </button>
          <button
            onClick={() => {
              setModo("registro");
              setError("");
            }}
            className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
              modo === "registro" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
            }`}
          >
            Crear cuenta
          </button>
        </div>

        {error && (
          <Alert tone="error" className="mb-4">
            {error}
          </Alert>
        )}

        {modo === "login" ? (
          <form onSubmit={enviarLogin} className="space-y-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Ingresa a tu cuenta</h2>
              <p className="mt-1 text-sm text-slate-500">
                Una sola pantalla para clientes, administradores de almacén y de la aplicación.
              </p>
            </div>
            <Field label="Correo electrónico" htmlFor="login-email">
              <Input
                id="login-email"
                type="email"
                autoComplete="email"
                required
                value={loginForm.email}
                onChange={(evento) =>
                  setLoginForm((actual) => ({ ...actual, email: evento.target.value }))
                }
                placeholder="tu@correo.com"
              />
            </Field>
            <Field label="Contraseña" htmlFor="login-password">
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                required
                value={loginForm.password}
                onChange={(evento) =>
                  setLoginForm((actual) => ({ ...actual, password: evento.target.value }))
                }
                placeholder="Tu contraseña"
              />
            </Field>
            <Button type="submit" size="lg" className="w-full" loading={cargando}>
              Entrar
            </Button>
            <p className="text-center text-xs text-slate-500">
              El registro público es solo para clientes. Las cuentas administrativas las crea el
              administrador de la aplicación.
            </p>
          </form>
        ) : (
          <form onSubmit={enviarRegistro} className="space-y-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Crea tu cuenta de cliente</h2>
              <p className="mt-1 text-sm text-slate-500">
                Necesitamos estos datos para registrar tus compras y compartirlos con los
                almacenes que participen en tu entrega.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Nombre" htmlFor="reg-nombre" className="sm:col-span-2">
                <Input id="reg-nombre" required autoComplete="name" {...campo("nombre")} />
              </Field>
              <Field label="Correo electrónico" htmlFor="reg-email">
                <Input id="reg-email" type="email" required autoComplete="email" {...campo("email")} />
              </Field>
              <Field label="Teléfono de contacto" htmlFor="reg-telefono">
                <Input id="reg-telefono" required autoComplete="tel" {...campo("telefono")} />
              </Field>
              <Field label="Contraseña" htmlFor="reg-password">
                <Input
                  id="reg-password"
                  type="password"
                  required
                  minLength={6}
                  autoComplete="new-password"
                  {...campo("password")}
                />
              </Field>
              <Field label="Confirmar contraseña" htmlFor="reg-password2">
                <Input
                  id="reg-password2"
                  type="password"
                  required
                  minLength={6}
                  autoComplete="new-password"
                  {...campo("password_confirmacion")}
                />
              </Field>
              <Field label="Dirección de entrega" htmlFor="reg-direccion" className="sm:col-span-2">
                <Input id="reg-direccion" required autoComplete="street-address" {...campo("direccion")} />
              </Field>
              <Field label="Ciudad o municipio" htmlFor="reg-ciudad" className="sm:col-span-2">
                <Input id="reg-ciudad" required autoComplete="address-level2" {...campo("ciudad")} />
              </Field>
            </div>
            <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">
              <input
                type="checkbox"
                required
                checked={registro.autoriza_datos}
                onChange={(evento) =>
                  setRegistro((actual) => ({
                    ...actual,
                    autoriza_datos: evento.target.checked,
                  }))
                }
                className="mt-0.5 h-4 w-4 accent-[#3483fa]"
              />
              <span>
                Autorizo el tratamiento de mis datos personales y su comunicación con los
                almacenes incluidos en mis compras, únicamente para gestionar la entrega. La
                compra y el pago son simulados.
              </span>
            </label>
            <Button type="submit" size="lg" className="w-full" loading={cargando}>
              Crear cuenta
            </Button>
          </form>
        )}
      </section>
    </div>
  );
}
