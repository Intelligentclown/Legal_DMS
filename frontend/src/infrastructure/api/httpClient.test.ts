import { afterEach, describe, expect, it, vi, type Mock } from "vitest";

vi.mock("@/infrastructure/ipc/ipcBridge", () => ({
  ipcBridge: {
    isAvailable: vi.fn(),
    clearRefreshToken: vi.fn(),
  },
}));

import {
  HttpError,
  httpClient,
  setAccessToken,
  setUnauthorizedHandler,
} from "@/infrastructure/api/httpClient";
import { ipcBridge } from "@/infrastructure/ipc/ipcBridge";

const mockedIsAvailable = ipcBridge.isAvailable as unknown as Mock;
const mockedClearRefreshToken = ipcBridge.clearRefreshToken as unknown as Mock;

interface FakeResponse {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
  blob?: () => Promise<Blob>;
  headers?: { get: (name: string) => string | null };
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

const UNAUTHORIZED_RESPONSE: FakeResponse = {
  ok: false,
  status: 401,
  json: () => Promise.resolve({ error: { code: "UNAUTHORIZED", message: "Invalid token" } }),
};

const DOWNLOAD_HEADERS: Record<string, string> = {
  "Content-Type": "application/pdf",
  "Content-Disposition": 'attachment; filename="deed.pdf"',
};

const BINARY_RESPONSE: FakeResponse = {
  ok: true,
  status: 200,
  json: () => Promise.resolve({ data: { id: "v1", version_number: 1 } }),
  blob: () => Promise.resolve(new Blob(["%PDF-1.7"])),
  headers: { get: (name) => DOWNLOAD_HEADERS[name] ?? null },
};

describe("httpClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setAccessToken(null);
    setUnauthorizedHandler(null);
    mockedIsAvailable.mockReset();
    mockedClearRefreshToken.mockReset();
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

  describe("raw-byte upload", () => {
    it("sends the bytes as the request body without JSON-serializing them", async () => {
      const mockFetch = stubFetch(BINARY_RESPONSE);
      const bytes = new Uint8Array([1, 2, 3]).buffer;

      await httpClient.postBinary("/versions", bytes, { contentType: "application/pdf" });

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(init.method).toBe("POST");
      expect(init.body).toBe(bytes);
    });

    it("sends the caller's Content-Type over the JSON default", async () => {
      const mockFetch = stubFetch(BINARY_RESPONSE);

      await httpClient.postBinary("/versions", new Uint8Array([1]).buffer, {
        contentType: "application/pdf",
      });

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("application/pdf");
    });

    it("defaults to application/octet-stream so the backend is never told it is JSON", async () => {
      const mockFetch = stubFetch(BINARY_RESPONSE);

      await httpClient.postBinary("/versions", new Uint8Array([1]).buffer);

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("application/octet-stream");
    });

    it("forwards the required X-Filename and optional Idempotency-Key headers", async () => {
      const mockFetch = stubFetch(BINARY_RESPONSE);

      await httpClient.postBinary("/versions", new Uint8Array([1]).buffer, {
        headers: { "X-Filename": "deed.pdf", "Idempotency-Key": "key-1" },
      });

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers["X-Filename"]).toBe("deed.pdf");
      expect(headers["Idempotency-Key"]).toBe("key-1");
    });

    it("omits Idempotency-Key entirely when the caller does not supply one", async () => {
      const mockFetch = stubFetch(BINARY_RESPONSE);

      await httpClient.postBinary("/versions", new Uint8Array([1]).buffer, {
        headers: { "X-Filename": "deed.pdf" },
      });

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers["X-Filename"]).toBe("deed.pdf");
      expect(headers).not.toHaveProperty("Idempotency-Key");
    });

    it("still attaches the bearer token on a raw-byte upload", async () => {
      setAccessToken("abc123");
      const mockFetch = stubFetch(BINARY_RESPONSE);

      await httpClient.postBinary("/versions", new Uint8Array([1]).buffer);

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers.Authorization).toBe("Bearer abc123");
    });

