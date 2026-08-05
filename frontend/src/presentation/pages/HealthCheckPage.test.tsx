import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { NotificationProvider } from "@/app/providers/NotificationProvider";
import { HealthCheckPage } from "@/presentation/pages/HealthCheckPage";

vi.mock("@/infrastructure/api/httpClient", () => {
  class HttpError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = "HttpError";
      this.status = status;
    }
  }
  return {
    httpClient: { get: vi.fn() },
    HttpError,
  };
});

import { httpClient } from "@/infrastructure/api/httpClient";

const mockedGet = httpClient.get as unknown as Mock;

const HEALTH_RESPONSE = {
  status: "ok",
  service: "Legal Document & Matter Management System",
  environment: "development",
  timestamp: "2026-01-01T00:00:00Z",
};
const VERSION_RESPONSE = { app_name: "Legal DMS", version: "0.1.0", api_prefix: "/api/v1" };

function mockSuccessfulBackend(): void {
  mockedGet.mockImplementation((path: string) =>
    path === "/api/v1/health"
      ? Promise.resolve(HEALTH_RESPONSE)
      : Promise.resolve(VERSION_RESPONSE),
  );
}

function renderPage() {
  return render(
    <NotificationProvider>
      <HealthCheckPage />
    </NotificationProvider>,
  );
}

describe("HealthCheckPage", () => {
  beforeEach(() => {
    mockedGet.mockReset();
  });

  it("shows a loading state before the backend responds", () => {
    mockedGet.mockReturnValue(new Promise(() => {}));

    renderPage();

    expect(screen.getByRole("status")).toHaveTextContent(/checking backend/i);
  });

  it("renders health and version data once the backend responds", async () => {
    mockSuccessfulBackend();

    renderPage();

    expect(await screen.findByText("ok")).toBeInTheDocument();
    expect(screen.getByText("development")).toBeInTheDocument();
    expect(screen.getByText("0.1.0")).toBeInTheDocument();
  });

  it("shows an error state with a retry action, and recovers on retry", async () => {
    mockedGet.mockRejectedValue(new Error("network error"));

    renderPage();

    // Appears twice by design: once in the inline error card, once in the toast.
    expect(await screen.findAllByText(/backend unreachable/i)).not.toHaveLength(0);

    mockSuccessfulBackend();
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));

    expect(await screen.findByText("ok")).toBeInTheDocument();
  });
});
