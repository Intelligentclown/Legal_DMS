import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { PartiesPage } from "@/presentation/pages/PartiesPage";
import { renderRoute } from "@/test/renderRoute";

vi.mock("@/infrastructure/api/partiesApi", () => ({
  listParties: vi.fn(),
  getParty: vi.fn(),
  createParty: vi.fn(),
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

import { listParties } from "@/infrastructure/api/partiesApi";
import { HttpError } from "@/infrastructure/api/httpClient";

const mockedList = listParties as unknown as Mock;

const PARTY = {
  id: "p1",
  party_type: "organization",
  display_name: "Northwind Traders",
  primary_phone: "+91 9876543210",
  primary_email: "legal@northwind.example",
  address_id: null,
  notes: null,
  pan_number: null,
  aadhaar_number: null,
  gstin: null,
  registration_identifier: null,
  date_of_birth: null,
  gender: null,
  occupation: null,
  incorporation_date: null,
};

function page(items: unknown[], overrides: Record<string, unknown> = {}) {
  return {
    items,
    pagination: { page: 1, page_size: 20, total: items.length, total_pages: 1 },
    ...overrides,
  };
}

function renderPage() {
  return renderRoute({
    element: <PartiesPage />,
    path: "/parties",
    initialEntry: "/parties",
    routes: [
      { path: "/parties/new", element: <div>New party page</div> },
      { path: "/parties/p1/matters/new", element: <div>New matter page</div> },
    ],
  });
}

describe("PartiesPage", () => {
  beforeEach(() => {
    mockedList.mockReset();
  });

  it("shows a loading state, then the parties the backend returned", async () => {
    mockedList.mockResolvedValue(page([PARTY]));

    renderPage();
    expect(screen.getByText(/loading parties/i)).toBeInTheDocument();

    expect(await screen.findByText("Northwind Traders")).toBeInTheDocument();
    expect(screen.getByText("Organization")).toBeInTheDocument();
    expect(screen.getByText("+91 9876543210")).toBeInTheDocument();
    expect(mockedList).toHaveBeenCalledWith({ page: 1 });
  });

  it("shows an empty state when the organization has no parties", async () => {
    mockedList.mockResolvedValue(page([]));

    renderPage();

    expect(await screen.findByText(/no parties yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("surfaces the backend's own message when the list request fails", async () => {
    mockedList.mockRejectedValue(new HttpError(403, "You do not have parties:read"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have parties:read");
  });

  it("offers a route into creating a matter for the selected party", async () => {
    mockedList.mockResolvedValue(page([PARTY]));
    const user = userEvent.setup();

    renderPage();
    await user.click(await screen.findByRole("link", { name: /new matter/i }));

    expect(await screen.findByText("New matter page")).toBeInTheDocument();
  });

  it("requests the next page when Next is used", async () => {
    mockedList.mockResolvedValue(
      page([PARTY], { pagination: { page: 1, page_size: 20, total: 40, total_pages: 2 } }),
    );
    const user = userEvent.setup();

    renderPage();
    await user.click(await screen.findByRole("button", { name: /next/i }));

    await waitFor(() => expect(mockedList).toHaveBeenLastCalledWith({ page: 2 }));
  });

  it("links to the new-party form", async () => {
    mockedList.mockResolvedValue(page([PARTY]));
    const user = userEvent.setup();

    renderPage();
    await user.click(await screen.findByRole("link", { name: /new party/i }));

    expect(await screen.findByText("New party page")).toBeInTheDocument();
  });

  it("never renders an internal id in the table", async () => {
    mockedList.mockResolvedValue(page([PARTY]));

    renderPage();
    await screen.findByText("Northwind Traders");

    expect(screen.queryByText("p1")).not.toBeInTheDocument();
  });
});
