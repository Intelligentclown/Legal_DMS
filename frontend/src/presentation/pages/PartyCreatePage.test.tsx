import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { PartyCreatePage } from "@/presentation/pages/PartyCreatePage";
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

import { createParty } from "@/infrastructure/api/partiesApi";
import { HttpError } from "@/infrastructure/api/httpClient";

const mockedCreate = createParty as unknown as Mock;

const CREATED = {
  id: "p1",
  party_type: "organization",
  display_name: "Northwind Traders",
  primary_phone: "+91 9876543210",
  primary_email: null,
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

function renderPage() {
  return renderRoute({
    element: <PartyCreatePage />,
    path: "/parties/new",
    initialEntry: "/parties/new",
    routes: [{ path: "/parties", element: <div>Parties page</div> }],
  });
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(screen.getByLabelText(/party type/i), "organization");
  await user.type(screen.getByLabelText(/display name/i), "Northwind Traders");
  await user.type(screen.getByLabelText(/primary phone/i), "+91 9876543210");
}

describe("PartyCreatePage", () => {
  beforeEach(() => {
    mockedCreate.mockReset();
  });

  it("blocks submission and explains what is missing", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /create party/i }));

    expect(await screen.findByText(/choose whether this is an individual/i)).toBeInTheDocument();
    expect(screen.getByText(/display name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/primary phone must be at least/i)).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it("rejects a malformed email before calling the API", async () => {
    const user = userEvent.setup();
    renderPage();

    await fillValidForm(user);
    await user.type(screen.getByLabelText(/primary email/i), "not-an-email");
    await user.click(screen.getByRole("button", { name: /create party/i }));

    expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it("creates the party with the canonical create payload and returns to the list", async () => {
    mockedCreate.mockResolvedValue(CREATED);
    const user = userEvent.setup();
    renderPage();

    await fillValidForm(user);
    await user.type(screen.getByLabelText(/primary email/i), "legal@northwind.example");
    await user.click(screen.getByRole("button", { name: /create party/i }));

    expect(await screen.findByText("Parties page")).toBeInTheDocument();
    expect(mockedCreate).toHaveBeenCalledWith({
      party_type: "organization",
      display_name: "Northwind Traders",
      primary_phone: "+91 9876543210",
      primary_email: "legal@northwind.example",
      notes: null,
    });
  });

  it("sends null rather than an empty string for optional fields left blank", async () => {
    mockedCreate.mockResolvedValue(CREATED);
    const user = userEvent.setup();
    renderPage();

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /create party/i }));

    await screen.findByText("Parties page");
    expect(mockedCreate).toHaveBeenCalledWith(
      expect.objectContaining({ primary_email: null, notes: null }),
    );
  });

  it("shows the backend's message when creation is rejected", async () => {
    mockedCreate.mockRejectedValue(
      new HttpError(409, "A party with this registration identifier already exists"),
    );
    const user = userEvent.setup();
    renderPage();

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /create party/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A party with this registration identifier already exists",
    );
  });

  it("disables the submit button while the request is pending", async () => {
    mockedCreate.mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();
    renderPage();

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /create party/i }));

    expect(await screen.findByRole("button", { name: /creating/i })).toBeDisabled();
  });

  it("offers no field for an internal party identifier", () => {
    renderPage();

    expect(screen.queryByLabelText(/id/i)).not.toBeInTheDocument();
  });
});
