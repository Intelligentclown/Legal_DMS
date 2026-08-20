import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { CurrentUser, AuthTokens, LoginCredentials } from "@/domain/types/auth";
import {
  httpClient,
  setAccessToken,
  setUnauthorizedHandler,
} from "@/infrastructure/api/httpClient";
import { ipcBridge } from "@/infrastructure/ipc/ipcBridge";

interface AuthState {
  currentUser: CurrentUser | null;
  tokens: AuthTokens | null;
}

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    currentUser: null,
    tokens: null,
  });

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setState({ currentUser: null, tokens: null });
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const tokens = await httpClient.post<AuthTokens>("/api/v1/auth/login", credentials);
    setAccessToken(tokens.access_token);
    try {
      const response = await httpClient.get<{ data: CurrentUser }>("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });
      setState({ tokens, currentUser: response.data });
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
    setState({ currentUser: null, tokens: null });
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