    it("converts a failed raw-byte upload into a structured HttpError", async () => {
      stubFetch({
        ok: false,
        status: 409,
        json: () =>
          Promise.resolve({ error: { code: "CONFLICT", message: "Idempotency key reused" } }),
      });

      const error: unknown = await httpClient
        .postBinary("/versions", new Uint8Array([1]).buffer)
        .catch((e: unknown) => e);

      expect(error).toBeInstanceOf(HttpError);
      expect((error as HttpError).status).toBe(409);
      expect((error as HttpError).message).toBe("Idempotency key reused");
    });
  });

  describe("binary download", () => {
    it("returns the bytes plus the Content-Type and Content-Disposition headers", async () => {
      stubFetch(BINARY_RESPONSE);

      const result = await httpClient.getBinary("/versions/v1/content");

      expect(await result.blob.text()).toBe("%PDF-1.7");
      expect(result.contentType).toBe("application/pdf");
      expect(result.contentDisposition).toBe('attachment; filename="deed.pdf"');
    });

    it("issues a GET request", async () => {
      const mockFetch = stubFetch(BINARY_RESPONSE);

      await httpClient.getBinary("/versions/v1/content");

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(init.method).toBe("GET");
    });

    it("attaches the bearer token on a download", async () => {
      setAccessToken("abc123");
      const mockFetch = stubFetch(BINARY_RESPONSE);

      await httpClient.getBinary("/versions/v1/content");

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers.Authorization).toBe("Bearer abc123");
    });

    it("converts a failed download into a structured HttpError", async () => {
      stubFetch({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: { code: "NOT_FOUND", message: "Version not found" } }),
      });

      const error: unknown = await httpClient
        .getBinary("/versions/v1/content")
        .catch((e: unknown) => e);

      expect(error).toBeInstanceOf(HttpError);
      expect((error as HttpError).status).toBe(404);
      expect((error as HttpError).message).toBe("Version not found");
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

  describe("204 No Content", () => {
    it("resolves without throwing and without parsing a body", async () => {
      const mockFetch = stubFetch({
        ok: true,
        status: 204,
        json: () => Promise.reject(new Error("should not be called for a 204 response")),
      });

      const result = await httpClient.post("/api/v1/auth/logout", { refresh_token: "r1" });

      expect(result).toBeUndefined();
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe("Authorization header injection", () => {
    it("does not attach an Authorization header when no access token is set", async () => {
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.get("/widgets/1");

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers.Authorization).toBeUndefined();
    });

    it("attaches Authorization: Bearer <token> once an access token is set", async () => {
      setAccessToken("abc123");
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.get("/widgets/1");

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers.Authorization).toBe("Bearer abc123");
    });

    it("merges an auto-attached Authorization header with caller-supplied headers", async () => {
      setAccessToken("abc123");
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.get("/widgets/1", { headers: { "X-Custom": "1" } });

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers.Authorization).toBe("Bearer abc123");
      expect(headers["X-Custom"]).toBe("1");
      expect(headers["Content-Type"]).toBe("application/json");
    });

    it("lets an explicit caller-supplied Authorization header take precedence", async () => {
      setAccessToken("abc123");
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.get("/api/v1/auth/me", { headers: { Authorization: "Bearer explicit" } });

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers.Authorization).toBe("Bearer explicit");
    });

    it("stops attaching the Authorization header once the token is cleared", async () => {
      setAccessToken("abc123");
      setAccessToken(null);
      const mockFetch = stubFetch(OK_RESPONSE);

      await httpClient.get("/widgets/1");

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers.Authorization).toBeUndefined();
    });
  });

  describe("global 401 handling", () => {
    it("does not invoke the unauthorized handler for a 401 on a request with no access token", async () => {
      const handler = vi.fn();
      setUnauthorizedHandler(handler);
      stubFetch(UNAUTHORIZED_RESPONSE);

      await httpClient
        .post("/api/v1/auth/login", { email: "a@b.com", password: "wrong" })
        .catch(() => {});

      expect(handler).not.toHaveBeenCalled();
    });

    it("invokes the unauthorized handler for a 401 on a request that carried an access token", async () => {
      const handler = vi.fn();
      setAccessToken("abc123");
      setUnauthorizedHandler(handler);
      stubFetch(UNAUTHORIZED_RESPONSE);

      await httpClient.get("/api/v1/matters/1").catch(() => {});

      expect(handler).toHaveBeenCalledTimes(1);
    });

    it("clears the access token so subsequent requests are unauthenticated", async () => {
      const handler = vi.fn();
      setAccessToken("abc123");
      setUnauthorizedHandler(handler);
      stubFetch(UNAUTHORIZED_RESPONSE);
      await httpClient.get("/api/v1/matters/1").catch(() => {});

      const mockFetch = stubFetch(OK_RESPONSE);
      await httpClient.get("/widgets/1");

      const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers.Authorization).toBeUndefined();
    });

    it("clears the securely stored refresh token via ipcBridge when available", async () => {
      setAccessToken("abc123");
      mockedIsAvailable.mockReturnValue(true);
      mockedClearRefreshToken.mockResolvedValue(undefined);
      stubFetch(UNAUTHORIZED_RESPONSE);

      await httpClient.get("/api/v1/matters/1").catch(() => {});

      expect(mockedClearRefreshToken).toHaveBeenCalledTimes(1);
    });

    it("skips ipcBridge clearing when the IPC bridge is unavailable (browser context)", async () => {
      setAccessToken("abc123");
      mockedIsAvailable.mockReturnValue(false);
      stubFetch(UNAUTHORIZED_RESPONSE);

      await httpClient.get("/api/v1/matters/1").catch(() => {});

      expect(mockedClearRefreshToken).not.toHaveBeenCalled();
    });

    it("still throws HttpError for the 401 response", async () => {
      setAccessToken("abc123");
      stubFetch(UNAUTHORIZED_RESPONSE);

      const error: unknown = await httpClient.get("/api/v1/matters/1").catch((e: unknown) => e);

      expect(error).toBeInstanceOf(HttpError);
      expect((error as HttpError).status).toBe(401);
    });
  });
});
