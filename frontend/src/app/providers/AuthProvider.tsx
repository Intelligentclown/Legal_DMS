import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { CurrentUser, AuthTokens, LoginCredentials } from "@/domain/types/auth";
import {
  httpClient,
  HttpError,
  setAccessToken,
  setUnauthorizedHandler,
} from "@/infrastructure/api/httpClient";
import { ipcBridge } from "@/infrastructure/ipc/ipcBridge";

interface AuthState {
  currentUser: CurrentUser | null;
  tokens: AuthTokens | null;
  /** True only while startup session restoration is still in flight. */
  isInitializing: boolean;
}

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

async function fetchCurrentUser(accessToken: string): Promise<CurrentUser> {
  const response = await httpClient.get<{ data: CurrentUser }>("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    currentUser: null,
    tokens: null,
    isInitializing: true,
  });

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setState((prev) => ({ ...prev, currentUser: null, tokens: null }));
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  // Guards session restoration so it runs at most once per app startup. React 18
  // StrictMode (development only) intentionally double-invokes every effect
  // (mount -> cleanup -> mount) to surface effects that aren't safe to run twice --
  // and this one makes a real, side-effecting network call (/auth/refresh), so a
  // second, concurrent invocation is exactly the kind of thing StrictMode exists to
  // catch. `restorationStartedRef` ensures only the first invocation ever starts the
  // actual work; `isMountedRef` (reset to `true` on every invocation's synchronous
  // body, set `false` only by cleanup) tracks whether the component is *currently*
  // mounted in a way that's immune to StrictMode's synchronous probe-cleanup, so the
  // one real restoreSession() call can still safely update state once it resolves.
  // Together these remove the possibility of a second, competing restoration attempt
  // entirely, rather than only gating its result after the fact.
  const restorationStartedRef = useRef(false);
  const isMountedRef = useRef(false);

  useEffect(() => {
    isMountedRef.current = true;

    async function restoreSession(): Promise<void> {
      if (!ipcBridge.isAvailable()) {
        return;
      }

      let persistedToken: string | null;
      try {
        persistedToken = await ipcBridge.getRefreshToken();
      } catch {
        return;
      }
      if (!persistedToken) {
        return;
      }

      let tokens: AuthTokens;
      try {
        tokens = await httpClient.post<AuthTokens>("/api/v1/auth/refresh", {
          refresh_token: persistedToken,
        });
      } catch (error) {
        // A structured HTTP failure (401 etc.) means the persisted token is genuinely
        // invalid/expired/revoked -- clear it so the app doesn't keep retrying it on
        // every future launch. A non-HttpError (network failure, backend unreachable)
        // says nothing about the token's validity, so it's deliberately left in place
        // for the next attempt.
        if (error instanceof HttpError) {
          await ipcBridge.clearRefreshToken().catch(() => {});
        }
        return;
      }

      setAccessToken(tokens.access_token);
      try {
        const currentUser = await fetchCurrentUser(tokens.access_token);
        // /auth/refresh rotates the refresh token -- the one just presented is now
        // revoked, so the newly-issued one must replace it in persisted storage or
        // the *next* restoration attempt would fail.
        await ipcBridge.setRefreshToken(tokens.refresh_token).catch(() => {});
        if (isMountedRef.current) {
          setState({ currentUser, tokens, isInitializing: false });
        }
      } catch {
        setAccessToken(null);
      }
    }

    if (!restorationStartedRef.current) {
      restorationStartedRef.current = true;
      void restoreSession().finally(() => {
        if (isMountedRef.current) {
          setState((prev) => (prev.isInitializing ? { ...prev, isInitializing: false } : prev));
        }
      });
    }

    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const tokens = await httpClient.post<AuthTokens>("/api/v1/auth/login", credentials);
    setAccessToken(tokens.access_token);
    try {
      const currentUser = await fetchCurrentUser(tokens.access_token);
      setState({ tokens, currentUser, isInitializing: false });
    } catch (error) {
      setAccessToken(null);
      throw error;
    }
  };

  const logout = async () => {
    if (state.tokens?.refresh_token) {
      try {
        await httpClient.post("/api/v1/auth/logout", { refresh_token: state.tokens.refresh_token });
      } catch (error) {
        console.error("Logout request failed:", error);
      }
    }
    if (ipcBridge.isAvailable()) {
      try {
        await ipcBridge.clearRefreshToken();
      } catch (error) {
        console.error("Failed to clear persisted refresh token:", error);
      }
    }
    setAccessToken(null);
    setState({ currentUser: null, tokens: null, isInitializing: false });
  };

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
