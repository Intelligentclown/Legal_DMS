import type { DocumentType, MatterStatus, MatterType } from "@/domain/types/lookup";
import type { ApiEnvelope } from "@/domain/types/page";
import { httpClient } from "@/infrastructure/api/httpClient";

/**
 * T146's read-only reference-vocabulary discovery, used to populate the Matter
 * Type, Matter Status and Document Type selectors with human-readable choices
 * instead of requiring an internal UUID to be entered. These collections are
 * global reference data, are not Organization-scoped, and are not paginated.
 */

/** Requires `matters:read`. */
export async function listMatterTypes(): Promise<MatterType[]> {
  const envelope = await httpClient.get<ApiEnvelope<MatterType[]>>("/api/v1/matter-types");
  return envelope.data;
}

/** Requires `matters:read`. */
export async function listMatterStatuses(): Promise<MatterStatus[]> {
  const envelope = await httpClient.get<ApiEnvelope<MatterStatus[]>>("/api/v1/matter-statuses");
  return envelope.data;
}

/** Requires `documents:read`. */
export async function listDocumentTypes(): Promise<DocumentType[]> {
  const envelope = await httpClient.get<ApiEnvelope<DocumentType[]>>("/api/v1/document-types");
  return envelope.data;
}
