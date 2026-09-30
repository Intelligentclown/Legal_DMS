import { createBrowserRouter } from "react-router-dom";

import { ProtectedRoute } from "@/app/ProtectedRoute";
import { MainLayout } from "@/presentation/layouts/MainLayout";
import { DocumentDetailPage } from "@/presentation/pages/DocumentDetailPage";
import { FileDetailPage } from "@/presentation/pages/FileDetailPage";
import { HealthCheckPage } from "@/presentation/pages/HealthCheckPage";
import { LoginPage } from "@/presentation/pages/LoginPage";
import { MatterCreatePage } from "@/presentation/pages/MatterCreatePage";
import { MatterDetailPage } from "@/presentation/pages/MatterDetailPage";
import { MattersPage } from "@/presentation/pages/MattersPage";
import { PartiesPage } from "@/presentation/pages/PartiesPage";
import { PartyCreatePage } from "@/presentation/pages/PartyCreatePage";

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
          {
            path: "parties",
            element: <PartiesPage />,
          },
          {
            path: "parties/new",
            element: <PartyCreatePage />,
          },
          {
            path: "parties/:partyId/matters/new",
            element: <MatterCreatePage />,
          },
          {
            path: "matters",
            element: <MattersPage />,
          },
          {
            path: "matters/:matterId",
            element: <MatterDetailPage />,
          },
          {
            path: "matters/:matterId/files/:fileId",
            element: <FileDetailPage />,
          },
          {
            path: "matters/:matterId/files/:fileId/documents/:documentId",
            element: <DocumentDetailPage />,
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
