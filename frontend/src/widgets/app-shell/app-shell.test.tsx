import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { ROUTES } from "@/shared/config";
import { SIDEBAR_STORAGE_KEY } from "@/shared/constants";
import { AppShell } from "./app-shell";

beforeAll(() => {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.scrollIntoView = () => {};
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

/** Force the `useMediaQuery` result (max-width: 767px) to model mobile/desktop. */
function setViewport(isMobile: boolean): void {
  window.matchMedia = ((query: string) => ({
    matches: isMobile,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

function renderShell(initialPath: string = ROUTES.cabinet) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AppShell headerActions={<button type="button">Меню пользователя</button>}>
        <p>Содержимое страницы</p>
      </AppShell>
    </MemoryRouter>,
  );
}

afterEach(() => {
  window.localStorage.clear();
  setViewport(false);
});

describe("AppShell — navigation rendering", () => {
  it("renders the desktop sidebar with primary navigation landmarks", () => {
    setViewport(false);
    renderShell();
    expect(screen.getByRole("complementary", { name: "Боковая навигация" })).toBeInTheDocument();
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("renders top-level navigation links from the model", () => {
    setViewport(false);
    renderShell();
    const sidebar = screen.getByRole("complementary", { name: "Боковая навигация" });
    expect(within(sidebar).getByRole("link", { name: "Кабинет" })).toBeInTheDocument();
    expect(within(sidebar).getByRole("link", { name: "Участники" })).toBeInTheDocument();
    expect(within(sidebar).getByRole("button", { name: "Фестивали" })).toBeInTheDocument();
  });

  it("renders group headings", () => {
    setViewport(false);
    renderShell();
    // "Реестр" is a group heading with no same-named item (unambiguous).
    expect(screen.getByText("Реестр")).toBeInTheDocument();
    // "Судейство" is both a group heading and a nav item → at least two nodes.
    expect(screen.getAllByText("Судейство").length).toBeGreaterThanOrEqual(2);
  });

  it("provides a skip-to-content link and a focusable main region", () => {
    setViewport(false);
    renderShell();
    expect(screen.getByRole("link", { name: "Перейти к содержимому" })).toHaveAttribute(
      "href",
      "#app-shell-main",
    );
    expect(screen.getByRole("main")).toHaveAttribute("id", "app-shell-main");
  });

  it("renders app-injected header actions", () => {
    setViewport(false);
    renderShell();
    expect(screen.getByRole("button", { name: "Меню пользователя" })).toBeInTheDocument();
  });
});

describe("AppShell — sidebar collapse", () => {
  it("collapses and expands the sidebar via the toggle, persisting the choice", async () => {
    setViewport(false);
    const user = userEvent.setup();
    renderShell();

    const sidebar = screen.getByRole("complementary", { name: "Боковая навигация" });
    expect(sidebar).toHaveAttribute("data-collapsed", "false");

    await user.click(screen.getByRole("button", { name: "Свернуть меню" }));
    expect(sidebar).toHaveAttribute("data-collapsed", "true");
    expect(window.localStorage.getItem(SIDEBAR_STORAGE_KEY)).toBe("true");

    await user.click(screen.getByRole("button", { name: "Развернуть меню" }));
    expect(sidebar).toHaveAttribute("data-collapsed", "false");
    expect(window.localStorage.getItem(SIDEBAR_STORAGE_KEY)).toBe("false");
  });

  it("restores the persisted collapsed state on mount", () => {
    setViewport(false);
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, "true");
    renderShell();
    expect(screen.getByRole("complementary", { name: "Боковая навигация" })).toHaveAttribute(
      "data-collapsed",
      "true",
    );
  });
});

describe("AppShell — nested navigation & keyboard", () => {
  it("expands a nested branch to reveal its children", async () => {
    setViewport(false);
    const user = userEvent.setup();
    renderShell();

    const branch = screen.getByRole("button", { name: "Фестивали" });
    expect(branch).toHaveAttribute("aria-expanded", "false");

    await user.click(branch);
    expect(branch).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Заявки" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Выступления" })).toBeInTheDocument();
  });

  it("auto-expands the branch containing the active route", () => {
    setViewport(false);
    renderShell("/applications");
    expect(screen.getByRole("button", { name: "Фестивали" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("operates the collapse toggle with the keyboard", async () => {
    setViewport(false);
    const user = userEvent.setup();
    renderShell();
    const toggle = screen.getByRole("button", { name: "Свернуть меню" });
    toggle.focus();
    expect(toggle).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("complementary", { name: "Боковая навигация" })).toHaveAttribute(
      "data-collapsed",
      "true",
    );
  });
});

describe("AppShell — breadcrumbs", () => {
  it("derives the breadcrumb trail for a top-level route", () => {
    setViewport(false);
    renderShell("/participants");
    const crumbs = screen.getByRole("navigation", { name: "Хлебные крошки" });
    expect(within(crumbs).getByText("Участники")).toBeInTheDocument();
    expect(within(crumbs).getByText("Участники")).toHaveAttribute("aria-current", "page");
  });

  it("derives a nested trail (parent › child)", () => {
    setViewport(false);
    renderShell("/applications");
    const crumbs = screen.getByRole("navigation", { name: "Хлебные крошки" });
    expect(within(crumbs).getByRole("link", { name: "Фестивали" })).toBeInTheDocument();
    expect(within(crumbs).getByText("Заявки")).toHaveAttribute("aria-current", "page");
  });

  it("renders no breadcrumbs for paths outside the navigation model", () => {
    setViewport(false);
    renderShell("/profile");
    expect(screen.queryByRole("navigation", { name: "Хлебные крошки" })).not.toBeInTheDocument();
  });
});

describe("AppShell — responsive (mobile drawer)", () => {
  it("hides the desktop sidebar toggle and shows a menu button on mobile", () => {
    setViewport(true);
    renderShell();
    expect(screen.getByRole("button", { name: "Открыть меню" })).toBeInTheDocument();
  });

  it("opens the navigation drawer from the mobile menu button", async () => {
    setViewport(true);
    const user = userEvent.setup();
    renderShell();

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Открыть меню" }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: "Участники" })).toBeInTheDocument();
  });
});
