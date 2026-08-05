import { env } from "@/shared/config/env";

export class HttpError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (!response.ok) {
    throw new HttpError(
      response.status,
      `Request to ${path} failed with status ${response.status}`,
    );
  }

  return (await response.json()) as T;
}

export const httpClient = {
  get: <T>(path: string): Promise<T> => request<T>(path),
};
