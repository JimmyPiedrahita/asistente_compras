import { useState } from "react";
import Icon from "./Icon";
import { useApp } from "../context/AppContext";

export function Spinner({ size = 16, className = "" }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={`animate-spin ${className}`}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

const buttonVariants = {
  primary: "bg-slate-900 text-white hover:bg-slate-800 active:bg-black",
  secondary:
    "border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50",
  ghost: "text-slate-500 hover:bg-slate-100 hover:text-slate-900",
  danger: "bg-rose-700 text-white hover:bg-rose-800 active:bg-rose-900",
  dangerSoft:
    "border border-slate-200 bg-white text-rose-700 hover:border-rose-300 hover:text-rose-800",
  success: "bg-slate-900 text-white hover:bg-slate-800",
  dark: "bg-slate-900 text-white hover:bg-slate-800",
};

const buttonSizes = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2.5 text-sm",
  lg: "px-5 py-3 text-sm",
};

export function Button({
  children,
  variant = "primary",
  size = "md",
  icon,
  iconRight,
  loading = false,
  className = "",
  disabled,
  type = "button",
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/10 disabled:cursor-not-allowed disabled:opacity-40 ${buttonVariants[variant]} ${buttonSizes[size]} ${className}`}
      {...props}
    >
      {loading ? <Spinner size={size === "sm" ? 13 : 15} /> : icon ? <Icon name={icon} size={size === "sm" ? 14 : 16} /> : null}
      {children}
      {iconRight && !loading ? (
        <Icon name={iconRight} size={size === "sm" ? 14 : 16} />
      ) : null}
    </button>
  );
}

export function Card({ title, description, actions, children, className = "", bodyClassName = "" }) {
  return (
    <section
      className={`overflow-hidden rounded-xl border border-slate-200 bg-white ${className}`}
    >
      {(title || description || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
          <div className="min-w-0">
            {title && (
              <h2 className="text-sm font-semibold tracking-tight text-slate-900">{title}</h2>
            )}
            {description && (
              <p className="mt-0.5 text-xs text-slate-500">{description}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={`p-5 sm:p-6 ${bodyClassName}`}>{children}</div>
    </section>
  );
}

export function Field({ label, hint, children, className = "", htmlFor }) {
  return (
    <label htmlFor={htmlFor} className={`block ${className}`}>
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </span>
      {children}
      {hint && <span className="mt-1.5 block text-xs text-slate-400">{hint}</span>}
    </label>
  );
}

const controlClasses =
  "w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900/5 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400";

export function Input({ className = "", ...props }) {
  return <input className={`${controlClasses} ${className}`} {...props} />;
}

export function Select({ className = "", children, ...props }) {
  return (
    <select className={`${controlClasses} ${className}`} {...props}>
      {children}
    </select>
  );
}

export function Textarea({ className = "", rows = 5, ...props }) {
  return (
    <textarea rows={rows} className={`${controlClasses} font-mono text-xs leading-relaxed ${className}`} {...props} />
  );
}

const badgeTones = {
  slate: "bg-slate-100 text-slate-600 ring-slate-200",
  indigo: "bg-slate-900 text-white ring-slate-900",
  violet: "bg-slate-900 text-white ring-slate-900",
  emerald: "bg-white text-emerald-700 ring-slate-200",
  amber: "bg-white text-amber-700 ring-slate-200",
  rose: "bg-white text-rose-700 ring-rose-200",
  sky: "bg-slate-100 text-slate-600 ring-slate-200",
  dark: "bg-slate-900 text-white ring-slate-900",
};

export function Badge({ children, tone = "slate", className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${badgeTones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Stat({ label, value, hint, icon }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-slate-400">
            {label}
          </p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
          {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
        </div>
        {icon && (
          <span className="rounded-lg bg-slate-100 p-2 text-slate-500">
            <Icon name={icon} size={18} />
          </span>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ icon = "sparkles", title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/40 px-6 py-10 text-center">
      <span className="rounded-lg border border-slate-200 bg-white p-3 text-slate-400">
        <Icon name={icon} size={22} />
      </span>
      <h3 className="mt-3 text-sm font-medium text-slate-700">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

const alertTones = {
  info: {
    box: "border-slate-200 bg-slate-50/60 text-slate-700",
    icon: "text-slate-500",
  },
  success: {
    box: "border-slate-200 bg-white text-slate-700",
    icon: "text-emerald-600",
  },
  warning: {
    box: "border-slate-200 bg-white text-slate-700",
    icon: "text-amber-600",
  },
  error: {
    box: "border-rose-200 bg-white text-slate-700",
    icon: "text-rose-600",
  },
};

export function Alert({ tone = "info", title, children, className = "" }) {
  const style = alertTones[tone] || alertTones.info;
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${style.box} ${className}`}>
      <div className="flex items-start gap-2.5">
        <Icon
          name={tone === "success" ? "check" : tone === "error" || tone === "warning" ? "alert" : "sparkles"}
          size={16}
          className={`mt-0.5 shrink-0 ${style.icon}`}
        />
        <div className="min-w-0">
          {title && <p className="font-medium text-slate-900">{title}</p>}
          {children && <div className={title ? "mt-0.5" : ""}>{children}</div>}
        </div>
      </div>
    </div>
  );
}

