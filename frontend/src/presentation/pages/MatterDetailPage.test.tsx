import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { MatterDetailPage } from "@/presentation/pages/MatterDetailPage";
import { renderRoute } from "@/test/renderRoute";

vi.mock("@/infrastructure/api/mattersApi", () => ({
  getMatter: vi.fn(),
  listMatters: vi.fn(),
  createMatter: vi.fn(),
}));
vi.mock("@/infrastructure/api/partiesApi", () => ({
  getParty: vi.fn(),
  listParties: vi.fn(),
  createParty: vi.fn(),
}));
vi.mock("@/infrastructure/api/lookupsApi", () => ({
  listMatterTypes: vi.fn(),
  listMatterStatuses: vi.fn(),
  listDocumentTypes: vi.fn(),
}));
vi.mock("@/infrastructure/api/filesApi", () => ({
  listMatterFiles: vi.fn(),
  getMatterFile: vi.fn(),
  createMatterFile: vi.fn(),
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

import { getMatter } from "@/infrastructure/api/mattersApi";
import { getParty } from "@/infrastructure/api/partiesApi";
import { listMatterStatuses, listMatterTypes } from "@/infrastructure/api/lookupsApi";
import { createMatterFile, listMatterFiles } from "@/infrastructure/api/filesApi";
import { HttpError } from "@/infrastructure/api/httpClient";

const mockedGetMatter = getMatter as unknown as Mock;
const mockedGetParty = getParty as unknown as Mock;
const mockedMatterTypes = listMatterTypes as unknown as Mock;
const mockedMatterStatuses = listMatterStatuses as unknown as Mock;
const mockedListFiles = listMatterFiles as unknown as Mock;
const mockedCreateFile = createMatterFile as unknown as Mock;

const MATTER = {
  id: "m1",
  matter_number: "MAT-2026-ABC123",
  matter_type_id: "mt-civil",
  matter_status_id: "ms-open",
  title: "Northwind v. Contoso",
  description: null,
  opened_at: "2026-01-05T00:00:00Z",
  closed_at: null,
  legacy_client_id: null,
  participants: [{ party_id: "p1", role: "client" }],
};

const FILES = [
  { id: "f1", matter_id: "m1", file_number: 1, title: "Pleadings", version: 1 },
  { id: "f2", matter_id: "m1", file_number: 2, title: "Discovery", version: 1 },
];

function filesPage(items: unknown[]) {
  return { items, pagination: { page: 1, page_size: 20, total: items.length, total_pages: 1 } };
}

function renderPage() {
  return renderRoute({
    element: <MatterDetailPage />,
    path: "/matters/:matterId",
    initialEntry: "/matters/m1",
    routes: [
      { path: "/matters/m1/files/f1", element: <div>File detail page</div> },
      { path: "/matters", element: <div>Matters page</div> },
    ],
  });
}

describe("MatterDetailPage", () => {
  beforeEach(() => {
    mockedGetMatter.mockReset().mockResolvedValue(MATTER);
    mockedGetParty.mockReset().mockResolvedValue({ id: "p1", display_name: "Northwind Traders" });
    mockedMatterTypes
      .mockReset()
      .mockResolvedValue([
        { id: "mt-civil", code: "CIV", name: "Civil Litigation", is_active: true },
      ]);
    mockedMatterStatuses
      .mockReset()
      .mockResolvedValue([{ id: "ms-open", code: "OPEN", name: "Open", is_terminal: false }]);
    mockedListFiles.mockReset().mockResolvedValue(filesPage(FILES));
    mockedCreateFile.mockReset();
  });

  it("resolves the canonical client participant to the party's display name", async () => {
    renderPage();

    expect(await screen.findByText("Northwind Traders")).toBeInTheDocument();
    expect(mockedGetParty).toHaveBeenCalledWith("p1");
  });

  it("shows the matter type and status by name, not by internal id", async () => {
    renderPage();

    await screen.findByText("Northwind Traders");
    expect(screen.getByText("Civil Litigation", { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByText("Open", { selector: "dd" })).toBeInTheDocument();
    expect(screen.queryByText("mt-civil")).not.toBeInTheDocument();
    expect(screen.queryByText("ms-open")).not.toBeInTheDocument();
  });

  it("displays the backend-assigned file numbers verbatim", async () => {
    renderPage();

    expect(await screen.findByText("Pleadings")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("reports that the client is not recorded when the matter has no client participant", async () => {
    mockedGetMatter.mockResolvedValue({ ...MATTER, participants: [] });

    renderPage();

    expect(await screen.findByText("Not recorded")).toBeInTheDocument();
    expect(mockedGetParty).not.toHaveBeenCalled();
  });

  it("shows the backend's message when the matter is not found", async () => {
    mockedGetMatter.mockRejectedValue(new HttpError(404, "Matter with id m1 was not found"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Matter with id m1 was not found");
  });

  it("shows an empty state for a matter with no files", async () => {
    mockedListFiles.mockResolvedValue(filesPage([]));

    renderPage();

    expect(await screen.findByText(/no files on this matter yet/i)).toBeInTheDocument();
  });

  it("requires a title before creating a file", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pleadings");

    await user.click(screen.getByRole("button", { name: /create file/i }));

    expect(await screen.findByText(/file title is required/i)).toBeInTheDocument();
    expect(mockedCreateFile).not.toHaveBeenCalled();
  });

  it("creates a file from the title alone and reports the backend's number", async () => {
    mockedCreateFile.mockResolvedValue({
      id: "f3",
      matter_id: "m1",
      file_number: 3,
      title: "Orders",
      version: 1,
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pleadings");

    await user.type(screen.getByLabelText(/new file title/i), "Orders");
    await user.click(screen.getByRole("button", { name: /create file/i }));

    await waitFor(() => expect(mockedCreateFile).toHaveBeenCalledWith("m1", { title: "Orders" }));
    expect(
      await screen.findByText(/file number 3 was assigned by the backend/i),
    ).toBeInTheDocument();
  });

  it("never sends a file number of its own", async () => {
    mockedCreateFile.mockResolvedValue({
      id: "f3",
      matter_id: "m1",
      file_number: 3,
      title: "Orders",
      version: 1,
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pleadings");

    await user.type(screen.getByLabelText(/new file title/i), "Orders");
    await user.click(screen.getByRole("button", { name: /create file/i }));

    await waitFor(() => expect(mockedCreateFile).toHaveBeenCalled());
    expect(mockedCreateFile.mock.calls[0][1]).not.toHaveProperty("file_number");
  });

  it("refreshes the file list after a successful create", async () => {
    mockedCreateFile.mockResolvedValue({
      id: "f3",
      matter_id: "m1",
      file_number: 3,
      title: "Orders",
      version: 1,
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pleadings");
    const callsBefore = mockedListFiles.mock.calls.length;

    await user.type(screen.getByLabelText(/new file title/i), "Orders");
    await user.click(screen.getByRole("button", { name: /create file/i }));

    await waitFor(() => expect(mockedListFiles.mock.calls.length).toBeGreaterThan(callsBefore));
  });

  it("surfaces a permission failure when creating a file", async () => {
    mockedCreateFile.mockRejectedValue(new HttpError(403, "You do not have files:write"));
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pleadings");

    await user.type(screen.getByLabelText(/new file title/i), "Orders");
    await user.click(screen.getByRole("button", { name: /create file/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have files:write");
  });

  it("navigates into a file from the list", async () => {
    const user = userEvent.setup();
    renderPage();

    const openButtons = await screen.findAllByRole("link", { name: /open/i });
    await user.click(openButtons[0]);

    expect(await screen.findByText("File detail page")).toBeInTheDocument();
  });
});
