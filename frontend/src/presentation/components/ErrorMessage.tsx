import { HttpError } from "@/infrastructure/api/httpClient";

const cardClassName =
  "rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive";

export interface ErrorMessageProps {
  error: unknown;
  title?: string;
  className?: string;
}

/**
 * Renders an API or transport failure. The backend's own message is shown for
 * `HttpError` (it is already a product-level message such as "Matter with id …
 * was not found"); anything else gets a generic fallback so internal detail is
 * never surfaced unnecessarily.
 */
export function ErrorMessage({ error, title = "Request failed", className }: ErrorMessageProps) {
  if (error === null || error === undefined) {
    return null;
  }

  const message =
    error instanceof HttpError
      ? error.message
      : "Could not reach the backend API. Please try again.";

  return (
    <div role="alert" className={className ? `${cardClassName} ${className}` : cardClassName}>
      <p className="font-medium">{title}</p>
      <p className="mt-1 opacity-80">{message}</p>
    </div>
  );
}
