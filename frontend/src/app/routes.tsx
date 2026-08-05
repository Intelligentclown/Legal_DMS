import { createBrowserRouter } from "react-router-dom";

import { MainLayout } from "@/presentation/layouts/MainLayout";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <p className="text-sm text-muted-foreground">Coming soon.</p>,
      },
    ],
  },
]);
