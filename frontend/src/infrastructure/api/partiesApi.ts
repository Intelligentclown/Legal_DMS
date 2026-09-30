import type { Party, PartyCreate } from "@/domain/types/party";
import type { ApiEnvelope, PageParams, Paginated } from "@/domain/types/page";
import { listResource } from "@/infrastructure/api/envelope";
import { httpClient } from "@/infrastructure/api/httpClient";

const PARTIES_PATH = "/api/v1/parties";

/** Requires `parties:read`. */
export async function listParties(params?: PageParams): Promise<Paginated<Party>> {
  return listResource<Party>(PARTIES_PATH, params);
}

/** Requires `parties:read`. Returns 404 for an unknown or other-Organization id. */
export async function getParty(partyId: string): Promise<Party> {
  const envelope = await httpClient.get<ApiEnvelope<Party>>(`${PARTIES_PATH}/${partyId}`);
  return envelope.data;
}

/** Requires `parties:write`. Returns 201 with the created Party. */
export async function createParty(payload: PartyCreate): Promise<Party> {
  const envelope = await httpClient.post<ApiEnvelope<Party>>(PARTIES_PATH, payload);
  return envelope.data;
}
