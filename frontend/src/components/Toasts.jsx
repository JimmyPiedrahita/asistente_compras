import Icon from "./Icon";
import { useApp } from "../context/AppContext";

const styles = {
  success: {
    icon: "check",
    iconClass: "text-emerald-600",
    border: "border-slate-200",
  },
  error: {
    icon: "alert",
    iconClass: "text-rose-600",
    border: "border-rose-200",
  },
  info: {
    icon: "sparkles",
    iconClass: "text-slate-500",
    border: "border-slate-200",
  },
};

export default function Toasts() {
  const { toasts, dismissToast } = useApp();

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2">
      {toasts.map((toast) => {
        const style = styles[toast.type] || styles.info;
        return (
          <div
            key={toast.id}
            className={`animate-toast pointer-events-auto flex items-start gap-3 rounded-lg border bg-white p-3.5 ${style.border}`}
            role="status"
          >
            <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-md bg-slate-100">
              <Icon name={style.icon} size={15} className={style.iconClass} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                {toast.title}
              </p>
              <p className="mt-0.5 break-words text-sm text-slate-700">{toast.message}</p>
            </div>
            <button
              onClick={() => dismissToast(toast.id)}
              className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              aria-label="Cerrar aviso"
            >
              <Icon name="x" size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
