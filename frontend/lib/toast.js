"use client";

import { useSyncExternalStore } from "react";

// One global toast store; <Toaster /> in the root layout renders it.
let toasts = [];
let nextId = 1;
const listeners = new Set();
const emit = () => listeners.forEach((l) => l());

export const removeToast = (id) => {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
};

export const toast = (message, tone = "info", duration = 4000) => {
  const id = nextId++;
  toasts = [...toasts, { id, message, tone }].slice(-3);
  emit();
  if (duration > 0) setTimeout(() => removeToast(id), duration);
  return id;
};

const EMPTY = [];
export function useToasts() {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => toasts,
    () => EMPTY,
  );
}