import { cn } from "@/shared/utils/cn";

export type NotificationVariant = "info" | "success" | "error";

interface NotificationProps {
  title: string;
  description?: string;
  variant: NotificationVariant;
  onDismiss: () => void;
}

const variantStyles: Record<NotificationVariant, string> = {
  info: "border-border bg-card text-card-foreground",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  error: "border-destructive/40 bg-destructive/10 text-destructive",
};

export function Notification({ title, description, variant, onDismiss }: NotificationProps) {
  return (
    <div
      role="alert"
      className={cn(
        "pointer-events-auto w-full max-w-sm rounded-lg border px-4 py-3 shadow-lg",
        variantStyles[variant],
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium">{title}</p>
          {description ? <p className="mt-1 text-sm opacity-80">{description}</p> : null}
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="text-sm opacity-60 hover:opacity-100"
          aria-label="Dismiss notification"
        >
          &times;
        </button>
      </div>
    </div>
  );
}
