/**
 * Wire types for the existing Matter-scoped File surface
 * (`/api/v1/matters/{matter_id}/files`).
 *
 * Named `MatterFile` because `File` is a DOM global. `file_number` is
 * allocated exclusively by the backend (ADR-0027); it is displayed exactly as
 * returned and is never predicted or generated here. `version` is the backend's
 * optimistic-lock counter, not a document version.
 */
export interface MatterFile {
  id: string;
  matter_id: string;
  file_number: number;
  title: string;
  version: number;
}

export interface MatterFileCreate {
  title: string;
}
