import { useState } from "react";
import { Link } from "react-router-dom";

import { listMatters } from "@/infrastructure/api/mattersApi";
import { EmptyState } from "@/presentation/components/EmptyState";
import { ErrorMessage } from "@/presentation/components/ErrorMessage";
import { LoadingSpinner } from "@/presentation/components/LoadingSpinner";
import { PageHeader } from "@/presentation/components/PageHeader";
import { PaginationControls } from "@/presentation/components/PaginationControls";
import {
  cellClassName,
  headerCellClassName,
  tableClassName,
} from "@/presentation/components/form/styles";
import { useAsyncResource } from "@/presentation/hooks/useAsyncResource";
import { Button } from "@/presentation/components/ui/button";

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

/** Organization-wide Matter index; the backend applies no party filter. */
export function MattersPage() {
  const [page, setPage] = useState(1);
  const resource = useAsyncResource(`matters:${page}`, () => listMatters({ page }));

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <PageHeader
        title="Matters"
        description="Every matter in this organization, newest identifiers included as recorded by the backend."
      />

      <ErrorMessage error={resource.error} title="Could not load matters" />

      {resource.isLoading ? <LoadingSpinner label="Loading matters…" /> : null}

      {resource.data ? (
        resource.data.items.length === 0 ? (
          <EmptyState
            title="No matters yet"
            description="Start from a party and open a matter for it."
          >
            <Button asChild size="sm">
              <Link to="/parties">Go to parties</Link>
            </Button>
          </EmptyState>
        ) : (
          <>
            <table className={tableClassName}>
              <thead>
                <tr>
                  <th className={headerCellClassName}>Matter number</th>
                  <th className={headerCellClassName}>Title</th>
                  <th className={headerCellClassName}>Opened</th>
                  <th className={headerCellClassName}>Closed</th>
                  <th className={headerCellClassName}>Action</th>
                </tr>
              </thead>
              <tbody>
                {resource.data.items.map((matter) => (
                  <tr key={matter.id}>
                    <td className={`${cellClassName} font-medium text-foreground`}>
                      {matter.matter_number}
                    </td>
                    <td className={cellClassName}>{matter.title}</td>
                    <td className={cellClassName}>{formatDate(matter.opened_at)}</td>
                    <td className={cellClassName}>
                      {matter.closed_at ? formatDate(matter.closed_at) : "—"}
                    </td>
                    <td className={cellClassName}>
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/matters/${matter.id}`}>Open</Link>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {resource.data.pagination ? (
              <PaginationControls
                page={resource.data.pagination.page}
                totalPages={resource.data.pagination.total_pages}
                total={resource.data.pagination.total}
                onPageChange={setPage}
                isLoading={resource.isLoading}
              />
            ) : null}
          </>
        )
      ) : null}
    </div>
  );
}
