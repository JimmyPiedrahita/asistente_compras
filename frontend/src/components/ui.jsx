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
  primary: "bg-stone-900 text-white hover:bg-stone-800 active:bg-stone-950 shadow-sm",
  secondary:
    "border border-stone-200 bg-white text-stone-700 hover:border-stone-300 hover:bg-stone-50",
  ghost: "text-stone-500 hover:bg-stone-100 hover:text-stone-900",
  danger: "bg-rose-700 text-white hover:bg-rose-800 active:bg-rose-900 shadow-sm",
  dangerSoft:
    "border border-stone-200 bg-white text-rose-700 hover:border-rose-300 hover:text-rose-800",
  success: "bg-stone-900 text-white hover:bg-stone-800 shadow-sm",
  dark: "bg-stone-900 text-white hover:bg-stone-800 shadow-sm",
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
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stone-900/10 disabled:cursor-not-allowed disabled:opacity-40 ${buttonVariants[variant]} ${buttonSizes[size]} ${className}`}
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
      className={`overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm ${className}`}
    >
      {(title || description || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-stone-100 px-5 py-4 sm:px-6">
          <div className="min-w-0">
            {title && (
              <h2 className="text-base font-semibold text-stone-900">{title}</h2>
            )}
            {description && (
              <p className="mt-1 text-sm text-stone-500">{description}</p>
            )}
          </div>
          {actions && (
            <div className="flex min-w-0 w-full shrink-0 flex-wrap items-center gap-2 sm:w-auto">
              {actions}
            </div>
          )}
        </header>
      )}
      <div className={`p-5 sm:p-6 ${bodyClassName}`}>{children}</div>
    </section>
  );
}

export function Field({ label, hint, children, className = "", htmlFor }) {
  return (
    <label htmlFor={htmlFor} className={`block ${className}`}>
      <span className="mb-1 block text-sm font-medium text-stone-600">
        {label}
      </span>
      {children}
      {hint && <span className="mt-1 block text-xs text-stone-400">{hint}</span>}
    </label>
  );
}

const controlClasses =
  "w-full rounded-xl border border-stone-200 bg-white px-3.5 py-2.5 text-sm text-stone-900 placeholder:text-stone-400 transition focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900/10 disabled:cursor-not-allowed disabled:bg-stone-50 disabled:text-stone-400";

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
    <textarea rows={rows} className={`${controlClasses} ${className}`} {...props} />
  );
}

const badgeTones = {
  slate: "bg-stone-100 text-stone-600 ring-stone-200",
  indigo: "bg-sky-600 text-white ring-sky-600",
  violet: "bg-violet-600 text-white ring-violet-600",
  emerald: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  amber: "bg-amber-50 text-amber-700 ring-amber-200",
  rose: "bg-rose-50 text-rose-700 ring-rose-200",
  sky: "bg-sky-50 text-sky-700 ring-sky-200",
  dark: "bg-stone-900 text-white ring-stone-900",
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
    <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-stone-500">
            {label}
          </p>
          <p className="mt-1 text-2xl font-bold text-stone-900">{value}</p>
          {hint && <p className="mt-1 text-xs text-stone-400">{hint}</p>}
        </div>
        {icon && (
          <span className="rounded-xl bg-stone-100 p-2.5 text-stone-500">
            <Icon name={icon} size={18} />
          </span>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ icon = "sparkles", title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-stone-200 bg-stone-50/50 px-6 py-10 text-center">
      <span className="rounded-xl bg-stone-100 p-3 text-stone-400">
        <Icon name={icon} size={22} />
      </span>
      <h3 className="mt-3 text-sm font-semibold text-stone-700">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-stone-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

const alertTones = {
  info: {
    box: "border-sky-200 bg-sky-50 text-sky-800",
    icon: "text-sky-600",
  },
  success: {
    box: "border-emerald-200 bg-emerald-50 text-emerald-800",
    icon: "text-emerald-600",
  },
  warning: {
    box: "border-amber-200 bg-amber-50 text-amber-800",
    icon: "text-amber-600",
  },
  error: {
    box: "border-rose-200 bg-rose-50 text-rose-800",
    icon: "text-rose-600",
  },
};

export function Alert({ tone = "info", title, children, className = "" }) {
  const style = alertTones[tone] || alertTones.info;
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${style.box} ${className}`}>
      <div className="flex items-start gap-2.5">
        <Icon
          name={tone === "success" ? "check" : tone === "error" || tone === "warning" ? "alert" : "sparkles"}
          size={16}
          className={`mt-0.5 shrink-0 ${style.icon}`}
        />
        <div className="min-w-0">
          {title && <p className="font-semibold">{title}</p>}
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

export function NeedSession({ title = "Inicia sesión para continuar" }) {
  return (
    <Card>
      <EmptyState
        icon="key"
        title={title}
        description="Inicia sesión para acceder a esta sección."
      />
    </Card>
  );
}

export function NeedPermission({ session, permission, title }) {
  return (
    <Card>
      <EmptyState
        icon="shield"
        title={title || "Esta función no está disponible"}
        description={
          session
            ? `Tu cuenta (${session.usuario}) no tiene acceso a esta función. Contacta al administrador si necesitas este permiso.`
            : "Esta función requiere una cuenta con los permisos adecuados."
        }
      />
    </Card>
  );
}

export function NeedAdmin({ session }) {
  return (
    <Card>
      <EmptyState
        icon="shield"
        title="Esta sección requiere acceso de administrador"
        description={
          session
            ? `Tu cuenta actual (${session.usuario}) no tiene permisos de administrador.`
            : "Esta sección solo está disponible para administradores."
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
