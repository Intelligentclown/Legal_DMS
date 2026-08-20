import { useEffect } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "@/app/providers/AuthProvider";
import { ProtectedRoute } from "@/app/ProtectedRoute";
import {
  httpClient,
  setAccessToken,
  setUnauthorizedHandler,
} from "@/infrastructure/api/httpClient";

const TOKENS = { access_token: "access-123", refresh_token: "refresh-456" };
const ME_RESPONSE = { data: { id: "u1", display_name: "Jane Doe", roles: ["Administrator"] } };

function stubFetch(): void {
  const mockFetch = vi.fn(async (url: unknown) => {
    const path = String(url);
    if (path.includes("/auth/login")) {
      return { ok: true, status: 200, json: () => Promise.resolve(TOKENS) } as Response;
    }
    if (path.includes("/auth/me")) {
      return { ok: true, status: 200, json: () => Promise.resolve(ME_RESPONSE) } as Response;
    }
    return {
      ok: false,
      status: 401,
      json: () =>
        Promise.resolve({ error: { code: "UNAUTHORIZED", message: "Invalid or expired token" } }),
    } as Response;
  });
  vi.stubGlobal("fetch", mockFetch);
}

/** Mirrors LoginPage.tsx's real login-then-navigate flow, without coupling this test to its UI. */
function AutoLogin() {
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    void login({ email: "jane@example.com", password: "correct-password" }).then(() =>
      navigate("/", { replace: true }),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

function ProtectedHarness() {
  const { currentUser } = useAuth();

  return (
    <div>
      <p>Protected content for {currentUser?.display_name}</p>
      <button onClick={() => void httpClient.get("/api/v1/matters/1").catch(() => {})}>
        Trigger 401
      </button>
    </div>
  );
}

function renderApp() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <AuthProvider>
        <AutoLogin />
        <Routes>
          <Route path="/login" element={<div>Login page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<ProtectedHarness />} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("AuthProvider — global 401 handling", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setAccessToken(null);
    setUnauthorizedHandler(null);
  });

  it("clears the session and redirects to /login when an authenticated request comes back 401", async () => {
    stubFetch();
    const user = userEvent.setup();

    renderApp();

    const trigger = await screen.findByRole("button", { name: "Trigger 401" });
    expect(screen.getByText("Protected content for Jane Doe")).toBeInTheDocument();

    await user.click(trigger);

    expect(await screen.findByText("Login page")).toBeInTheDocument();
    expect(screen.queryByText(/Protected content/)).not.toBeInTheDocument();
  });
});
