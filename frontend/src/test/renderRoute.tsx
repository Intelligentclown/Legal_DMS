import { render, type RenderOptions } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { NotificationProvider } from "@/app/providers/NotificationProvider";

export interface RouteStub {
  path: string;
  element: ReactNode;
}

export interface RenderRouteOptions extends Omit<RenderOptions, "wrapper"> {
  /** The page under test. */
  element: ReactNode;
  /** Route pattern the page is mounted at, e.g. `/matters/:matterId`. */
  path: string;
  /** Concrete URL to start on, e.g. `/matters/m1`. */
  initialEntry: string;
  /** Other destinations, so navigation performed by the page is observable. */
  routes?: RouteStub[];
}

/**
 * Renders a single page at a concrete route with a MemoryRouter, the
 * notification provider every page that mutates depends on, and any navigation
 * targets the test needs to assert against.
 */
export function renderRoute({
  element,
  path,
  initialEntry,
  routes = [],
  ...options
}: RenderRouteOptions) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <NotificationProvider>
        <Routes>
          <Route path={path} element={element} />
          {routes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
        </Routes>
      </NotificationProvider>
    </MemoryRouter>,
    options,
  );
}
