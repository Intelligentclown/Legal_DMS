import type { ReactNode } from "react";

export interface DetailItem {
  label: string;
  value: ReactNode;
}

export interface DetailListProps {
  items: DetailItem[];
}

/** Read-only "label: value" summary used at the top of each detail page. */
export function DetailList({ items }: DetailListProps) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="flex flex-col gap-0.5">
          <dt className="text-xs font-medium text-muted-foreground uppercase">{item.label}</dt>
          <dd className="text-sm break-words text-foreground">
            {item.value === null || item.value === undefined || item.value === ""
              ? "—"
              : item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
