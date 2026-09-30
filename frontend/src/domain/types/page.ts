/**
 * The backend's shared `ApiResponse[T]` envelope
 * (`backend/src/app/presentation/common/response.py`): always a `data` field,
 * with `meta` non-null only for paginated list routes.
 */
export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: { pagination: PaginationMeta } | null;
}

/** An unwrapped page: the route's items plus its pagination metadata. */
export interface Paginated<T> {
  items: T[];
  pagination: PaginationMeta | null;
}

export interface PageParams {
  page?: number;
  pageSize?: number;
}

const DEFAULT_PAGE_SIZE = 20;
const MAX_PAGE_SIZE = 100;

/**
 * The backend's `PageRequest` raises a bare `ValueError` (surfacing as a 500,
 * not a 422) for `page < 1` or `page_size` outside `1..100`, so the bounds are
 * clamped here rather than sent and rejected.
 */
export function normalizePageParams(params: PageParams = {}): Required<PageParams> {
  const page = Number.isFinite(params.page) ? Math.floor(params.page as number) : 1;
  const pageSize = Number.isFinite(params.pageSize)
    ? Math.floor(params.pageSize as number)
    : DEFAULT_PAGE_SIZE;

  return {
    page: Math.max(1, page),
    pageSize: Math.min(MAX_PAGE_SIZE, Math.max(1, pageSize)),
  };
}
