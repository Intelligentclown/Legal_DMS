import { Loader2 } from "lucide-react";

import { cn } from "@/shared/utils/cn";

interface LoadingSpinnerProps {
  className?: string;
  label?: string;
}

export function LoadingSpinner({ className, label = "Loading…" }: LoadingSpinnerProps) {
  return (
    <div className="flex items-center gap-2 text-muted-foreground" role="status">
      <Loader2 className={cn("size-4 animate-spin", className)} aria-hidden="true" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
