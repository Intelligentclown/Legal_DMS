import { createBrowserRouter, createHashRouter } from "react-router-dom";

import { ProtectedRoute } from "@/app/ProtectedRoute";
import { MainLayout } from "@/presentation/layouts/MainLayout";
import { DocumentDetailPage } from "@/presentation/pages/DocumentDetailPage";
import { EnquiriesPage } from "@/presentation/pages/EnquiriesPage";
import { EnquiryCreatePage } from "@/presentation/pages/EnquiryCreatePage";
import { EnquiryDetailPage } from "@/presentation/pages/EnquiryDetailPage";
import { FileDetailPage } from "@/presentation/pages/FileDetailPage";
import { HealthCheckPage } from "@/presentation/pages/HealthCheckPage";
import { LoginPage } from "@/presentation/pages/LoginPage";
import { MatterCreatePage } from "@/presentation/pages/MatterCreatePage";
import { MatterDetailPage } from "@/presentation/pages/MatterDetailPage";
import { MattersPage } from "@/presentation/pages/MattersPage";
import { PartiesPage } from "@/presentation/pages/PartiesPage";
import { PartyCreatePage } from "@/presentation/pages/PartyCreatePage";
import { QuotationDetailPage } from "@/presentation/pages/QuotationDetailPage";

const routes = [
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
          { path: "enquiries", element: <EnquiriesPage /> },
          { path: "enquiries/new", element: <EnquiryCreatePage /> },
          { path: "enquiries/:enquiryId", element: <EnquiryDetailPage /> },
          {
            path: "enquiries/:enquiryId/quotations/:quotationId",
            element: <QuotationDetailPage />,
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
];

export function createAppRouter(protocol = window.location.protocol) {
  const createRouter = protocol === "file:" ? createHashRouter : createBrowserRouter;
  return createRouter(routes);
}

export const router = createAppRouter();
