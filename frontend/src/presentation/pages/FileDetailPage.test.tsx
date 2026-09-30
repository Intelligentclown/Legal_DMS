import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { FileDetailPage } from "@/presentation/pages/FileDetailPage";
import { renderRoute } from "@/test/renderRoute";

vi.mock("@/infrastructure/api/documentsApi", () => ({
  listLegalDocuments: vi.fn(),
  getLegalDocument: vi.fn(),
  createLegalDocument: vi.fn(),
}));
vi.mock("@/infrastructure/api/filesApi", () => ({
  listMatterFiles: vi.fn(),
  getMatterFile: vi.fn(),
  createMatterFile: vi.fn(),
}));
vi.mock("@/infrastructure/api/mattersApi", () => ({
  getMatter: vi.fn(),
  listMatters: vi.fn(),
  createMatter: vi.fn(),
}));
vi.mock("@/infrastructure/api/lookupsApi", () => ({
  listMatterTypes: vi.fn(),
  listMatterStatuses: vi.fn(),
  listDocumentTypes: vi.fn(),
}));
vi.mock("@/infrastructure/api/httpClient", () => {
  class HttpError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = "HttpError";
      this.status = status;
    }
  }
  return { httpClient: { get: vi.fn(), post: vi.fn() }, HttpError };
});

import { createLegalDocument, listLegalDocuments } from "@/infrastructure/api/documentsApi";
import { getMatterFile } from "@/infrastructure/api/filesApi";
import { getMatter } from "@/infrastructure/api/mattersApi";
import { listDocumentTypes } from "@/infrastructure/api/lookupsApi";
import { HttpError } from "@/infrastructure/api/httpClient";

const mockedCreateDocument = createLegalDocument as unknown as Mock;
const mockedListDocuments = listLegalDocuments as unknown as Mock;
const mockedGetFile = getMatterFile as unknown as Mock;
const mockedGetMatter = getMatter as unknown as Mock;
const mockedDocumentTypes = listDocumentTypes as unknown as Mock;

const FILE = { id: "f1", matter_id: "m1", file_number: 1, title: "Pleadings", version: 1 };
const MATTER = { id: "m1", matter_number: "MAT-2026-ABC123", title: "Northwind v. Contoso" };

const DOCUMENT_TYPES = [
  { id: "dt-plaint", code: "PL", name: "Plaint", is_active: true },
  { id: "dt-old", code: "OLD", name: "Retired", is_active: false },
];

const DOCUMENTS = [
  {
    id: "d1",
    document_type_id: "dt-plaint",
    title: "Written Complaint",
    status: "draft",
    version: 1,
  },
];

function documentsPage(items: unknown[]) {
  return { items, pagination: { page: 1, page_size: 20, total: items.length, total_pages: 1 } };
}

function renderPage() {
  return renderRoute({
    element: <FileDetailPage />,
    path: "/matters/:matterId/files/:fileId",
    initialEntry: "/matters/m1/files/f1",
    routes: [
      {
        path: "/matters/m1/files/f1/documents/d1",
        element: <div>Document detail page</div>,
      },
    ],
  });
}

describe("FileDetailPage", () => {
  beforeEach(() => {
    mockedGetFile.mockReset().mockResolvedValue(FILE);
    mockedGetMatter.mockReset().mockResolvedValue(MATTER);
    mockedDocumentTypes.mockReset().mockResolvedValue(DOCUMENT_TYPES);
    mockedListDocuments.mockReset().mockResolvedValue(documentsPage(DOCUMENTS));
    mockedCreateDocument.mockReset();
  });

  it("shows the file number the backend assigned and its matter", async () => {
    renderPage();

    expect((await screen.findAllByText("Pleadings")).length).toBeGreaterThan(0);
    expect(mockedGetFile).toHaveBeenCalledWith("m1", "f1");
    expect(screen.getAllByText("MAT-2026-ABC123").length).toBeGreaterThan(0);
  });

  it("lists only the documents reachable through this file", async () => {
    renderPage();

    expect(await screen.findByText("Written Complaint")).toBeInTheDocument();
    expect(mockedListDocuments).toHaveBeenCalledWith("m1", "f1", { page: 1 });
  });

  it("shows an empty state for a file with no documents", async () => {
    mockedListDocuments.mockResolvedValue(documentsPage([]));

    renderPage();

    expect(await screen.findByText(/no documents in this file yet/i)).toBeInTheDocument();
  });

  it("offers the active document types discovered from the T146 route", async () => {
    renderPage();

    await screen.findByLabelText(/document type/i);
    expect(mockedDocumentTypes).toHaveBeenCalled();
    expect(screen.getByRole("option", { name: "Plaint (PL)" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Retired/ })).not.toBeInTheDocument();
  });

  it("requires a title and a type before creating a document", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Written Complaint");

    await user.click(screen.getByRole("button", { name: /create document/i }));

    expect(await screen.findByText(/document title is required/i)).toBeInTheDocument();
    expect(screen.getByText(/choose a document type/i)).toBeInTheDocument();
    expect(mockedCreateDocument).not.toHaveBeenCalled();
  });

  it("creates a document scoped to the matter, file and selected type", async () => {
    mockedCreateDocument.mockResolvedValue({
      id: "d2",
      document_type_id: "dt-plaint",
      title: "Amended Complaint",
      status: "draft",
      version: 1,
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Written Complaint");

    await user.type(screen.getByLabelText(/new document title/i), "Amended Complaint");
    await user.selectOptions(await screen.findByLabelText(/document type/i), "dt-plaint");
    await user.click(screen.getByRole("button", { name: /create document/i }));

    await waitFor(() =>
      expect(mockedCreateDocument).toHaveBeenCalledWith("m1", "f1", {
        title: "Amended Complaint",
        document_type_id: "dt-plaint",
      }),
    );
  });

  it("leaves the document status to the backend default rather than sending one", async () => {
    mockedCreateDocument.mockResolvedValue({
      id: "d2",
      document_type_id: "dt-plaint",
      title: "Amended Complaint",
      status: "draft",
      version: 1,
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Written Complaint");

    await user.type(screen.getByLabelText(/new document title/i), "Amended Complaint");
    await user.selectOptions(await screen.findByLabelText(/document type/i), "dt-plaint");
    await user.click(screen.getByRole("button", { name: /create document/i }));

    await waitFor(() => expect(mockedCreateDocument).toHaveBeenCalled());
    expect(mockedCreateDocument.mock.calls[0][2]).not.toHaveProperty("status");
  });

  it("surfaces a conflict raised while creating a document", async () => {
    mockedCreateDocument.mockRejectedValue(new HttpError(409, "A document with this title exists"));
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Written Complaint");

    await user.type(screen.getByLabelText(/new document title/i), "Written Complaint");
    await user.selectOptions(await screen.findByLabelText(/document type/i), "dt-plaint");
    await user.click(screen.getByRole("button", { name: /create document/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("A document with this title exists");
  });

  it("reports a file that is not reachable through this matter", async () => {
    mockedGetFile.mockRejectedValue(
      new HttpError(404, "File with id f1 was not found on this matter"),
    );

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "File with id f1 was not found on this matter",
    );
  });

  it("navigates into a document from the list", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("link", { name: /open/i }));

    expect(await screen.findByText("Document detail page")).toBeInTheDocument();
  });
});
