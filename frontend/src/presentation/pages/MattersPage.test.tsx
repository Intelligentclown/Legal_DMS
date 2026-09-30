import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { MattersPage } from "@/presentation/pages/MattersPage";
import { renderRoute } from "@/test/renderRoute";

vi.mock("@/infrastructure/api/mattersApi", () => ({
  listMatters: vi.fn(),
  getMatter: vi.fn(),
  createMatter: vi.fn(),
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

import { listMatters } from "@/infrastructure/api/mattersApi";
import { HttpError } from "@/infrastructure/api/httpClient";

const mockedList = listMatters as unknown as Mock;

const MATTERS = [
  {
    id: "m1",
    matter_number: "MAT-2026-ABC123",
    matter_type_id: "mt-civil",
    matter_status_id: "ms-open",
    title: "Northwind v. Contoso",
    description: null,
    opened_at: "2026-01-05T00:00:00Z",
    closed_at: null,
    legacy_client_id: 7,
    participants: [],
  },
  {
    id: "m2",
    matter_number: "MAT-2026-DEF456",
    matter_type_id: "mt-civil",
    matter_status_id: "ms-closed",
    title: "Contoso v. Fabrikam",
    description: null,
    opened_at: "2025-06-01T00:00:00Z",
    closed_at: "2025-09-01T00:00:00Z",
    legacy_client_id: null,
    participants: [],
  },
];

function mattersPage(items: unknown[], overrides: Record<string, unknown> = {}) {
  return {
    items,
    pagination: { page: 1, page_size: 20, total: items.length, total_pages: 1 },
    ...overrides,
  };
}

function renderPage() {
  return renderRoute({
    element: <MattersPage />,
    path: "/matters",
    initialEntry: "/matters",
    routes: [{ path: "/matters/m1", element: <div>Matter detail page</div> }],
  });
}

describe("MattersPage", () => {
  beforeEach(() => {
    mockedList.mockReset();
  });

  it("lists matters by their backend-issued number and title", async () => {
    mockedList.mockResolvedValue(mattersPage(MATTERS));

    renderPage();

    expect(await screen.findByText("MAT-2026-ABC123")).toBeInTheDocument();
    expect(screen.getByText("Northwind v. Contoso")).toBeInTheDocument();
    expect(mockedList).toHaveBeenCalledWith({ page: 1 });
  });

  it("shows an empty state when no matter exists", async () => {
    mockedList.mockResolvedValue(mattersPage([]));

    renderPage();

    expect(await screen.findByText(/no matters yet/i)).toBeInTheDocument();
  });

  it("surfaces a permission failure", async () => {
    mockedList.mockRejectedValue(new HttpError(403, "You do not have matters:read"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have matters:read");
  });

  it("navigates into a matter", async () => {
    mockedList.mockResolvedValue(mattersPage(MATTERS));
    const user = userEvent.setup();
    renderPage();

    const openLinks = await screen.findAllByRole("link", { name: /open/i });
    await user.click(openLinks[0]);

    expect(await screen.findByText("Matter detail page")).toBeInTheDocument();
  });

  it("pages through the list using the backend's own pagination metadata", async () => {
    mockedList.mockImplementation((params: { page: number }) =>
      Promise.resolve(
        mattersPage(MATTERS, {
          pagination: { page: params.page, page_size: 20, total: 45, total_pages: 3 },
        }),
      ),
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /next/i }));
    await waitFor(() => expect(mockedList).toHaveBeenLastCalledWith({ page: 2 }));

    await user.click(await screen.findByRole("button", { name: /next/i }));
    await waitFor(() => expect(mockedList).toHaveBeenLastCalledWith({ page: 3 }));

    await user.click(await screen.findByRole("button", { name: /previous/i }));
    await waitFor(() => expect(mockedList).toHaveBeenLastCalledWith({ page: 2 }));
  });

  it("keeps Previous disabled on the first page", async () => {
    mockedList.mockResolvedValue(
      mattersPage(MATTERS, { pagination: { page: 1, page_size: 20, total: 45, total_pages: 3 } }),
    );

    renderPage();
    await screen.findByText("MAT-2026-ABC123");

    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /next/i })).toBeEnabled();
  });

  it("does not surface the legacy client column as a client identity", async () => {
    mockedList.mockResolvedValue(mattersPage(MATTERS));

    renderPage();
    await screen.findByText("MAT-2026-ABC123");

    expect(screen.queryByText("7")).not.toBeInTheDocument();
  });
});
