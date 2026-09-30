/**
 * Wire types for the T146 read-only reference-vocabulary discovery surface
 * (`/api/v1/matter-types`, `/api/v1/matter-statuses`, `/api/v1/document-types`).
 *
 * These project only columns that already exist on the reference tables. They
 * are read-only: no create/update/delete route exists for any of them, and
 * nothing here implies configurability, Work Type, Classification, Workflow or
 * Government Status semantics (Required ADR #15 and #12 stay unresolved).
 */
export interface MatterType {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface MatterStatus {
  id: string;
  code: string;
  name: string;
  is_terminal: boolean;
}

export interface DocumentType {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}
