import { useCallback, useSyncExternalStore } from "react";

/*
 * Global toast store. The old hook kept toasts in each page's local state
 * and nothing rendered them, so every showToast() was a no-op. Pages now
 * push into one shared store and <Toaster /> (in Layout) renders it.
 */
let toasts = [];
let nextId = 1;
const listeners = new Set();

const emit = () => listeners.forEach((l) => l());

const subscribe = (listener) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

const getSnapshot = () => toasts;

export const removeToast = (id) => {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
};

export const showToast = (message, type = "info", duration = 3000) => {
  const id = nextId++;
  toasts = [...toasts, { id, message, type }].slice(-4);
  emit();
  if (duration > 0) setTimeout(() => removeToast(id), duration);
  return id;
};

export function useToastStore() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export function useToast() {
  const toastList = useToastStore();
  const show = useCallback((message, type, duration) => showToast(message, type, duration), []);
  const remove = useCallback((id) => removeToast(id), []);
  return { toasts: toastList, showToast: show, removeToast: remove };
}