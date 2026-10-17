import type {
  Acceptance,
  AcceptanceMatterCreate,
  Enquiry,
  EnquiryCreate,
  EnquiryFields,
  Quotation,
  QuotationRevision,
} from "@/domain/types/enquiry";
import type { ApiEnvelope, PageParams, Paginated } from "@/domain/types/page";
import { listResource } from "@/infrastructure/api/envelope";
import { httpClient } from "@/infrastructure/api/httpClient";

const ENQUIRIES_PATH = "/api/v1/enquiries";

export function listEnquiries(params?: PageParams): Promise<Paginated<Enquiry>> {
  return listResource<Enquiry>(ENQUIRIES_PATH, params);
}

export async function getEnquiry(enquiryId: string): Promise<Enquiry> {
  return (await httpClient.get<ApiEnvelope<Enquiry>>(`${ENQUIRIES_PATH}/${enquiryId}`)).data;
}

export async function createEnquiry(payload: EnquiryCreate): Promise<Enquiry> {
  return (await httpClient.post<ApiEnvelope<Enquiry>>(ENQUIRIES_PATH, payload)).data;
}

export async function updateEnquiry(enquiryId: string, payload: EnquiryFields): Promise<Enquiry> {
  return (await httpClient.put<ApiEnvelope<Enquiry>>(`${ENQUIRIES_PATH}/${enquiryId}`, payload))
    .data;
}

export async function linkEnquiryParty(enquiryId: string, partyId: string): Promise<Enquiry> {
  return (
    await httpClient.put<ApiEnvelope<Enquiry>>(`${ENQUIRIES_PATH}/${enquiryId}/party`, {
      party_id: partyId,
    })
  ).data;
}

export function listQuotations(
  enquiryId: string,
  params?: PageParams,
): Promise<Paginated<Quotation>> {
  return listResource<Quotation>(`${ENQUIRIES_PATH}/${enquiryId}/quotations`, params);
}

export async function getQuotation(enquiryId: string, quotationId: string): Promise<Quotation> {
  return (
    await httpClient.get<ApiEnvelope<Quotation>>(
      `${ENQUIRIES_PATH}/${enquiryId}/quotations/${quotationId}`,
    )
  ).data;
}

export async function createQuotation(enquiryId: string): Promise<Quotation> {
  return (
    await httpClient.post<ApiEnvelope<Quotation>>(`${ENQUIRIES_PATH}/${enquiryId}/quotations`)
  ).data;
}

export async function listQuotationRevisions(
  enquiryId: string,
  quotationId: string,
): Promise<QuotationRevision[]> {
  return (
    await httpClient.get<ApiEnvelope<QuotationRevision[]>>(
      `${ENQUIRIES_PATH}/${enquiryId}/quotations/${quotationId}/revisions`,
    )
  ).data;
}

export async function createQuotationRevision(
  enquiryId: string,
  quotationId: string,
  proposalSnapshot: Record<string, unknown>,
): Promise<QuotationRevision> {
  return (
    await httpClient.post<ApiEnvelope<QuotationRevision>>(
      `${ENQUIRIES_PATH}/${enquiryId}/quotations/${quotationId}/revisions`,
      { proposal_snapshot: proposalSnapshot },
    )
  ).data;
}

export async function issueQuotationRevision(
  enquiryId: string,
  quotationId: string,
  revisionId: string,
): Promise<QuotationRevision> {
  return (
    await httpClient.post<ApiEnvelope<QuotationRevision>>(
      `${ENQUIRIES_PATH}/${enquiryId}/quotations/${quotationId}/revisions/${revisionId}/issue`,
    )
  ).data;
}

export async function acceptQuotationRevision(
  enquiryId: string,
  quotationId: string,
  revisionId: string,
  payload: AcceptanceMatterCreate,
  idempotencyKey: string,
): Promise<{ acceptance: Acceptance; status: number }> {
  const response = await httpClient.postWithResponse<ApiEnvelope<Acceptance>>(
    `${ENQUIRIES_PATH}/${enquiryId}/quotations/${quotationId}/revisions/${revisionId}/accept`,
    payload,
    { headers: { "Idempotency-Key": idempotencyKey } },
  );
  return { acceptance: response.data.data, status: response.status };
}
