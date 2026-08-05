import { createBrowserRouter } from "react-router-dom";

import { MainLayout } from "@/presentation/layouts/MainLayout";
import { HealthCheckPage } from "@/presentation/pages/HealthCheckPage";

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
]);
