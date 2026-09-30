import type { ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  description?: string;
  children?: ReactNode;
}

const cardClassName =
  "rounded-lg border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground";

/** Shown in place of a list that loaded successfully but has nothing in it. */
export function EmptyState({ title, description, children }: EmptyStateProps) {
  return (
    <div className={cardClassName}>
      <p className="font-medium text-foreground">{title}</p>
      {description ? <p className="mt-1">{description}</p> : null}
      {children ? <div className="mt-3 flex justify-center">{children}</div> : null}
    </div>
  );
}
