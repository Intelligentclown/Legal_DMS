import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

vi.mock("@/infrastructure/api/httpClient", () => {
  class HttpError extends Error {
    status: number;
    code?: string;
    constructor(status: number, message: string, code?: string) {
      super(message);
      this.name = "HttpError";
      this.status = status;
      this.code = code;
    }
  }
  return {
    httpClient: { get: vi.fn(), postBinary: vi.fn(), getBinary: vi.fn() },
    HttpError,
  };
});

import {
  createDocumentVersion,
  downloadDocumentVersion,
  getLatestDocumentVersion,
  listDocumentVersions,
} from "@/infrastructure/api/documentVersionsApi";
import { httpClient, HttpError } from "@/infrastructure/api/httpClient";

const mockedGet = httpClient.get as unknown as Mock;
const mockedPostBinary = httpClient.postBinary as unknown as Mock;
const mockedGetBinary = httpClient.getBinary as unknown as Mock;

const BASE = "/api/v1/matters/m1/files/f1/documents/d1/versions";
const bytes = new Uint8Array([1, 2, 3]).buffer;

describe("documentVersionsApi", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPostBinary.mockReset();
    mockedGetBinary.mockReset();
  });

  describe("createDocumentVersion", () => {
    it("posts the raw bytes with the filename as the required X-Filename header", async () => {
      mockedPostBinary.mockResolvedValue({ data: { id: "v1", version_number: 1 } });

      const version = await createDocumentVersion("m1", "f1", "d1", {
        content: bytes,
        filename: "deed.pdf",
        mimeType: "application/pdf",
      });

      expect(version).toEqual({ id: "v1", version_number: 1 });
      const [path, body, options] = mockedPostBinary.mock.calls[0] as [
        string,
        ArrayBuffer,
        { contentType: string; headers: Record<string, string> },
      ];
      expect(path).toBe(BASE);
      expect(body).toBe(bytes);
      expect(options.contentType).toBe("application/pdf");
      expect(options.headers["X-Filename"]).toBe("deed.pdf");
    });

    it("passes change_summary as a query parameter, not a header or body field", async () => {
      mockedPostBinary.mockResolvedValue({ data: { id: "v1", version_number: 1 } });

      await createDocumentVersion("m1", "f1", "d1", {
        content: bytes,
        filename: "deed.pdf",
        mimeType: "application/pdf",
        changeSummary: "Signed copy",
      });

      const [path, , options] = mockedPostBinary.mock.calls[0] as [
        string,
        ArrayBuffer,
        { headers: Record<string, string> },
      ];
      expect(path).toBe(`${BASE}?change_summary=Signed+copy`);
      expect(options.headers).not.toHaveProperty("change_summary");
    });

    it("sends an Idempotency-Key when one is supplied", async () => {
      mockedPostBinary.mockResolvedValue({ data: { id: "v1", version_number: 1 } });

      await createDocumentVersion("m1", "f1", "d1", {
        content: bytes,
        filename: "deed.pdf",
        mimeType: "application/pdf",
        idempotencyKey: "key-1",
      });

      const [, , options] = mockedPostBinary.mock.calls[0] as [
        string,
        ArrayBuffer,
        { headers: Record<string, string> },
      ];
      expect(options.headers["Idempotency-Key"]).toBe("key-1");
    });

    it("omits the Idempotency-Key header when none is supplied", async () => {
      mockedPostBinary.mockResolvedValue({ data: { id: "v1", version_number: 1 } });

      await createDocumentVersion("m1", "f1", "d1", {
        content: bytes,
        filename: "deed.pdf",
        mimeType: "application/pdf",
      });

      const [, , options] = mockedPostBinary.mock.calls[0] as [
        string,
        ArrayBuffer,
        { headers: Record<string, string> },
      ];
      expect(options.headers).not.toHaveProperty("Idempotency-Key");
    });
  });

  describe("listDocumentVersions", () => {
    it("unwraps the envelope and returns the versions in backend order", async () => {
      mockedGet.mockResolvedValue({
        data: [
          { id: "v2", version_number: 2, change_summary: null, created_at: "2026-01-02" },
          { id: "v1", version_number: 1, change_summary: "Initial", created_at: "2026-01-01" },
        ],
      });

      const versions = await listDocumentVersions("m1", "f1", "d1");

      expect(mockedGet).toHaveBeenCalledWith(BASE);
      expect(versions.map((version) => version.version_number)).toEqual([2, 1]);
    });
  });

  describe("getLatestDocumentVersion", () => {
    it("returns the latest version", async () => {
      mockedGet.mockResolvedValue({ data: { id: "v2", version_number: 2 } });

      await expect(getLatestDocumentVersion("m1", "f1", "d1")).resolves.toEqual({
        id: "v2",
        version_number: 2,
      });
      expect(mockedGet).toHaveBeenCalledWith(`${BASE}/latest`);
    });

    it("treats a 404 as an empty history rather than a failure", async () => {
      mockedGet.mockRejectedValue(new HttpError(404, "No versions yet", "not_found"));

      await expect(getLatestDocumentVersion("m1", "f1", "d1")).resolves.toBeNull();
    });

    it("propagates any other failure", async () => {
      mockedGet.mockRejectedValue(new HttpError(403, "Forbidden", "forbidden"));

      await expect(getLatestDocumentVersion("m1", "f1", "d1")).rejects.toBeInstanceOf(HttpError);
    });
  });

  describe("downloadDocumentVersion", () => {
    it("reads the binary content route and hands back the response headers", async () => {
      const response = {
        blob: new Blob(["%PDF"]),
        contentType: "application/pdf",
        contentDisposition: 'attachment; filename="deed.pdf"',
      };
      mockedGetBinary.mockResolvedValue(response);

      await expect(downloadDocumentVersion("m1", "f1", "d1", "v1")).resolves.toBe(response);
      expect(mockedGetBinary).toHaveBeenCalledWith(`${BASE}/v1/content`);
    });
  });
});
