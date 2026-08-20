import { createBrowserRouter } from "react-router-dom";

import { ProtectedRoute } from "@/app/ProtectedRoute";
import { MainLayout } from "@/presentation/layouts/MainLayout";
import { HealthCheckPage } from "@/presentation/pages/HealthCheckPage";
import { LoginPage } from "@/presentation/pages/LoginPage";

export const router = createBrowserRouter([
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: "/",
        element: <MainLayout />,
        children: [
          {
            index: true,
            element: <HealthCheckPage />,
          },
        ],
      },
    ],
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
]);
