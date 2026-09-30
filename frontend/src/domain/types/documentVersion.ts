/**
 * Wire types for the existing canonical DocumentVersion surface
 * (`/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions`).
 *
 * `version_number` is allocated exclusively by the backend under a document row
 * lock; it is displayed exactly as returned and never predicted or generated
 * here. The backend read model exposes no size, checksum or filename — those are
 * only observable through the download response's own headers, so they are not
 * modelled as fields here rather than being guessed at.
 */
export interface DocumentVersion {
  id: string;
  version_number: number;
  change_summary: string | null;
  /** Declared `object | None` by the backend; in practice an ISO-8601 string. */
  created_at: string | null;
}
