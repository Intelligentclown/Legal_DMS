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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const hadAccessToken = accessToken !== null;

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
  });

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

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function requestWithBody<T>(method: string, path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export const httpClient = {
  get: <T>(path: string, options?: { headers?: Record<string, string> }): Promise<T> =>
    request<T>(path, { headers: options?.headers }),
  post: <T>(path: string, body?: unknown): Promise<T> => requestWithBody<T>("POST", path, body),
  put: <T>(path: string, body?: unknown): Promise<T> => requestWithBody<T>("PUT", path, body),
  delete: <T>(path: string): Promise<T> => requestWithBody<T>("DELETE", path),
};
