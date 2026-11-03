"use client";

import { removeToast, useToasts } from "@/lib/toast";

const TONE = {
  success: "border-l-low",
  error: "border-l-critical",
  info: "border-l-accent",
};

export default function Toaster() {
  const toasts = useToasts();
  return (
    <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role={t.tone === "error" ? "alert" : "status"}
          className={`pointer-events-auto flex items-start gap-3 rounded-lg border border-rule border-l-4 bg-surface px-4 py-3 text-sm shadow-lg shadow-black/5 ${TONE[t.tone] || TONE.info}`}
        >
          <p className="flex-1">{t.message}</p>
          <button
            type="button"
            onClick={() => removeToast(t.id)}
            className="text-muted hover:text-ink"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}