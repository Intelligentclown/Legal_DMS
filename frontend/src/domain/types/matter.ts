/**
 * Wire types for the existing Party-canonical Matter surface
 * (`/api/v1/matters`).
 *
 * `client_party_id` is the backend's own canonical client relationship to a
 * Party. `legacy_client_id` is a read-only legacy `clients.id` column surfaced
 * by the backend for visibility only; it is never a create input here and
 * never drives a frontend master. Matter Type and Matter Status stay the
 * existing reference vocabularies — no Work Type or Classification is implied.
 */
export interface MatterParticipant {
  party_id: string;
  role: string;
}

export interface Matter {
  id: string;
  matter_number: string;
  matter_type_id: string;
  matter_status_id: string;
  title: string;
  description: string | null;
  opened_at: string;
  closed_at: string | null;
  legacy_client_id: string | null;
  participants: MatterParticipant[];
}

export interface MatterCreate {
  matter_number: string;
  matter_type_id: string;
  matter_status_id: string;
  title: string;
  description?: string | null;
  opened_at: string;
  client_party_id: string;
}
