import { Outlet } from "react-router-dom";

export function MainLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-base font-semibold">Legal Document &amp; Matter Management System</h1>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
