import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

import { Notification, type NotificationVariant } from "@/presentation/components/Notification";

interface NotificationItem {
  id: string;
  title: string;
  description?: string;
  variant: NotificationVariant;
}

type NotifyInput = Omit<NotificationItem, "id">;

interface NotificationContextValue {
  notify: (notification: NotifyInput) => void;
}

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);
const AUTO_DISMISS_MS = 5000;

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<NotificationItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const notify = useCallback(
    (notification: NotifyInput) => {
      const id = crypto.randomUUID();
      setItems((current) => [...current, { ...notification, id }]);
      window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    },
    [dismiss],
  );

  return (
    <NotificationContext.Provider value={{ notify }}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-4 z-50 flex flex-col items-center gap-2 px-4">
        {items.map((item) => (
          <Notification key={item.id} {...item} onDismiss={() => dismiss(item.id)} />
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotifications(): NotificationContextValue {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within a NotificationProvider");
  }
  return context;
}
