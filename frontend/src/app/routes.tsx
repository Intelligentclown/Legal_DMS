import { createBrowserRouter } from "react-router-dom";

import { MainLayout } from "@/presentation/layouts/MainLayout";
import { HealthCheckPage } from "@/presentation/pages/HealthCheckPage";
import { LoginPage } from "@/presentation/pages/LoginPage";

export const router = createBrowserRouter([
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
  {
    path: "/login",
    element: <LoginPage />,
  },
]);
