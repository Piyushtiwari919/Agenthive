import React, { createContext, useCallback, useContext, useState } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

interface ToastItem {
  id: string;
  type: "success" | "error" | "info";
  title: string;
  message?: string;
}

interface ToastContextValue {
  notify: (type: ToastItem["type"], title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const notify = useCallback((type: ToastItem["type"], title: string, message?: string) => {
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md w-full pointer-events-none px-4"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-lg border shadow-xl backdrop-blur-md ${
              t.type === "error"
                ? "bg-rose-950/95 border-rose-700 text-rose-100"
                : t.type === "success"
                ? "bg-emerald-950/95 border-emerald-700 text-emerald-100"
                : "bg-slate-900/95 border-indigo-700 text-slate-100"
            }`}
          >
            {t.type === "error" ? (
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            ) : t.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
            )}
            <div className="flex-1 text-xs">
              <div className="font-semibold text-sm">{t.title}</div>
              {t.message && <div className="mt-0.5 opacity-90">{t.message}</div>}
            </div>
            <button
              onClick={() => dismiss(t.id)}
              aria-label="Close notification"
              className="text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return ctx;
}