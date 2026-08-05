import { describe, expect, it } from "vitest";

import { createPageRequest, DEFAULT_PAGE_SIZE } from "@/shared/types/query";

describe("createPageRequest", () => {
  it("defaults to page 1 with the default page size", () => {
    expect(createPageRequest()).toEqual({ page: 1, pageSize: DEFAULT_PAGE_SIZE });
  });

  it("applies overrides", () => {
    expect(createPageRequest({ page: 3 })).toEqual({ page: 3, pageSize: DEFAULT_PAGE_SIZE });
    expect(createPageRequest({ pageSize: 50 })).toEqual({ page: 1, pageSize: 50 });
  });
});
