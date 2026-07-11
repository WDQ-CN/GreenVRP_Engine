import type { ToastOptions } from '@/components/ui/toaster';

type Listener = (toasts: ToastOptions[]) => void;

const listeners: Set<Listener> = new Set();
let toasts: ToastOptions[] = [];

export function notify() {
  listeners.forEach((listener) => listener([...toasts]));
}

export function toast(options: Omit<ToastOptions, 'id'>) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  const newToast: ToastOptions = { ...options, id };
  toasts = [...toasts, newToast];
  notify();

  window.setTimeout(() => {
    dismissToast(id);
  }, options.duration ?? 5000);

  return id;
}

export function dismissToast(id: string) {
  toasts = toasts.filter((t) => t.id !== id);
  notify();
}

export function subscribeToasts(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
