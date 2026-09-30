/**
 * Wire types for the existing File-canonical Document surface
 * (`/api/v1/matters/{matter_id}/files/{file_id}/documents`).
 *
 * Named `LegalDocument` because `Document` is a DOM global. Note the backend's
 * read model carries neither `matter_id` nor `file_id`: those live only in the
 * route, so the frontend keeps the hierarchy context it navigated with. `status`
 * is the backend's own free-form column; T145 does not add a status vocabulary,
 * so create uses the backend default.
 */
export interface LegalDocument {
  id: string;
  document_type_id: string;
  title: string;
  status: string;
  version: number;
}

export interface LegalDocumentCreate {
  document_type_id: string;
  title: string;
}
