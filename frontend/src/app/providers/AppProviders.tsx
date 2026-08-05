import type { ReactNode } from "react";

import { ErrorBoundary } from "@/presentation/components/ErrorBoundary";

import { NotificationProvider } from "./NotificationProvider";
import { ThemeProvider } from "./ThemeProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <NotificationProvider>{children}</NotificationProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
