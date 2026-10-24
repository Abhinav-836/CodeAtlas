import { useToastStore, removeToast } from "../../hooks/useToast";

const STYLES = {
  success: "bg-green-600",
  error: "bg-red-600",
  warning: "bg-yellow-500",
  info: "bg-blue-600",
};

export default function Toaster() {
  const toasts = useToastStore();
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 left-4 sm:left-auto z-[60] flex flex-col gap-2 sm:w-96"
      role="status"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`${STYLES[t.type] || STYLES.info} text-white px-4 py-3 rounded-lg shadow-lg flex items-start justify-between gap-3`}
        >
          <span className="text-sm break-words">{t.message}</span>
          <button
            onClick={() => removeToast(t.id)}
            className="text-white/80 hover:text-white leading-none"
            aria-label="Dismiss notification"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}