export function CopyButton({ value, label = "Copiar" }) {
  const { notify } = useApp();
  return (
    <Button
      size="sm"
      variant="secondary"
      icon="copy"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          notify("Copiado al portapapeles.", "success", "Portapapeles");
        } catch {
          notify("El navegador no permitió copiar.", "error");
        }
      }}
    >
      {label}
    </Button>
  );
}

export function JsonBlock({ data, label = "Respuesta JSON" }) {
  if (data === undefined) return null;
  return (
    <details className="group mt-4 rounded-xl border border-slate-200 bg-slate-50">
      <summary className="cursor-pointer select-none px-4 py-2.5 text-xs font-semibold text-slate-500 transition hover:text-slate-700">
        {label}
      </summary>
      <pre className="scroll-thin max-h-64 overflow-auto border-t border-slate-200 p-4 font-mono text-[11px] leading-relaxed text-slate-700">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
}

export function NeedSession({ onNavigate, title = "Necesitas una sesión activa" }) {
  return (
    <Card>
      <EmptyState
        icon="key"
        title={title}
        description="Crea una sesión de cliente, proveedor o administrador para consumir los endpoints protegidos."
        action={
          <Button icon="key" onClick={() => onNavigate?.("sesion")}>
            Ir a sesiones
          </Button>
        }
      />
    </Card>
  );
}

export function NeedPermission({ onNavigate, session, permission, title }) {
  const detail = session?.descripcion_rol
    ? ` ${session.descripcion_rol}`
    : " Consulta el catálogo de roles para ver qué acciones permite cada uno.";
  return (
    <Card>
      <EmptyState
        icon="shield"
        title={title || "Tu rol no permite esta acción"}
        description={
          session
            ? `La sesión de ${session.usuario} tiene el rol ${session.rol}${
                permission ? ` y no incluye el permiso "${permission}"` : ""
              }.${detail}`
            : `Inicia una sesión con un rol que incluya${
                permission ? ` "${permission}"` : " esta función"
              }.`
        }
        action={
          <Button icon="shield" onClick={() => onNavigate?.("roles")}>
            Ver roles y permisos
          </Button>
        }
      />
    </Card>
  );
}

export function NeedAdmin({ onNavigate, session }) {
  return (
    <Card>
      <EmptyState
        icon="shield"
        title="Esta sección requiere rol ADMIN"
        description={
          session
            ? `La sesión actual es de ${session.usuario} (${session.rol}). Cierra sesión e inicia una administrativa.`
            : "Inicia sesión con la clave de administrador para gestionar inventarios y el comparador."
        }
        action={
          <Button icon="shield" onClick={() => onNavigate?.("sesion")}>
            Ir a sesiones
          </Button>
        }
      />
    </Card>
  );
}

export function ProductTypeBadge({ tipo }) {
  return <Badge tone="slate">{tipo}</Badge>;
}

export function Money({ value }) {
  return (
    <span className="tabular-nums">
      {new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "COP",
        maximumFractionDigits: 2,
      }).format(Number(value || 0))}
    </span>
  );
}

export function useAsyncAction() {
  const [loading, setLoading] = useState(false);
  const run = async (fn) => {
    setLoading(true);
    try {
      return await fn();
    } finally {
      setLoading(false);
    }
  };
  return [loading, run];
}
