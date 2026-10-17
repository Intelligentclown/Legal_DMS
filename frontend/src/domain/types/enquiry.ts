export interface Enquiry {
  id: string;
  party_id: string | null;
  prospect_display_name: string | null;
  prospect_phone: string | null;
  prospect_email: string | null;
  prospect_description: string | null;
  prospect_source: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface EnquiryFields {
  prospect_display_name?: string | null;
  prospect_phone?: string | null;
  prospect_email?: string | null;
  prospect_description?: string | null;
  prospect_source?: string | null;
}

export interface EnquiryCreate extends EnquiryFields {
  party_id?: string | null;
}

export interface Quotation {
  id: string;
  enquiry_id: string;
  created_at: string | null;
}

export interface QuotationRevision {
  id: string;
  quotation_id: string;
  ordinal: number;
  proposal_snapshot: Record<string, unknown>;
  issued_at: string | null;
  issued_by: string | null;
  created_at: string | null;
}

export interface AcceptanceMatterCreate {
  matter_number: string;
  matter_type_id: string;
  matter_status_id: string;
  title: string;
  description: string | null;
  opened_at: string;
}

export interface Acceptance {
  id: string;
  matter_id: string;
  quotation_revision_id: string;
  replayed: boolean;
}
