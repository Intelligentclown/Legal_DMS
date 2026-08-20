import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/app/providers/AuthProvider";

export function ProtectedRoute() {
  const { currentUser } = useAuth();

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
