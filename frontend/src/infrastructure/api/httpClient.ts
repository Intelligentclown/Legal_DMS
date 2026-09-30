import { env } from "@/shared/config/env";
import { ipcBridge } from "@/infrastructure/ipc/ipcBridge";

interface StructuredErrorBody {
  error: {
    code: string;
    message: string;
  };
}

function isStructuredErrorBody(value: unknown): value is StructuredErrorBody {
  if (typeof value !== "object" || value === null) return false;
  const error = (value as Record<string, unknown>).error;
  if (typeof error !== "object" || error === null) return false;
  const { code, message } = error as Record<string, unknown>;
  return typeof code === "string" && typeof message === "string";
}

export class HttpError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.code = code;
  }
}

async function buildHttpError(path: string, response: Response): Promise<HttpError> {
  const genericMessage = `Request to ${path} failed with status ${response.status}`;

  try {
    const body: unknown = await response.json();
    if (isStructuredErrorBody(body)) {
      return new HttpError(response.status, body.error.message, body.error.code);
    }
  } catch {
    // Response body isn't valid JSON — fall back to the generic message below.
  }

  return new HttpError(response.status, genericMessage);
}

let accessToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

/** Sets the token attached as `Authorization: Bearer <token>` to future requests. */
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/**
 * Registers the callback invoked when a request that carried an access token comes back
 * `401` — i.e. a session that was authenticated has stopped being accepted. Never invoked for
 * a `401` on a request that had no token attached (e.g. a login attempt with bad credentials),
 * since there's no session to expire in that case.
 */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...extra,
  };
}

/**
 * Single funnel for every request: resolves the URL, injects the bearer token,
 * runs the global 401 handling, and converts a non-OK response into a
 * structured `HttpError`. Returns the raw `Response` so callers that need a
 * non-JSON body (binary download) can read it themselves.
 */
async function send(path: string, init: RequestInit): Promise<Response> {
  const hadAccessToken = accessToken !== null;

  const response = await fetch(`${env.apiBaseUrl}${path}`, init);

  if (response.status === 401) {
    accessToken = null;
    if (hadAccessToken) {
      if (ipcBridge.isAvailable()) {
        void ipcBridge.clearRefreshToken().catch(() => {});
      }
      unauthorizedHandler?.();
    }
  }

  if (!response.ok) {
    throw await buildHttpError(path, response);
  }

  return response;
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await send(path, init);

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function requestWithBody<T>(method: string, path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: authHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

const DEFAULT_BINARY_CONTENT_TYPE = "application/octet-stream";

export interface BinaryResponse {
  blob: Blob;
  /** The backend replays the MIME type recorded at upload; null if none was sent. */
  contentType: string | null;
  /** `attachment; filename="…"` as returned by the download route. */
  contentDisposition: string | null;
}

export const httpClient = {
  get: <T>(path: string, options?: { headers?: Record<string, string> }): Promise<T> =>
    request<T>(path, { method: "GET", headers: authHeaders(options?.headers) }),
  post: <T>(path: string, body?: unknown): Promise<T> => requestWithBody<T>("POST", path, body),
  put: <T>(path: string, body?: unknown): Promise<T> => requestWithBody<T>("PUT", path, body),
  delete: <T>(path: string): Promise<T> => requestWithBody<T>("DELETE", path),

  /**
   * Sends raw bytes as the request body instead of a JSON payload, for the
   * existing DocumentVersion upload contract, which takes the file bytes
   * directly (not multipart/form-data) alongside the required `X-Filename`
   * header and the optional `Idempotency-Key` header.
   *
   * `contentType` is applied over the JSON default because the backend reads
   * `Content-Type` as the stored MIME type and FastAPI would try to JSON-parse
   * a body declared as `application/json`.
   */
  postBinary: <T>(
    path: string,
    content: Blob | ArrayBuffer,
    options?: { contentType?: string; headers?: Record<string, string> },
  ): Promise<T> =>
    request<T>(path, {
      method: "POST",
      headers: authHeaders({
        "Content-Type": options?.contentType ?? DEFAULT_BINARY_CONTENT_TYPE,
        ...options?.headers,
      }),
      body: content,
    }),

  /** Reads a binary response plus the headers the download route relies on. */
  getBinary: async (path: string): Promise<BinaryResponse> => {
    const response = await send(path, { method: "GET", headers: authHeaders() });

    return {
      blob: await response.blob(),
      contentType: response.headers.get("Content-Type"),
      contentDisposition: response.headers.get("Content-Disposition"),
    };
  },
};
