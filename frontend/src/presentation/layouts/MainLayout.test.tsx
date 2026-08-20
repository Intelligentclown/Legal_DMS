import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { MainLayout } from "@/presentation/layouts/MainLayout";

const mockUseAuth = vi.fn();

vi.mock("@/app/providers/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
}));

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<div>Page content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("MainLayout", () => {
  it("displays the authenticated current user's name in the header", () => {
    mockUseAuth.mockReturnValue({
      currentUser: { id: "u1", display_name: "Jane Doe", roles: ["Administrator"] },
      tokens: { access_token: "access-123", refresh_token: "refresh-456" },
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderLayout();

    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("Page content")).toBeInTheDocument();
  });

  it("does not render the user/logout block when there is no current user", () => {
    mockUseAuth.mockReturnValue({
      currentUser: null,
      tokens: null,
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderLayout();

    expect(screen.queryByRole("button", { name: /log out/i })).not.toBeInTheDocument();
  });

  it("calls logout() when the Log out button is clicked", async () => {
    const logout = vi.fn().mockResolvedValue(undefined);
    mockUseAuth.mockReturnValue({
      currentUser: { id: "u1", display_name: "Jane Doe", roles: ["Administrator"] },
      tokens: { access_token: "access-123", refresh_token: "refresh-456" },
      login: vi.fn(),
      logout,
    });
    const user = userEvent.setup();

    renderLayout();
    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(logout).toHaveBeenCalledTimes(1);
  });

  it("disables the logout button while logout() is pending", async () => {
    mockUseAuth.mockReturnValue({
      currentUser: { id: "u1", display_name: "Jane Doe", roles: ["Administrator"] },
      tokens: { access_token: "access-123", refresh_token: "refresh-456" },
      login: vi.fn(),
      logout: vi.fn().mockReturnValue(new Promise(() => {})),
    });
    const user = userEvent.setup();

    renderLayout();
    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(screen.getByRole("button", { name: /logging out/i })).toBeDisabled();
  });
});
