import { useEffect } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi, type Mock } from "vitest";

vi.mock("@/infrastructure/ipc/ipcBridge", () => ({
  ipcBridge: {
    isAvailable: vi.fn(),
    getRefreshToken: vi.fn(),
    setRefreshToken: vi.fn(),
    clearRefreshToken: vi.fn(),
  },
}));

import { AuthProvider, useAuth } from "@/app/providers/AuthProvider";
import { ProtectedRoute } from "@/app/ProtectedRoute";
import {
  httpClient,
  setAccessToken,
  setUnauthorizedHandler,
} from "@/infrastructure/api/httpClient";
import { ipcBridge } from "@/infrastructure/ipc/ipcBridge";

const mockedIsAvailable = ipcBridge.isAvailable as unknown as Mock;
const mockedGetRefreshToken = ipcBridge.getRefreshToken as unknown as Mock;
const mockedSetRefreshToken = ipcBridge.setRefreshToken as unknown as Mock;
const mockedClearRefreshToken = ipcBridge.clearRefreshToken as unknown as Mock;

const TOKENS = { access_token: "access-123", refresh_token: "refresh-456" };
const ME_RESPONSE = { data: { id: "u1", display_name: "Jane Doe", roles: ["Administrator"] } };
const RESTORED_TOKENS = {
  access_token: "restored-access-789",
  refresh_token: "restored-refresh-101",
};

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
    mockedIsAvailable.mockReset();
    mockedGetRefreshToken.mockReset();
    mockedSetRefreshToken.mockReset();
    mockedClearRefreshToken.mockReset();
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

function LogoutHarness() {
  const { login, logout, currentUser } = useAuth();

  return (
    <div>
      <button
        onClick={() => void login({ email: "jane@example.com", password: "correct-password" })}
      >
        Login
      </button>
      <button onClick={() => void logout()}>Logout</button>
      <p>{currentUser ? `Logged in as ${currentUser.display_name}` : "Logged out"}</p>
    </div>
  );
}

