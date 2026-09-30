import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { DocumentDetailPage } from "@/presentation/pages/DocumentDetailPage";
import { renderRoute } from "@/test/renderRoute";

vi.mock("@/infrastructure/api/documentsApi", () => ({
  listLegalDocuments: vi.fn(),
  getLegalDocument: vi.fn(),
  createLegalDocument: vi.fn(),
}));
vi.mock("@/infrastructure/api/documentVersionsApi", () => ({
  createDocumentVersion: vi.fn(),
  listDocumentVersions: vi.fn(),
  getLatestDocumentVersion: vi.fn(),
  downloadDocumentVersion: vi.fn(),
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
vi.mock("@/shared/utils/download", () => ({ downloadBlob: vi.fn() }));
vi.mock("@/infrastructure/api/httpClient", () => {
  class HttpError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = "HttpError";
      this.status = status;
    }
  }
  return {
    httpClient: { get: vi.fn(), post: vi.fn(), postBinary: vi.fn(), getBinary: vi.fn() },
    HttpError,
  };
});

import { getLegalDocument } from "@/infrastructure/api/documentsApi";
import {
  createDocumentVersion,
  downloadDocumentVersion,
  getLatestDocumentVersion,
  listDocumentVersions,
} from "@/infrastructure/api/documentVersionsApi";
import { getMatterFile } from "@/infrastructure/api/filesApi";
import { getMatter } from "@/infrastructure/api/mattersApi";
import { listDocumentTypes } from "@/infrastructure/api/lookupsApi";
import { downloadBlob } from "@/shared/utils/download";
import { HttpError } from "@/infrastructure/api/httpClient";

const mockedGetDocument = getLegalDocument as unknown as Mock;
const mockedCreateVersion = createDocumentVersion as unknown as Mock;
const mockedListVersions = listDocumentVersions as unknown as Mock;
const mockedLatestVersion = getLatestDocumentVersion as unknown as Mock;
const mockedDownload = downloadDocumentVersion as unknown as Mock;
const mockedGetFile = getMatterFile as unknown as Mock;
const mockedGetMatter = getMatter as unknown as Mock;
const mockedDocumentTypes = listDocumentTypes as unknown as Mock;
const mockedDownloadBlob = downloadBlob as unknown as Mock;

const DOC = {
  id: "d1",
  document_type_id: "dt-plaint",
  title: "Written Complaint",
  status: "draft",
  version: 1,
};
const FILE = { id: "f1", matter_id: "m1", file_number: 1, title: "Pleadings", version: 1 };
const MATTER = { id: "m1", matter_number: "MAT-2026-ABC123", title: "Northwind v. Contoso" };

const VERSIONS = [
  {
    id: "v2",
    version_number: 2,
    change_summary: "Signed copy",
    created_at: "2026-02-02T10:00:00Z",
  },
  {
    id: "v1",
    version_number: 1,
    change_summary: "Initial draft",
    created_at: "2026-02-01T10:00:00Z",
  },
];

function renderPage() {
  return renderRoute({
    element: <DocumentDetailPage />,
    path: "/matters/:matterId/files/:fileId/documents/:documentId",
    initialEntry: "/matters/m1/files/f1/documents/d1",
  });
}

async function chooseFile(name: string, type = "application/pdf") {
  const file = new File(["%PDF-1.7 bytes"], name, { type });
  await userEvent.upload(await screen.findByLabelText(/choose a file/i), file);
  return file;
}

describe("DocumentDetailPage", () => {
  beforeEach(() => {
    mockedGetDocument.mockReset().mockResolvedValue(DOC);
    mockedGetFile.mockReset().mockResolvedValue(FILE);
    mockedGetMatter.mockReset().mockResolvedValue(MATTER);
    mockedDocumentTypes
      .mockReset()
      .mockResolvedValue([{ id: "dt-plaint", code: "PL", name: "Plaint", is_active: true }]);
    mockedListVersions.mockReset().mockResolvedValue(VERSIONS);
    mockedLatestVersion.mockReset().mockResolvedValue(VERSIONS[0]);
    mockedCreateVersion.mockReset();
    mockedDownload.mockReset();
    mockedDownloadBlob.mockReset();
  });

  it("shows the document with its type resolved to a name", async () => {
    renderPage();

    expect((await screen.findAllByText("Written Complaint")).length).toBeGreaterThan(0);
    expect(mockedGetDocument).toHaveBeenCalledWith("m1", "f1", "d1");
    expect(screen.getByText("Plaint", { selector: "dd" })).toBeInTheDocument();
  });

  it("lists the version history in the order the backend returned it", async () => {
    renderPage();

    expect(await screen.findByText("Signed copy")).toBeInTheDocument();
    expect(screen.getByText("Initial draft")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^download$/i })).toHaveLength(2);
  });

  it("shows an empty state when the document has no versions yet", async () => {
    mockedListVersions.mockResolvedValue([]);
    mockedLatestVersion.mockResolvedValue(null);

    renderPage();

    expect(await screen.findByText(/no versions uploaded yet/i)).toBeInTheDocument();
  });

  it("keeps the latest version visible when only that lookup 404s", async () => {
    mockedLatestVersion.mockResolvedValue(null);

    renderPage();

    expect(await screen.findByText("Initial draft")).toBeInTheDocument();
    expect(screen.getByText("1", { selector: "td" })).toBeInTheDocument();
  });

  it("marks the latest version in the history", async () => {
    renderPage();

    expect(await screen.findByText("Signed copy")).toBeInTheDocument();
    expect(screen.getByText("latest")).toBeInTheDocument();
  });

  it("keeps the upload button disabled until a file is chosen", async () => {
    renderPage();
    await screen.findByLabelText(/choose a file/i);

    expect(screen.getByRole("button", { name: /upload version/i })).toBeDisabled();
  });

  it("asks for a file when the upload form is submitted without one", async () => {
    renderPage();
    await screen.findByLabelText(/choose a file/i);

    const form = screen.getByRole("button", { name: /upload version/i }).closest("form");
    form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    expect(await screen.findByText(/choose a file to upload/i)).toBeInTheDocument();
    expect(mockedCreateVersion).not.toHaveBeenCalled();
  });

  it("uploads the raw bytes with the filename and a fresh idempotency key", async () => {
    mockedCreateVersion.mockResolvedValue({ id: "v3", version_number: 3 });
    renderPage();
    await chooseFile("deed.pdf");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /upload version/i }));

    await waitFor(() => expect(mockedCreateVersion).toHaveBeenCalled());
    const [matterId, fileId, documentId, input] = mockedCreateVersion.mock.calls[0] as [
      string,
      string,
      string,
      { content: ArrayBuffer; filename: string; mimeType: string; idempotencyKey: string },
    ];

    expect([matterId, fileId, documentId]).toEqual(["m1", "f1", "d1"]);
    expect(input.filename).toBe("deed.pdf");
    expect(input.mimeType).toBe("application/pdf");
    expect(input.idempotencyKey).toBeTruthy();
    expect(input.content).toBeInstanceOf(ArrayBuffer);
    expect(new TextDecoder().decode(input.content)).toBe("%PDF-1.7 bytes");
  });

  it("mints a different idempotency key for a different chosen file", async () => {
    mockedCreateVersion.mockResolvedValue({ id: "v3", version_number: 3 });
    const user = userEvent.setup();
    renderPage();
    await screen.findByLabelText(/choose a file/i);

    await user.upload(screen.getByLabelText(/choose a file/i), new File(["a"], "a.pdf"));
    await user.upload(screen.getByLabelText(/choose a file/i), new File(["b"], "b.pdf"));
    await user.click(screen.getByRole("button", { name: /upload version/i }));

    await waitFor(() => expect(mockedCreateVersion).toHaveBeenCalled());
    const first = mockedCreateVersion.mock.calls[0][3].idempotencyKey as string;
    expect(first).toBeTruthy();
  });

  it("sends the change summary and clears the form after a successful upload", async () => {
    mockedCreateVersion.mockResolvedValue({ id: "v3", version_number: 3 });
    const user = userEvent.setup();
    renderPage();
    await screen.findByLabelText(/choose a file/i);

    await user.upload(screen.getByLabelText(/choose a file/i), new File(["a"], "a.pdf"));
    await user.type(screen.getByLabelText(/change summary/i), "Filed copy");
    await user.click(screen.getByRole("button", { name: /upload version/i }));

    await waitFor(() =>
      expect(mockedCreateVersion.mock.calls[0][3]).toMatchObject({ changeSummary: "Filed copy" }),
    );
    await waitFor(() => expect(screen.getByLabelText(/change summary/i)).toHaveValue(""));
    expect(screen.getByLabelText(/choose a file/i)).toHaveValue("");
  });

  it("omits the change summary when the note is left blank", async () => {
    mockedCreateVersion.mockResolvedValue({ id: "v3", version_number: 3 });
    renderPage();
    await chooseFile("a.pdf");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /upload version/i }));

    await waitFor(() => expect(mockedCreateVersion).toHaveBeenCalled());
    expect(mockedCreateVersion.mock.calls[0][3].changeSummary).toBeUndefined();
  });

  it("strips path separators from the filename before it becomes a header", async () => {
    mockedCreateVersion.mockResolvedValue({ id: "v3", version_number: 3 });
    renderPage();
    await chooseFile("..\\..\\evil.pdf");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /upload version/i }));

    await waitFor(() => expect(mockedCreateVersion).toHaveBeenCalled());
    expect(mockedCreateVersion.mock.calls[0][3].filename).toBe(".._.._evil.pdf");
  });

  it("surfaces an idempotent-replay conflict from the backend", async () => {
    mockedCreateVersion.mockRejectedValue(
      new HttpError(409, "Idempotency-Key was reused with new content"),
    );
    renderPage();
    await chooseFile("a.pdf");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /upload version/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Idempotency-Key was reused with new content",
    );
  });

  it("downloads a version and names the file from Content-Disposition", async () => {
    const blob = new Blob(["%PDF"]);
    mockedDownload.mockResolvedValue({
      blob,
      contentType: "application/pdf",
      contentDisposition: 'attachment; filename="Board Minutes - March.pdf"',
    });
    const user = userEvent.setup();
    renderPage();

    const downloadButtons = await screen.findAllByRole("button", { name: /^download$/i });
    await user.click(downloadButtons[0]);

    await waitFor(() => expect(mockedDownload).toHaveBeenCalledWith("m1", "f1", "d1", "v2"));
    expect(mockedDownloadBlob).toHaveBeenCalledWith(blob, "Board Minutes - March.pdf");
  });

  it("falls back to a generated name when the download carries no filename", async () => {
    mockedDownload.mockResolvedValue({
      blob: new Blob(["x"]),
      contentType: "application/octet-stream",
      contentDisposition: null,
    });
    const user = userEvent.setup();
    renderPage();

    const downloadButtons = await screen.findAllByRole("button", { name: /^download$/i });
    await user.click(downloadButtons[0]);

    await waitFor(() =>
      expect(mockedDownloadBlob).toHaveBeenCalledWith(expect.anything(), "document-version-2"),
    );
  });

  it("surfaces a download failure", async () => {
    mockedDownload.mockRejectedValue(new HttpError(500, "Stored content failed its checksum"));
    const user = userEvent.setup();
    renderPage();

    const downloadButtons = await screen.findAllByRole("button", { name: /^download$/i });
    await user.click(downloadButtons[0]);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Stored content failed its checksum",
    );
    expect(mockedDownloadBlob).not.toHaveBeenCalled();
  });

  it("reports a document that is not reachable through this file", async () => {
    mockedGetDocument.mockRejectedValue(new HttpError(404, "Document with id d1 was not found"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Document with id d1 was not found");
  });
});
