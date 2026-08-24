import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "@/app/ProtectedRoute";

const mockUseAuth = vi.fn();

vi.mock("@/app/providers/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
}));

function renderAtRoot() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<div>Protected content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("redirects unauthenticated users to /login", () => {
    mockUseAuth.mockReturnValue({
      currentUser: null,
      tokens: null,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderAtRoot();

    expect(screen.getByText("Login page")).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("renders the protected content for authenticated users", () => {
    mockUseAuth.mockReturnValue({
      currentUser: { id: "u1", display_name: "Jane Doe", roles: ["Administrator"] },
      tokens: { access_token: "access-123", refresh_token: "refresh-456" },
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderAtRoot();

    expect(screen.getByText("Protected content")).toBeInTheDocument();
    expect(screen.queryByText("Login page")).not.toBeInTheDocument();
  });

  it("does not redirect to /login while session restoration is still in progress", () => {
    mockUseAuth.mockReturnValue({
      currentUser: null,
      tokens: null,
      isInitializing: true,
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderAtRoot();

    expect(screen.queryByText("Login page")).not.toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
