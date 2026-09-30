import { describe, expect, it } from "vitest";

import { normalizePageParams } from "@/domain/types/page";

/**
 * The backend's `PageRequest` raises a bare `ValueError` — a 500, not a 422 —
 * for `page < 1` or `page_size` outside `1..100`, so the bounds are enforced
 * before the request is sent.
 */
describe("normalizePageParams", () => {
  it("defaults to the first page with the default page size", () => {
    expect(normalizePageParams()).toEqual({ page: 1, pageSize: 20 });
  });

  it("passes through in-range values", () => {
    expect(normalizePageParams({ page: 3, pageSize: 50 })).toEqual({ page: 3, pageSize: 50 });
  });

  it("raises a page below 1 to the first page", () => {
    expect(normalizePageParams({ page: 0 }).page).toBe(1);
    expect(normalizePageParams({ page: -5 }).page).toBe(1);
  });

  it("clamps a page size above the backend maximum", () => {
    expect(normalizePageParams({ pageSize: 1000 }).pageSize).toBe(100);
  });

  it("raises a page size below 1 to the backend minimum", () => {
    expect(normalizePageParams({ pageSize: 0 }).pageSize).toBe(1);
    expect(normalizePageParams({ pageSize: -10 }).pageSize).toBe(1);
  });

  it("floors fractional values and falls back to defaults for non-numbers", () => {
    expect(normalizePageParams({ page: 2.9, pageSize: 10.7 })).toEqual({ page: 2, pageSize: 10 });
    expect(normalizePageParams({ page: Number.NaN, pageSize: Number.NaN })).toEqual({
      page: 1,
      pageSize: 20,
    });
  });
});
