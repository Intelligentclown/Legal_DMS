import type { Matter, MatterCreate } from "@/domain/types/matter";
import type { ApiEnvelope, PageParams, Paginated } from "@/domain/types/page";
import { listResource } from "@/infrastructure/api/envelope";
import { httpClient } from "@/infrastructure/api/httpClient";

const MATTERS_PATH = "/api/v1/matters";

/**
 * Requires `matters:read`.
 *
 * The backend lists Matters Organization-wide with no party filter, so the
 * client Party of each Matter is not resolved here.
 */
export async function listMatters(params?: PageParams): Promise<Paginated<Matter>> {
  return listResource<Matter>(MATTERS_PATH, params);
}

/** Requires `matters:read`. */
export async function getMatter(matterId: string): Promise<Matter> {
  const envelope = await httpClient.get<ApiEnvelope<Matter>>(`${MATTERS_PATH}/${matterId}`);
  return envelope.data;
}

/** Requires `matters:write`. `client_party_id` is the canonical Party client. */
export async function createMatter(payload: MatterCreate): Promise<Matter> {
  const envelope = await httpClient.post<ApiEnvelope<Matter>>(MATTERS_PATH, payload);
  return envelope.data;
}
