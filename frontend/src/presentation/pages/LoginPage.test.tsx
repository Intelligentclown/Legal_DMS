import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { AuthProvider } from "@/app/providers/AuthProvider";
import { LoginPage } from "@/presentation/pages/LoginPage";

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
    httpClient: { post: vi.fn(), get: vi.fn() },
    HttpError,
  };
});

import { httpClient, HttpError } from "@/infrastructure/api/httpClient";

const mockedPost = httpClient.post as unknown as Mock;
const mockedGet = httpClient.get as unknown as Mock;

const TOKENS = { access_token: "access-123", refresh_token: "refresh-456" };
const ME_RESPONSE = { data: { id: "u1", display_name: "Jane Doe", roles: ["Administrator"] } };

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Home page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

async function fillAndSubmit(email: string, password: string) {
  await userEvent.type(screen.getByLabelText(/email/i), email);
  await userEvent.type(screen.getByLabelText(/password/i), password);
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
}

describe("LoginPage", () => {
  beforeEach(() => {
    mockedPost.mockReset();
    mockedGet.mockReset();
  });

  it("renders email and password fields and a submit button", () => {
    renderPage();

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("logs in and navigates to / on successful submit", async () => {
    mockedPost.mockResolvedValue(TOKENS);
    mockedGet.mockResolvedValue(ME_RESPONSE);

    renderPage();
    await fillAndSubmit("jane@example.com", "correct-password");

    expect(await screen.findByText("Home page")).toBeInTheDocument();
    expect(mockedPost).toHaveBeenCalledWith("/api/v1/auth/login", {
      email: "jane@example.com",
      password: "correct-password",
    });
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/v1/auth/me",
      expect.objectContaining({ headers: { Authorization: "Bearer access-123" } }),
    );
  });

  it("shows an inline error and stays on the page when credentials are invalid", async () => {
    mockedPost.mockRejectedValue(new HttpError(401, "Invalid email or password", "unauthorized"));

    renderPage();
    await fillAndSubmit("jane@example.com", "wrong-password");

    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid email or password/i);
    expect(screen.queryByText("Home page")).not.toBeInTheDocument();
  });

  it("disables the submit button while the request is pending", async () => {
    mockedPost.mockReturnValue(new Promise(() => {}));

    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), "jane@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "correct-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
  });
});
