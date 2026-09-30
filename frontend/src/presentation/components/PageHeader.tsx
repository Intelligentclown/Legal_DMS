import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  description?: string;
  children?: ReactNode;
}

/** Shared page heading block, optionally with actions or breadcrumbs beside it. */
export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-sm font-medium text-foreground">{title}</h2>
        {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
      </div>
      {children ? <div className="flex items-center gap-2">{children}</div> : null}
    </div>
  );
}
