import { afterEach, describe, expect, it, vi, type Mock } from "vitest";

import { HttpError, httpClient } from "@/infrastructure/api/httpClient";

interface FakeResponse {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
}

function stubFetch(response: FakeResponse): Mock {
  const mockFetch = vi.fn().mockResolvedValue(response as unknown as Response);
  vi.stubGlobal("fetch", mockFetch);
  return mockFetch;
}

const OK_RESPONSE: FakeResponse = {
  ok: true,
  status: 200,
  json: () => Promise.resolve({ id: "1" }),
};

describe("httpClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("HTTP verbs", () => {
    it("get() issues a GET request", async () => {
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.get("/widgets/1");

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(init.method ?? "GET").toBe("GET");
    });

    it("post() issues a POST request with a JSON-serialized body", async () => {
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.post("/widgets", { name: "gadget" });

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(init.method).toBe("POST");
      expect(init.body).toBe(JSON.stringify({ name: "gadget" }));
    });

    it("put() issues a PUT request with a JSON-serialized body", async () => {
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.put("/widgets/1", { name: "renamed" });

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(init.method).toBe("PUT");
      expect(init.body).toBe(JSON.stringify({ name: "renamed" }));
    });

    it("delete() issues a DELETE request", async () => {
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.delete("/widgets/1");

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(init.method).toBe("DELETE");
    });
  });

  describe("error handling", () => {
    it("populates HttpError's code and message from a structured error body", async () => {
      stubFetch({
        ok: false,
        status: 409,
        json: () =>
          Promise.resolve({ error: { code: "CONFLICT", message: "Email already in use" } }),
      });

      const error: unknown = await httpClient.get("/users").catch((e: unknown) => e);

      expect(error).toBeInstanceOf(HttpError);
      const httpError = error as HttpError;
      expect(httpError.status).toBe(409);
      expect(httpError.code).toBe("CONFLICT");
      expect(httpError.message).toBe("Email already in use");
    });

    it("falls back to the generic message when the body doesn't match the structured shape", async () => {
      stubFetch({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: "boom" }),
      });

      const error: unknown = await httpClient.get("/users").catch((e: unknown) => e);

      expect(error).toBeInstanceOf(HttpError);
      const httpError = error as HttpError;
      expect(httpError.status).toBe(500);
      expect(httpError.code).toBeUndefined();
      expect(httpError.message).toBe("Request to /users failed with status 500");
    });

    it("falls back to the generic message when the response body isn't parseable JSON", async () => {
      stubFetch({
        ok: false,
        status: 502,
        json: () => Promise.reject(new SyntaxError("Unexpected token")),
      });

      const error: unknown = await httpClient.get("/users").catch((e: unknown) => e);

      expect(error).toBeInstanceOf(HttpError);
      const httpError = error as HttpError;
      expect(httpError.status).toBe(502);
      expect(httpError.code).toBeUndefined();
      expect(httpError.message).toBe("Request to /users failed with status 502");
    });

    it("doesn't crash and still throws when the error body is a non-object JSON value", async () => {
      stubFetch({
        ok: false,
        status: 400,
        json: () => Promise.resolve("plain string body"),
      });

      const error: unknown = await httpClient.get("/users").catch((e: unknown) => e);

      expect(error).toBeInstanceOf(HttpError);
      const httpError = error as HttpError;
      expect(httpError.status).toBe(400);
      expect(httpError.code).toBeUndefined();
      expect(httpError.message).toBe("Request to /users failed with status 400");
    });
  });
});
