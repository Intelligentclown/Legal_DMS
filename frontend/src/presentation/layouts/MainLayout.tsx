import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/presentation/components/ui/button";

const NAV_ITEMS = [
  { to: "/", label: "Status", end: true },
  { to: "/parties", label: "Parties", end: false },
  { to: "/matters", label: "Matters", end: false },
];

function navItemClassName(isActive: boolean): string {
  return isActive
    ? "rounded-md bg-muted px-2.5 py-1.5 text-sm font-medium text-foreground"
    : "rounded-md px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground";
}

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
      <nav aria-label="Main" className="flex items-center gap-1 border-b border-border px-6 py-2">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => navItemClassName(isActive)}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
