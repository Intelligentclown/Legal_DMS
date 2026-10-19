import type { PageParams, Paginated } from "@/domain/types/page";
import type { Property } from "@/domain/types/property";
import { listResource } from "@/infrastructure/api/envelope";

const PROPERTIES_PATH = "/api/v1/properties";

/** Requires `properties:read`; this is the existing tenant-scoped paginated Property API. */
export async function listProperties(params?: PageParams): Promise<Paginated<Property>> {
  return listResource<Property>(PROPERTIES_PATH, params);
}