describe("AuthProvider — logout() IPC refresh-token clearing", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setAccessToken(null);
    setUnauthorizedHandler(null);
    mockedIsAvailable.mockReset();
    mockedGetRefreshToken.mockReset();
    mockedSetRefreshToken.mockReset();
    mockedClearRefreshToken.mockReset();
  });

  /**
   * Also handles /auth/logout with a real 204, unlike the shared stubFetch() above (whose
   * catch-all 401 is deliberate for the global-401 tests). Without this, the logout POST
   * itself would come back 401 and trip httpClient's own global-401 ipcBridge.clearRefreshToken()
   * call, double-counting alongside AuthProvider.logout()'s own explicit call below.
   */
  function stubFetchWithLogout(): void {
    const mockFetch = vi.fn(async (url: unknown) => {
      const path = String(url);
      if (path.includes("/auth/login")) {
        return { ok: true, status: 200, json: () => Promise.resolve(TOKENS) } as Response;
      }
      if (path.includes("/auth/me")) {
        return { ok: true, status: 200, json: () => Promise.resolve(ME_RESPONSE) } as Response;
      }
      if (path.includes("/auth/logout")) {
        return {
          ok: true,
          status: 204,
          json: () => Promise.reject(new Error("no body")),
        } as Response;
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

  async function loginThenLogout() {
    stubFetchWithLogout();
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <LogoutHarness />
      </AuthProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Login" }));
    await screen.findByText("Logged in as Jane Doe");

    await user.click(screen.getByRole("button", { name: "Logout" }));
    await screen.findByText("Logged out");
  }

  it("calls ipcBridge.clearRefreshToken() when the IPC bridge is available", async () => {
    mockedIsAvailable.mockReturnValue(true);
    mockedClearRefreshToken.mockResolvedValue(undefined);

    await loginThenLogout();

    expect(mockedClearRefreshToken).toHaveBeenCalledTimes(1);
  });

  it("skips ipcBridge.clearRefreshToken() when the IPC bridge is unavailable", async () => {
    mockedIsAvailable.mockReturnValue(false);

    await loginThenLogout();

    expect(mockedClearRefreshToken).not.toHaveBeenCalled();
  });

  it("still clears currentUser/tokens when ipcBridge.clearRefreshToken() rejects", async () => {
    mockedIsAvailable.mockReturnValue(true);
    mockedClearRefreshToken.mockRejectedValue(new Error("secure storage unavailable"));

    // loginThenLogout()'s own findByText("Logged out") assertion is the proof: if the
    // try/catch around the awaited IPC call didn't shield logout()'s state-clearing tail
    // (setAccessToken(null) + setState(...)), that text would never appear and this would
    // time out instead of passing.
    await loginThenLogout();

    expect(mockedClearRefreshToken).toHaveBeenCalledTimes(1);
  });
});

function RestorationHarness() {
  const { currentUser, isInitializing } = useAuth();

  if (isInitializing) {
    return <p>Initializing…</p>;
  }
  return <p>{currentUser ? `Restored: ${currentUser.display_name}` : "Not authenticated"}</p>;
}

describe("AuthProvider — session restoration on mount", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setAccessToken(null);
    setUnauthorizedHandler(null);
    mockedIsAvailable.mockReset();
    mockedGetRefreshToken.mockReset();
    mockedSetRefreshToken.mockReset();
    mockedClearRefreshToken.mockReset();
  });

  function stubFetchForRestoration(options: { refreshFails?: boolean } = {}): void {
    const mockFetch = vi.fn(async (url: unknown) => {
      const path = String(url);
      if (path.includes("/auth/refresh")) {
        if (options.refreshFails) {
          return {
            ok: false,
            status: 401,
            json: () =>
              Promise.resolve({
                error: { code: "UNAUTHORIZED", message: "Invalid or expired token" },
              }),
          } as Response;
        }
        return { ok: true, status: 200, json: () => Promise.resolve(RESTORED_TOKENS) } as Response;
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

  it("restores currentUser from a persisted refresh token and persists the rotated token", async () => {
    mockedIsAvailable.mockReturnValue(true);
    mockedGetRefreshToken.mockResolvedValue("persisted-refresh-token");
    mockedSetRefreshToken.mockResolvedValue(undefined);
    stubFetchForRestoration();

    render(
      <AuthProvider>
        <RestorationHarness />
      </AuthProvider>,
    );

    expect(screen.getByText("Initializing…")).toBeInTheDocument();
    expect(await screen.findByText("Restored: Jane Doe")).toBeInTheDocument();
    expect(mockedSetRefreshToken).toHaveBeenCalledWith(RESTORED_TOKENS.refresh_token);
  });

  it("remains unauthenticated, with no network call, when no refresh token is persisted", async () => {
    mockedIsAvailable.mockReturnValue(true);
    mockedGetRefreshToken.mockResolvedValue(null);
    const mockFetch = vi.fn();
    vi.stubGlobal("fetch", mockFetch);

    render(
      <AuthProvider>
        <RestorationHarness />
      </AuthProvider>,
    );

    expect(await screen.findByText("Not authenticated")).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("clears the persisted token and remains unauthenticated when it is invalid, expired, or revoked", async () => {
    mockedIsAvailable.mockReturnValue(true);
    mockedGetRefreshToken.mockResolvedValue("stale-refresh-token");
    mockedClearRefreshToken.mockResolvedValue(undefined);
    stubFetchForRestoration({ refreshFails: true });

    render(
      <AuthProvider>
        <RestorationHarness />
      </AuthProvider>,
    );

    expect(await screen.findByText("Not authenticated")).toBeInTheDocument();
    expect(mockedClearRefreshToken).toHaveBeenCalledTimes(1);
  });

  it("leaves the persisted token untouched and remains unauthenticated on a network failure", async () => {
    mockedIsAvailable.mockReturnValue(true);
    mockedGetRefreshToken.mockResolvedValue("some-refresh-token");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );

    render(
      <AuthProvider>
        <RestorationHarness />
      </AuthProvider>,
    );

    expect(await screen.findByText("Not authenticated")).toBeInTheDocument();
    expect(mockedClearRefreshToken).not.toHaveBeenCalled();
  });

  it("skips restoration entirely outside Electron (ipcBridge.isAvailable() === false)", async () => {
    mockedIsAvailable.mockReturnValue(false);

    render(
      <AuthProvider>
        <RestorationHarness />
      </AuthProvider>,
    );

    expect(await screen.findByText("Not authenticated")).toBeInTheDocument();
    expect(mockedGetRefreshToken).not.toHaveBeenCalled();
  });

  it("does not redirect ProtectedRoute to /login while restoration is still in progress", async () => {
    mockedIsAvailable.mockReturnValue(true);
    let resolveGetRefreshToken: (value: string | null) => void = () => {};
    mockedGetRefreshToken.mockReturnValue(
      new Promise<string | null>((resolve) => {
        resolveGetRefreshToken = resolve;
      }),
    );

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<div>Protected content</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.queryByText("Login page")).not.toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();

    resolveGetRefreshToken(null);

    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });
});
