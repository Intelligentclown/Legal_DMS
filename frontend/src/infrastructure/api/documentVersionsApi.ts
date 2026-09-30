import type { DocumentVersion } from "@/domain/types/documentVersion";
import type { ApiEnvelope } from "@/domain/types/page";
import { buildQuery } from "@/infrastructure/api/envelope";
import { httpClient, HttpError, type BinaryResponse } from "@/infrastructure/api/httpClient";

function versionsPath(matterId: string, fileId: string, documentId: string): string {
  return `/api/v1/matters/${matterId}/files/${fileId}/documents/${documentId}/versions`;
}

export interface CreateDocumentVersionInput {
  content: Blob | ArrayBuffer;
  /** Sent as the required `X-Filename` header; the backend replays it on download. */
  filename: string;
  /** Sent as `Content-Type`; the backend stores and replays it as the MIME type. */
  mimeType: string;
  /** Optional `Idempotency-Key`; a repeat with identical bytes replays the same version. */
  idempotencyKey?: string;
  changeSummary?: string;
}

/**
 * Uploads an immutable version using the backend's existing contract: the raw
 * file bytes as the request body (not multipart), `X-Filename` as a required
 * header, `Idempotency-Key` optional, and `change_summary` as a query
 * parameter. The backend allocates the version number; nothing is computed
 * client-side.
 */
export async function createDocumentVersion(
  matterId: string,
  fileId: string,
  documentId: string,
  input: CreateDocumentVersionInput,
): Promise<DocumentVersion> {
  const path = `${versionsPath(matterId, fileId, documentId)}${buildQuery({
    change_summary: input.changeSummary,
  })}`;

  const headers: Record<string, string> = { "X-Filename": input.filename };
  if (input.idempotencyKey) {
    headers["Idempotency-Key"] = input.idempotencyKey;
  }

  const envelope = await httpClient.postBinary<ApiEnvelope<DocumentVersion>>(path, input.content, {
    contentType: input.mimeType,
    headers,
  });

  return envelope.data;
}

/** Requires `documents:read`. Not paginated by the backend. */
export async function listDocumentVersions(
  matterId: string,
  fileId: string,
  documentId: string,
): Promise<DocumentVersion[]> {
  const envelope = await httpClient.get<ApiEnvelope<DocumentVersion[]>>(
    versionsPath(matterId, fileId, documentId),
  );
  return envelope.data;
}

/**
 * Requires `documents:read`.
 *
 * The backend returns 404 when a Document has no committed version yet, which
 * is a normal empty state rather than a failure, so it is surfaced as `null`.
 * Any other failure still propagates.
 */
export async function getLatestDocumentVersion(
  matterId: string,
  fileId: string,
  documentId: string,
): Promise<DocumentVersion | null> {
  try {
    const envelope = await httpClient.get<ApiEnvelope<DocumentVersion>>(
      `${versionsPath(matterId, fileId, documentId)}/latest`,
    );
    return envelope.data;
  } catch (error) {
    if (error instanceof HttpError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

/**
 * Requires `documents:read`. The backend re-verifies the stored bytes on read
 * and fails closed on a mismatch; that surfaces here as an ordinary API failure
 * and is not reproduced client-side.
 */
export async function downloadDocumentVersion(
  matterId: string,
  fileId: string,
  documentId: string,
  versionId: string,
): Promise<BinaryResponse> {
  return httpClient.getBinary(`${versionsPath(matterId, fileId, documentId)}/${versionId}/content`);
}
