import { useState } from "react";
import { Link } from "react-router-dom";

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
import { listParties } from "@/infrastructure/api/partiesApi";

function displayType(partyType: "individual" | "organization"): string {
  return partyType === "individual" ? "Individual" : "Organization";
}

/**
 * Browses the Organization's Parties. Selecting a Party is what makes it the
 * canonical client for a new Matter, so each row links straight into that flow
 * rather than to an identifier the user would have to copy.
 */
export function PartiesPage() {
  const [page, setPage] = useState(1);
  const resource = useAsyncResource(`parties:${page}`, () => listParties({ page }));

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <PageHeader
        title="Parties"
        description="People and organizations this practice acts for. A party is the canonical client recorded on a matter."
      >
        <Button asChild size="sm">
          <Link to="/parties/new">New party</Link>
        </Button>
      </PageHeader>

      <ErrorMessage error={resource.error} title="Could not load parties" />

      {resource.isLoading ? <LoadingSpinner label="Loading parties…" /> : null}

      {resource.data ? (
        resource.data.items.length === 0 ? (
          <EmptyState
            title="No parties yet"
            description="Create the first party to start working on a matter."
          >
            <Button asChild size="sm">
              <Link to="/parties/new">New party</Link>
            </Button>
          </EmptyState>
        ) : (
          <>
            <table className={tableClassName}>
              <thead>
                <tr>
                  <th className={headerCellClassName}>Name</th>
                  <th className={headerCellClassName}>Type</th>
                  <th className={headerCellClassName}>Phone</th>
                  <th className={headerCellClassName}>Email</th>
                  <th className={headerCellClassName}>Action</th>
                </tr>
              </thead>
              <tbody>
                {resource.data.items.map((party) => (
                  <tr key={party.id}>
                    <td className={`${cellClassName} font-medium text-foreground`}>
                      {party.display_name}
                    </td>
                    <td className={cellClassName}>{displayType(party.party_type)}</td>
                    <td className={cellClassName}>{party.primary_phone}</td>
                    <td className={cellClassName}>{party.primary_email ?? "—"}</td>
                    <td className={cellClassName}>
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/parties/${party.id}/matters/new`}>New matter</Link>
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
