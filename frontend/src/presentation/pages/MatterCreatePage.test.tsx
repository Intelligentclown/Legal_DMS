import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { MatterCreatePage } from "@/presentation/pages/MatterCreatePage";
import { renderRoute } from "@/test/renderRoute";

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

import { getParty } from "@/infrastructure/api/partiesApi";
import { listMatterStatuses, listMatterTypes } from "@/infrastructure/api/lookupsApi";
import { createMatter } from "@/infrastructure/api/mattersApi";
import { HttpError } from "@/infrastructure/api/httpClient";

const mockedGetParty = getParty as unknown as Mock;
const mockedMatterTypes = listMatterTypes as unknown as Mock;
const mockedMatterStatuses = listMatterStatuses as unknown as Mock;
const mockedCreate = createMatter as unknown as Mock;

const PARTY = { id: "p1", display_name: "Northwind Traders" };

const MATTER_TYPES = [
  { id: "mt-civil", code: "CIV", name: "Civil Litigation", is_active: true },
  { id: "mt-retired", code: "OLD", name: "Retired Practice", is_active: false },
];

const MATTER_STATUSES = [
  { id: "ms-open", code: "OPEN", name: "Open", is_terminal: false },
  { id: "ms-closed", code: "CLOSED", name: "Closed", is_terminal: true },
];

const CREATED = { id: "m1", matter_number: "MAT-2026-ABC123" };

function renderPage() {
  return renderRoute({
    element: <MatterCreatePage />,
    path: "/parties/:partyId/matters/new",
    initialEntry: "/parties/p1/matters/new",
    routes: [{ path: "/matters/m1", element: <div>Matter detail page</div> }],
  });
}

async function ready(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByLabelText(/matter type/i);
  await user.selectOptions(screen.getByLabelText(/matter type/i), "mt-civil");
  await user.selectOptions(screen.getByLabelText(/matter status/i), "ms-open");
  await user.type(screen.getByLabelText(/^title/i), "Northwind v. Contoso");
}

describe("MatterCreatePage", () => {
  beforeEach(() => {
    mockedGetParty.mockReset().mockResolvedValue(PARTY);
    mockedMatterTypes.mockReset().mockResolvedValue(MATTER_TYPES);
    mockedMatterStatuses.mockReset().mockResolvedValue(MATTER_STATUSES);
    mockedCreate.mockReset();
  });

  it("resolves the party from the route and shows its name instead of an identifier", async () => {
    renderPage();

    expect(
      await screen.findByText(/Northwind Traders will be recorded as the client/i),
    ).toBeInTheDocument();
    expect(mockedGetParty).toHaveBeenCalledWith("p1");
  });

  it("offers the matter types and statuses discovered from the T146 routes", async () => {
    renderPage();

    await screen.findByLabelText(/matter type/i);
    expect(mockedMatterTypes).toHaveBeenCalledTimes(1);
    expect(mockedMatterStatuses).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("option", { name: "Civil Litigation (CIV)" })).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /Closed \(CLOSED\) — terminal/ }),
    ).toBeInTheDocument();
  });

  it("omits deactivated matter types from the selector", async () => {
    renderPage();

    await screen.findByLabelText(/matter type/i);
    expect(screen.queryByRole("option", { name: /Retired Practice/ })).not.toBeInTheDocument();
  });

  it("shows a loading state until the reference vocabularies arrive", () => {
    mockedMatterTypes.mockReturnValue(new Promise(() => {}));
    mockedMatterStatuses.mockReturnValue(new Promise(() => {}));

    renderPage();

    expect(screen.getByText(/loading matter types and statuses/i)).toBeInTheDocument();
  });

  it("reports a lookup failure instead of offering an empty selector", async () => {
    mockedMatterTypes.mockRejectedValue(new HttpError(403, "You do not have matters:read"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have matters:read");
    expect(screen.queryByLabelText(/matter type/i)).not.toBeInTheDocument();
  });

  it("requires a type and a status to be chosen", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByLabelText(/matter type/i);

    await user.type(screen.getByLabelText(/^title/i), "Northwind v. Contoso");
    await user.click(screen.getByRole("button", { name: /create matter/i }));

    expect(await screen.findByText(/choose a matter type/i)).toBeInTheDocument();
    expect(screen.getByText(/choose a matter status/i)).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it("creates the matter with the party from the route as the canonical client", async () => {
    mockedCreate.mockResolvedValue(CREATED);
    const user = userEvent.setup();
    renderPage();
    await ready(user);

    await user.click(screen.getByRole("button", { name: /create matter/i }));

    expect(await screen.findByText("Matter detail page")).toBeInTheDocument();
    const payload = mockedCreate.mock.calls[0][0] as Record<string, unknown>;
    expect(payload).toMatchObject({
      matter_type_id: "mt-civil",
      matter_status_id: "ms-open",
      title: "Northwind v. Contoso",
      client_party_id: "p1",
    });
    expect(payload.matter_number).toMatch(/^MAT-\d{8}-[A-Z0-9]+$/);
    expect(payload.opened_at).toMatch(/Z$/);
  });

  it("lets the user replace the suggested matter number", async () => {
    mockedCreate.mockResolvedValue(CREATED);
    const user = userEvent.setup();
    renderPage();
    await ready(user);

    const numberField = screen.getByLabelText(/matter number/i);
    await user.clear(numberField);
    await user.type(numberField, "NWD/2026/014");
    await user.click(screen.getByRole("button", { name: /create matter/i }));

    await screen.findByText("Matter detail page");
    expect(mockedCreate.mock.calls[0][0]).toMatchObject({ matter_number: "NWD/2026/014" });
  });

  it("surfaces a duplicate-number conflict from the backend", async () => {
    mockedCreate.mockRejectedValue(new HttpError(409, "Matter number MAT-1 is already in use"));
    const user = userEvent.setup();
    renderPage();
    await ready(user);

    await user.click(screen.getByRole("button", { name: /create matter/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Matter number MAT-1 is already in use",
    );
  });

  it("exposes no field for typing an internal matter, type or status id", () => {
    renderPage();

    expect(screen.queryByLabelText(/matter type id/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/status id/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/client party id/i)).not.toBeInTheDocument();
  });
});
