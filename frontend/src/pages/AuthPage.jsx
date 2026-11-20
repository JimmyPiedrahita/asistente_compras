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
    <div className="mx-auto grid min-h-screen max-w-6xl items-start gap-8 px-4 py-6 sm:py-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-16">
      <section className="text-center lg:text-left">
        <div className="inline-flex items-center gap-2 rounded-full bg-[#ffe600] px-4 py-1.5 text-xs font-bold text-stone-900">
          <Icon name="sparkles" size={14} /> Compra inteligente
        </div>
        <h1 className="mt-5 text-3xl font-bold leading-tight tracking-tight text-stone-900 sm:text-4xl lg:text-5xl">
          Arma tu lista, compara precios y compra en varios almacenes.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-stone-600">
          Busca cada producto en todos los almacenes registrados, elige la mejor opción,
          aplica cupones por almacén y finaliza con un pago. Cada almacén coordina
          su propia entrega.
        </p>
        <div className="mx-auto mt-6 grid max-w-lg grid-cols-3 gap-2.5 sm:mt-7 sm:gap-3 lg:mx-0">
          {[
            { icon: "list", title: "Tu lista", text: "Anota lo que necesitas comprar." },
            { icon: "search", title: "Compara", text: "Filtra por precio y almacén." },
            { icon: "cart", title: "Compra", text: "Un pago por todas tus compras" },
          ].map((item) => (
            <div key={item.title} className="min-w-0 rounded-2xl border border-stone-200 bg-white p-3 shadow-sm sm:p-4">
              <span className="grid h-8 w-8 place-items-center rounded-xl bg-sky-100 text-sky-700 sm:h-9 sm:w-9">
                <Icon name={item.icon} size={17} />
              </span>
              <p className="mt-2 text-xs font-semibold text-stone-900 sm:mt-3 sm:text-sm">{item.title}</p>
              <p className="mt-1 text-[11px] leading-snug text-stone-500 sm:text-xs sm:leading-relaxed">{item.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="w-full max-w-md justify-self-center rounded-2xl border border-stone-200 bg-white p-4 shadow-sm sm:p-7 lg:justify-self-end">
        <div className="mb-5 grid grid-cols-2 rounded-xl bg-stone-100 p-1">
          <button
            onClick={() => {
              setModo("login");
              setError("");
            }}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
              modo === "login" ? "bg-white text-stone-900 shadow-sm" : "text-stone-500"
            }`}
          >
            Iniciar sesión
          </button>
          <button
            onClick={() => {
              setModo("registro");
              setError("");
            }}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
              modo === "registro" ? "bg-white text-stone-900 shadow-sm" : "text-stone-500"
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
          </form>
        ) : (
          <form onSubmit={enviarRegistro} className="space-y-4">
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
            <label className="flex items-start gap-3 rounded-xl border border-stone-200 bg-stone-50 p-3 text-xs leading-relaxed text-stone-600">
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
                compra y el pago quedan registrados.
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
