import type { LegalDocument, LegalDocumentCreate } from "@/domain/types/document";
import type { ApiEnvelope, PageParams, Paginated } from "@/domain/types/page";
import { listResource } from "@/infrastructure/api/envelope";
import { httpClient } from "@/infrastructure/api/httpClient";

function documentsPath(matterId: string, fileId: string): string {
  return `/api/v1/matters/${matterId}/files/${fileId}/documents`;
}

/**
 * Requires `documents:read`.
 *
 * Only genuine File-linked Documents are reachable through this route: a
 * legacy unfiled Document is a 404 here, and T145 neither infers a File for one
 * nor reassigns an existing Document's relationships.
 */
export async function listLegalDocuments(
  matterId: string,
  fileId: string,
  params?: PageParams,
): Promise<Paginated<LegalDocument>> {
  return listResource<LegalDocument>(documentsPath(matterId, fileId), params);
}

/** Requires `documents:read`. */
export async function getLegalDocument(
  matterId: string,
  fileId: string,
  documentId: string,
): Promise<LegalDocument> {
  const envelope = await httpClient.get<ApiEnvelope<LegalDocument>>(
    `${documentsPath(matterId, fileId)}/${documentId}`,
  );
  return envelope.data;
}

/** Requires `documents:write`. `document_type_id` comes from T146's discovery route. */
export async function createLegalDocument(
  matterId: string,
  fileId: string,
  payload: LegalDocumentCreate,
): Promise<LegalDocument> {
  const envelope = await httpClient.post<ApiEnvelope<LegalDocument>>(
    documentsPath(matterId, fileId),
    payload,
  );
  return envelope.data;
}
