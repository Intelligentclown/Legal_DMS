import type { ReactNode } from "react";

import { ErrorBoundary } from "@/presentation/components/ErrorBoundary";

import { AuthProvider } from "./AuthProvider";
import { NotificationProvider } from "./NotificationProvider";
import { ThemeProvider } from "./ThemeProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <NotificationProvider>
          <AuthProvider>{children}</AuthProvider>
        </NotificationProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
