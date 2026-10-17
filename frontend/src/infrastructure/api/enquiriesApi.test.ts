import { afterEach, describe, expect, it, vi } from "vitest";

import {
  acceptQuotationRevision,
  createQuotationRevision,
} from "@/infrastructure/api/enquiriesApi";

function response(status: number, data: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  } as Response;
}

describe("enquiriesApi", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts an exact revision acceptance with its Idempotency-Key and preserves 201", async () => {
    const fetch = vi.fn().mockResolvedValue(
      response(201, {
        data: { id: "a1", matter_id: "m1", quotation_revision_id: "r1", replayed: false },
      }),
    );
    vi.stubGlobal("fetch", fetch);

    const result = await acceptQuotationRevision(
      "e1",
      "q1",
      "r1",
      {
        matter_number: "M-1",
        matter_type_id: "type",
        matter_status_id: "status",
        title: "Matter",
        description: null,
        opened_at: "2026-10-17T10:00:00.000Z",
      },
      "stable-key",
    );

    expect(result.status).toBe(201);
    expect(result.acceptance.matter_id).toBe("m1");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/enquiries/e1/quotations/q1/revisions/r1/accept"),
      expect.objectContaining({
        headers: expect.objectContaining({ "Idempotency-Key": "stable-key" }),
      }),
    );
  });

  it("preserves HTTP 200 for a same-key replay", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(200, {
          data: { id: "a1", matter_id: "m1", quotation_revision_id: "r1", replayed: true },
        }),
      ),
    );

    const result = await acceptQuotationRevision(
      "e1",
      "q1",
      "r1",
      {
        matter_number: "M-1",
        matter_type_id: "type",
        matter_status_id: "status",
        title: "Matter",
        description: null,
        opened_at: "2026-10-17T10:00:00.000Z",
      },
      "stable-key",
    );

    expect(result.status).toBe(200);
    expect(result.acceptance.replayed).toBe(true);
  });

  it("does not reshape a proposal snapshot before submitting it", async () => {
    const fetch = vi.fn().mockResolvedValue(response(201, { data: { id: "r1" } }));
    vi.stubGlobal("fetch", fetch);

    await createQuotationRevision("e1", "q1", {
      scope: { text: "Advice" },
      fee_note: "Quoted separately",
    });

    const [, init] = fetch.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(
      JSON.stringify({
        proposal_snapshot: { scope: { text: "Advice" }, fee_note: "Quoted separately" },
      }),
    );
  });
});
