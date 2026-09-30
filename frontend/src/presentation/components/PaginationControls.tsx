import { Button } from "@/presentation/components/ui/button";

export interface PaginationControlsProps {
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
}

const labelClassName = "text-xs text-muted-foreground";

/**
 * Drives the backend's own `page`/`page_size` query parameters. The backend
 * reports `total_pages` as 0 when there is nothing to page through, so the
 * control stays inert in that case.
 */
export function PaginationControls({
  page,
  totalPages,
  total,
  onPageChange,
  isLoading = false,
}: PaginationControlsProps) {
  const hasPrevious = page > 1;
  const hasNext = page < totalPages;

  return (
    <div className="flex items-center gap-3">
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={!hasPrevious || isLoading}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      <span className={labelClassName}>
        Page {page} of {Math.max(totalPages, 1)} · {total} total
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={!hasNext || isLoading}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </div>
  );
}
