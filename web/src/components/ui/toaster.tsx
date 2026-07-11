import * as React from 'react';
import * as ToastPrimitive from '@radix-ui/react-toast';

import { cn } from '@/lib/utils';
import { dismissToast, subscribeToasts } from '@/lib/toast';

export interface ToastOptions {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
  duration?: number;
}

export function Toaster() {
  const [items, setItems] = React.useState<ToastOptions[]>([]);

  React.useEffect(() => {
    const unsubscribe = subscribeToasts(setItems);
    return () => {
      unsubscribe();
    };
  }, []);

  return (
    <ToastPrimitive.Provider swipeDirection="right">
      {items.map((item) => (
        <ToastPrimitive.Root
          key={item.id}
          open
          onOpenChange={(open) => {
            if (!open) dismissToast(item.id);
          }}
          className={cn(
            'group pointer-events-auto relative flex w-full items-center justify-between gap-4 overflow-hidden rounded-md border p-4 pr-6 shadow-lg transition-all',
            item.variant === 'destructive'
              ? 'border-destructive bg-destructive text-destructive-foreground'
              : 'border bg-background text-foreground'
          )}
        >
          <div className="grid gap-1">
            <ToastPrimitive.Title className="text-sm font-semibold">
              {item.title}
            </ToastPrimitive.Title>
            {item.description && (
              <ToastPrimitive.Description className="text-sm opacity-90">
                {item.description}
              </ToastPrimitive.Description>
            )}
          </div>
          <ToastPrimitive.Close
            onClick={() => dismissToast(item.id)}
            className="absolute right-1 top-1 rounded-md p-1 opacity-0 transition-opacity hover:bg-black/10 focus:opacity-100 group-hover:opacity-100"
            aria-label="关闭"
          >
            <span aria-hidden className="text-lg leading-none">
              &times;
            </span>
          </ToastPrimitive.Close>
        </ToastPrimitive.Root>
      ))}
      <ToastPrimitive.Viewport className="fixed bottom-0 right-0 z-[100] flex max-w-[420px] flex-col gap-2 p-4 outline-none" />
    </ToastPrimitive.Provider>
  );
}
