import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { ROUTES, SUPPORT_EMAIL } from "@/shared/config";
import { OrganizersPage } from "./index";

/**
 * This page is the link an organizer is sent, so what is worth testing is not
 * that it renders — it is the two ways it can quietly stop being presentable
 * while every test stays green:
 *
 * 1. **A screenshot that is not there.** The images live in `public/` and are
 *    referenced by string. Rename one and the page keeps rendering, with holes
 *    where the product used to be — and nobody opens the sales page as often as
 *    they open the app. So every `src` is resolved against the real directory.
 * 2. **An image without reserved space.** Read over a festival's wifi, an image
 *    with no `width`/`height` reflows the paragraph under the reader's thumb.
 */

// `process.cwd()` rather than `import.meta.url`: vitest rewrites the latter to a
// non-file scheme, and the directory is the frontend root either way.
const PUBLIC_DIR = resolve(process.cwd(), "public");

function renderPage(): HTMLElement {
  const { container } = render(
    <MemoryRouter initialEntries={[ROUTES.organizers]}>
      <OrganizersPage />
    </MemoryRouter>,
  );
  return container;
}

describe("OrganizersPage", () => {
  it("says what the platform is for in the heading", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { level: 1, name: /от заявки до диплома/i }),
    ).toBeInTheDocument();
  });

  it("ships every screenshot it references", () => {
    const container = renderPage();
    const sources = Array.from(container.querySelectorAll("img")).map((img) =>
      img.getAttribute("src"),
    );

    expect(sources.length).toBeGreaterThan(0);
    for (const src of sources) {
      expect(src).toMatch(/^\/organizers\/.+\.webp$/);
      expect(existsSync(resolve(PUBLIC_DIR, (src ?? "").slice(1))), `missing ${src}`).toBe(true);
    }
  });

  it("reserves the space each screenshot will take, and names it", () => {
    const container = renderPage();

    for (const img of Array.from(container.querySelectorAll("img"))) {
      expect(Number(img.getAttribute("width"))).toBeGreaterThan(0);
      expect(Number(img.getAttribute("height"))).toBeGreaterThan(0);
      // Alt text carries the screen for a reader who cannot see it, so it is a
      // sentence rather than a filename.
      expect((img.getAttribute("alt") ?? "").length).toBeGreaterThan(20);
    }
  });

  it("points the call to action at the address the platform publishes", () => {
    const container = renderPage();
    const mailto = Array.from(container.querySelectorAll('a[href^="mailto:"]'));

    expect(mailto.length).toBeGreaterThan(0);
    for (const link of mailto) {
      expect(link.getAttribute("href")).toContain(SUPPORT_EMAIL);
    }
  });
});
