import { cn } from "@/shared/utils/cn";

export const inputClassName =
  "h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50";

export const textareaClassName = cn(inputClassName, "h-auto min-h-16 py-2 leading-relaxed");

export const selectClassName = inputClassName;

export const tableClassName = "w-full border-collapse text-left text-sm";

export const headerCellClassName =
  "border-b border-border px-3 py-2 text-xs font-medium text-muted-foreground uppercase";

export const cellClassName = "border-b border-border px-3 py-2 align-top";

export const formClassName = "flex flex-col gap-4";

export const cardClassName = "rounded-lg border border-border bg-card p-4";
