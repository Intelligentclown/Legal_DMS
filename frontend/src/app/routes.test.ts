import { describe, expect, it } from "vitest";
import type { RouteObject } from "react-router-dom";

import { router } from "@/app/routes";

const T145_PATHS = [
  "parties",
  "parties/new",
  "parties/:partyId/matters/new",
  "matters",
  "matters/:matterId",
  "matters/:matterId/files/:fileId",
  "matters/:matterId/files/:fileId/documents/:documentId",
];

const guard = router.routes.filter((route) => !route.path);
const layout = guard[0]?.children?.find((route) => route.children);
const slice = (layout?.children ?? []).map((child) => child.path);

describe("router", () => {
  it("keeps login outside the authenticated guard", () => {
    expect(router.routes.filter((route) => route.path).map((route) => route.path)).toEqual([
      "/login",
    ]);
  });

  it("puts the whole T145 slice under a single pathless authenticated guard", () => {
    expect(guard).toHaveLength(1);
    expect(guard[0].element).toBeTruthy();
    expect(guard[0].path).toBeUndefined();
  });

  it("registers the Party to DocumentVersion vertical slice behind that guard", () => {
    for (const expected of T145_PATHS) {
      expect(slice).toContain(expected);
    }
  });

  it("adds no T145 route outside the guard", () => {
    const outside = router.routes
      .filter((route) => route.path)
      .flatMap((route) => [route.path ?? "", ...(route.children ?? []).map((c) => c.path ?? "")]);

    for (const path of T145_PATHS) {
      expect(outside).not.toContain(path);
    }
  });

  it("orders each list before its create form and each parent before its children", () => {
    const at = (path: string) => slice.indexOf(path);

    expect(at("parties")).toBeGreaterThanOrEqual(0);
    expect(at("parties")).toBeLessThan(at("parties/new"));
    expect(at("parties/new")).toBeLessThan(at("parties/:partyId/matters/new"));
    expect(at("matters")).toBeLessThan(at("matters/:matterId"));
    expect(at("matters/:matterId")).toBeLessThan(at("matters/:matterId/files/:fileId"));
    expect(at("matters/:matterId/files/:fileId")).toBeLessThan(
      at("matters/:matterId/files/:fileId/documents/:documentId"),
    );
  });

  it("carries the hierarchy ids in the route patterns so no id is collected from the user", () => {
    const patterns: RouteObject[] = layout?.children ?? [];
    const params = patterns.flatMap((route) => route.path?.match(/:[A-Za-z]+/g) ?? []);

    expect(new Set(params)).toEqual(new Set([":partyId", ":matterId", ":fileId", ":documentId"]));
  });
});
