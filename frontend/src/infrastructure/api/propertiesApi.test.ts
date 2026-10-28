import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/infrastructure/api/httpClient", () => ({
  httpClient: { get: vi.fn() },
}));

import { httpClient } from "@/infrastructure/api/httpClient";
import { listProperties } from "@/infrastructure/api/propertiesApi";

const mockedGet = vi.mocked(httpClient.get);

describe("listProperties", () => {
  beforeEach(() => {
    mockedGet.mockReset().mockResolvedValue({
      data: [],
      meta: { pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 } },
    });
  });

  it("forwards a non-empty server-side search alongside pagination", async () => {
    await listProperties({ page: 2, pageSize: 10, search: "REG 42" });

    expect(mockedGet).toHaveBeenCalledWith("/api/v1/properties?page=2&page_size=10&search=REG+42");
  });

  it("keeps empty and whitespace-only searches compatible with the unfiltered list", async () => {
    await listProperties({ search: "   " });

    expect(mockedGet).toHaveBeenCalledWith("/api/v1/properties?page=1&page_size=20");
  });
});
