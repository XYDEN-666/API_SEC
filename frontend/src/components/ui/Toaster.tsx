import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Icon, { type IconName } from "../Icon";

type ToastTone = "success" | "error" | "info";

interface Toast {
  id: number;
  tone: ToastTone;
  title: string;
  message?: string;
}

interface ToastInput {
  tone?: ToastTone;
  title: string;
  message?: string;
}

interface ToastContextValue {
  push: (toast: ToastInput) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const ICONS: Record<ToastTone, IconName> = {
  success: "check",
  error: "alert",
  info: "info",
};

/** Provides transient notifications and renders the viewport itself. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    ({ tone = "info", title, message }: ToastInput) => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, tone, title, message }]);
      window.setTimeout(() => dismiss(id), tone === "error" ? 7000 : 4500);
    },
    [dismiss],
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      push,
      success: (title, message) => push({ tone: "success", title, message }),
      error: (title, message) => push({ tone: "error", title, message }),
      info: (title, message) => push({ tone: "info", title, message }),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-viewport" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast--${toast.tone}`}>
            <span className="toast__icon">
              <Icon name={ICONS[toast.tone]} size={17} />
            </span>
            <div className="stack stack--sm grow">
              <span className="toast__title">{toast.title}</span>
              {toast.message !== undefined && (
                <span className="toast__message">{toast.message}</span>
              )}
            </div>
            <button
              type="button"
              className="toast__close"
              onClick={() => dismiss(toast.id)}
              aria-label="Dismiss notification"
            >
              <Icon name="close" size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
