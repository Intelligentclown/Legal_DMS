import type { MatterFile, MatterFileCreate } from "@/domain/types/matterFile";
import type { ApiEnvelope, PageParams, Paginated } from "@/domain/types/page";
import { listResource } from "@/infrastructure/api/envelope";
import { httpClient } from "@/infrastructure/api/httpClient";

function filesPath(matterId: string): string {
  return `/api/v1/matters/${matterId}/files`;
}

/**
 * Requires `files:read`.
 *
 * `file_number` in the returned items is backend-allocated and is displayed
 * verbatim; it is never computed here.
 */
export async function listMatterFiles(
  matterId: string,
  params?: PageParams,
): Promise<Paginated<MatterFile>> {
  return listResource<MatterFile>(filesPath(matterId), params);
}

/** Requires `files:read`. */
export async function getMatterFile(matterId: string, fileId: string): Promise<MatterFile> {
  const envelope = await httpClient.get<ApiEnvelope<MatterFile>>(
    `${filesPath(matterId)}/${fileId}`,
  );
  return envelope.data;
}

/** Requires `files:write`. Only `title` is accepted; the backend allocates the number. */
export async function createMatterFile(
  matterId: string,
  payload: MatterFileCreate,
): Promise<MatterFile> {
  const envelope = await httpClient.post<ApiEnvelope<MatterFile>>(filesPath(matterId), payload);
  return envelope.data;
}
