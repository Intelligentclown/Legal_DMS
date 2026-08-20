import { useState } from "react";
import { Outlet } from "react-router-dom";

import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/presentation/components/ui/button";

export function MainLayout() {
  const { currentUser, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <h1 className="text-base font-semibold">Legal Document &amp; Matter Management System</h1>
        {currentUser ? (
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">{currentUser.display_name}</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isLoggingOut}
              onClick={() => void handleLogout()}
            >
              {isLoggingOut ? "Logging out…" : "Log out"}
            </Button>
          </div>
        ) : null}
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
