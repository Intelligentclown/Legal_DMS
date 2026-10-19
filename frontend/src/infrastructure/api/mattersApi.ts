import type { Matter, MatterCreate } from "@/domain/types/matter";
import type { Property } from "@/domain/types/property";
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

function matterPropertiesPath(matterId: string): string {
  return `${MATTERS_PATH}/${matterId}/properties`;
}

/** Requires `matters:read` and `properties:read`. */
export async function listMatterProperties(matterId: string): Promise<Property[]> {
  const envelope = await httpClient.get<ApiEnvelope<Property[]>>(matterPropertiesPath(matterId));
  return envelope.data;
}

export interface MatterPropertyLinkResult {
  property: Property;
  /** `false` means the backend returned its documented 200 idempotent response. */
  created: boolean;
}

/** Requires `matters:write` and `properties:read`; accepts documented 201 and idempotent 200. */
export async function linkMatterProperty(
  matterId: string,
  propertyId: string,
): Promise<MatterPropertyLinkResult> {
  const response = await httpClient.postWithResponse<ApiEnvelope<Property>>(
    matterPropertiesPath(matterId),
    { property_id: propertyId },
  );
  return { property: response.data.data, created: response.status === 201 };
}

/** Requires `matters:write` and `properties:read`; removes only the association. */
export async function unlinkMatterProperty(matterId: string, propertyId: string): Promise<void> {
  await httpClient.delete<void>(`${matterPropertiesPath(matterId)}/${propertyId}`);
}
