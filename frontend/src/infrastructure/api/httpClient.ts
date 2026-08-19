import { env } from "@/shared/config/env";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (!response.ok) {
    throw await buildHttpError(path, response);
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
