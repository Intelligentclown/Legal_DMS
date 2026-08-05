/**
 * Pagination/filter/sort/search request and response shapes, mirroring the
 * backend's query framework (`backend/src/app/application/common/pagination.py`
 * and `query.py`) so a future page listing paginated resources already has
 * matching types to deserialize the backend's `ApiResponse` envelope into.
 */

export const DEFAULT_PAGE_SIZE = 20;

export interface PageRequest {
  page: number;
  pageSize: number;
}

export function createPageRequest(overrides: Partial<PageRequest> = {}): PageRequest {
  return { page: 1, pageSize: DEFAULT_PAGE_SIZE, ...overrides };
}

export interface PaginationMeta {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: { pagination: PaginationMeta } | null;
}

export type SortDirection = "asc" | "desc";

export interface SortSpec {
  field: string;
  direction: SortDirection;
}

export type FilterOperator = "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "contains" | "in";

export interface FilterSpec {
  field: string;
  operator: FilterOperator;
  value: unknown;
}

export interface SearchQuery {
  page: PageRequest;
  q?: string;
  filters: FilterSpec[];
  sort: SortSpec[];
}
