import { useState } from "react";
import { Link } from "react-router-dom";

import { listEnquiries } from "@/infrastructure/api/enquiriesApi";
import { Button } from "@/presentation/components/ui/button";
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

/** Organization-scoped pre-engagement index. Party names are resolved only on detail to avoid guessing identity. */
export function EnquiriesPage() {
  const [page, setPage] = useState(1);
  const resource = useAsyncResource(`enquiries:${page}`, () => listEnquiries({ page }));

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <PageHeader
        title="Enquiries"
        description="Prospective engagements before quotation and acceptance."
      >
        <Button asChild size="sm">
          <Link to="/enquiries/new">New enquiry</Link>
        </Button>
      </PageHeader>
      <ErrorMessage error={resource.error} title="Could not load enquiries" />
      {resource.isLoading ? <LoadingSpinner label="Loading enquiries…" /> : null}
      {resource.data ? (
        resource.data.items.length === 0 ? (
          <EmptyState
            title="No enquiries yet"
            description="Record a prospective engagement to begin."
          >
            <Button asChild size="sm">
              <Link to="/enquiries/new">New enquiry</Link>
            </Button>
          </EmptyState>
        ) : (
          <>
            <table className={tableClassName}>
              <thead>
                <tr>
                  <th className={headerCellClassName}>Prospect</th>
                  <th className={headerCellClassName}>Party linked</th>
                  <th className={headerCellClassName}>Source</th>
                  <th className={headerCellClassName}>Action</th>
                </tr>
              </thead>
              <tbody>
                {resource.data.items.map((enquiry) => (
                  <tr key={enquiry.id}>
                    <td className={`${cellClassName} font-medium text-foreground`}>
                      {enquiry.prospect_display_name ?? "Party-linked enquiry"}
                    </td>
                    <td className={cellClassName}>{enquiry.party_id ? "Yes" : "No"}</td>
                    <td className={cellClassName}>{enquiry.prospect_source ?? "—"}</td>
                    <td className={cellClassName}>
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/enquiries/${enquiry.id}`}>Open</Link>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {resource.data.pagination ? (
              <PaginationControls
                page={resource.data.pagination.page}
                total={resource.data.pagination.total}
                totalPages={resource.data.pagination.total_pages}
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
