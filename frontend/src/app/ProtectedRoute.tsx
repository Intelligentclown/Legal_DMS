import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/app/providers/AuthProvider";
import { LoadingSpinner } from "@/presentation/components/LoadingSpinner";

export function ProtectedRoute() {
  const { currentUser, isInitializing } = useAuth();

  if (isInitializing) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner label="Restoring session…" />
      </div>
    );
  }

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
