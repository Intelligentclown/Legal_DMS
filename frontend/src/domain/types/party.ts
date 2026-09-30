/**
 * Wire types for the existing Party surface (`/api/v1/parties`).
 *
 * `party_type` is the backend's own two-value literal, not a frontend-invented
 * vocabulary. Party is the canonical reusable party identity; no legacy Client
 * concept is modelled here.
 */
export type PartyType = "individual" | "organization";

export interface Party {
  id: string;
  party_type: PartyType;
  display_name: string;
  primary_phone: string;
  primary_email: string | null;
  address_id: string | null;
  notes: string | null;
  pan_number: string | null;
  aadhaar_number: string | null;
  gstin: string | null;
  registration_identifier: string | null;
  date_of_birth: string | null;
  gender: string | null;
  occupation: string | null;
  incorporation_date: string | null;
}

/**
 * The bounded create payload T145's form needs. Optional fields the backend
 * accepts but that the smallest coherent slice does not collect are omitted
 * rather than sent as null.
 */
export interface PartyCreate {
  party_type: PartyType;
  display_name: string;
  primary_phone: string;
  primary_email?: string | null;
  notes?: string | null;
}
