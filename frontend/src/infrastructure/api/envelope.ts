import { httpClient } from "@/infrastructure/api/httpClient";
import { normalizePageParams } from "@/domain/types/page";
import type { ApiEnvelope, PageParams, Paginated } from "@/domain/types/page";

/** Serializes optional query parameters, omitting anything not supplied. */
export function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      search.set(key, String(value));
    }
  }

  const query = search.toString();
  return query ? `?${query}` : "";
}

/**
 * Calls a paginated list route and unwraps the backend's `ApiResponse` envelope.
 * The backend's own `page`/`page_size` bounds are clamped before sending.
 */
export async function listResource<T>(path: string, params?: PageParams): Promise<Paginated<T>> {
  const { page, pageSize } = normalizePageParams(params);
  const envelope = await httpClient.get<ApiEnvelope<T[]>>(
    `${path}${buildQuery({ page, page_size: pageSize })}`,
  );

  return { items: envelope.data, pagination: envelope.meta?.pagination ?? null };
}
