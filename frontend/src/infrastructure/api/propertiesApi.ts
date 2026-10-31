import { normalizePageParams } from "@/domain/types/page";
import type { ApiEnvelope, PageParams, Paginated } from "@/domain/types/page";
import type { Property } from "@/domain/types/property";
import { buildQuery } from "@/infrastructure/api/envelope";
import { httpClient } from "@/infrastructure/api/httpClient";

const PROPERTIES_PATH = "/api/v1/properties";

export interface PropertyListParams extends PageParams {
  search?: string;
}

/** Requires `properties:read`; this is the existing tenant-scoped paginated Property API. */
export async function listProperties(params?: PropertyListParams): Promise<Paginated<Property>> {
  const { page, pageSize } = normalizePageParams(params);
  const search = params?.search?.trim() || undefined;
  const envelope = await httpClient.get<ApiEnvelope<Property[]>>(
    `${PROPERTIES_PATH}${buildQuery({ page, page_size: pageSize, search })}`,
  );

  return { items: envelope.data, pagination: envelope.meta?.pagination ?? null };
}
