"use client";

import { useEffect, useRef } from "react";

// Native <dialog>: focus trapping, Esc and the backdrop come for free.
export default function Modal({ open, onClose, title, children, wide = false }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      className={`m-auto w-[calc(100vw-2rem)] rounded-2xl border border-rule bg-surface p-0 text-ink backdrop:bg-ink/40 ${
        wide ? "max-w-2xl" : "max-w-md"
      }`}
    >
      {open && (
        <div className="p-6">
          <div className="mb-4 flex items-start justify-between gap-4">
            <h2 className="text-xl font-semibold break-words">{title}</h2>
            <button type="button" onClick={onClose} aria-label="Close" className="text-muted hover:text-ink">
              ✕
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}