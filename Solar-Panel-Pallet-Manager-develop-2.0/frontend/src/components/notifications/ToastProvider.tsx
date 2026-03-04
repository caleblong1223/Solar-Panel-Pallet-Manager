import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

type ToastLevel = "success" | "warning" | "error";

type Toast = {
  id: string;
  message: string;
  level: ToastLevel;
};

type ToastContextValue = {
  notify: (message: string, level?: ToastLevel) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((message: string, level: ToastLevel = "success") => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { id, message, level }]);

    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 3000);
  }, []);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite" aria-label="Notifications">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast--${toast.level}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}
