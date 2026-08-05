import { describe, expect, it } from "vitest";

import { err, isErr, isOk, ok } from "@/domain/types/result";

describe("Result", () => {
  it("ok() creates a success result", () => {
    const result = ok(42);

    expect(result.success).toBe(true);
    expect(isOk(result)).toBe(true);
    expect(isErr(result)).toBe(false);
  });

  it("err() creates a failure result", () => {
    const result = err("something went wrong");

    expect(result.success).toBe(false);
    expect(isErr(result)).toBe(true);
    expect(isOk(result)).toBe(false);
  });

  it("isOk narrows the type so .value is accessible", () => {
    const result = ok<number>(7);

    if (isOk(result)) {
      expect(result.value).toBe(7);
    } else {
      throw new Error("expected isOk to be true");
    }
  });

  it("isErr narrows the type so .error is accessible", () => {
    const result = err<number, string>("bad");

    if (isErr(result)) {
      expect(result.error).toBe("bad");
    } else {
      throw new Error("expected isErr to be true");
    }
  });
});
