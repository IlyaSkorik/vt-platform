import { beforeEach, describe, expect, it } from "vitest";
import { resetDocumentHeadState, SEO_PRIORITY, writeDocumentHead } from "./document-head";

const SITE = "Взлёт талантов";

function write(
  seo: Parameters<typeof writeDocumentHead>[0],
  options: Partial<Parameters<typeof writeDocumentHead>[1]> = {},
): boolean {
  return writeDocumentHead(seo, {
    location: "/competitions",
    priority: SEO_PRIORITY.page,
    siteName: SITE,
    ...options,
  });
}

function meta(selector: string): string | null {
  return document.head.querySelector(selector)?.getAttribute("content") ?? null;
}

function canonical(): string | null {
  return document.head.querySelector('link[rel="canonical"]')?.getAttribute("href") ?? null;
}

beforeEach(() => {
  document.head.innerHTML = "";
  document.title = "";
  resetDocumentHeadState();
});

describe("writeDocumentHead", () => {
  it("composes the page name with the site name", () => {
    write({ title: "Фестивали" });
    expect(document.title).toBe("Фестивали — Взлёт талантов");
  });

  it("leaves a standalone title alone", () => {
    write({ title: "Взлёт талантов — конкурсы", standaloneTitle: true });
    expect(document.title).toBe("Взлёт талантов — конкурсы");
  });

  it("writes the description to both the meta tag and Open Graph", () => {
    write({ title: "Фестивали", description: "Каталог конкурсов" });
    expect(meta('meta[name="description"]')).toBe("Каталог конкурсов");
    expect(meta('meta[property="og:description"]')).toBe("Каталог конкурсов");
  });

  it("says nothing about robots when the page is indexable", () => {
    write({ title: "Фестивали" });
    expect(document.head.querySelector('meta[name="robots"]')).toBeNull();
  });

  it("refuses indexing and withholds the canonical together", () => {
    write({ title: "Кабинет", canonical: "https://example.by/cabinet", robots: "noindex" });
    expect(meta('meta[name="robots"]')).toBe("noindex, nofollow");
    expect(canonical()).toBeNull();
  });

  it("upgrades the twitter card when there is an image to show", () => {
    write({ title: "Фестиваль", image: "https://cdn.example.by/poster.jpg", imageAlt: "Афиша" });
    expect(meta('meta[name="twitter:card"]')).toBe("summary_large_image");
    expect(meta('meta[property="og:image"]')).toBe("https://cdn.example.by/poster.jpg");
    expect(meta('meta[property="og:image:alt"]')).toBe("Афиша");
  });

  it("replaces rather than accumulates across navigations", () => {
    write({ title: "Первый", description: "Один" });
    write({ title: "Второй", description: "Два" }, { location: "/competitions/2" });

    expect(document.head.querySelectorAll('meta[name="description"]')).toHaveLength(1);
    expect(meta('meta[name="description"]')).toBe("Два");
  });

  it("clears a tag the previous page set and this one does not", () => {
    write({ title: "С картинкой", image: "https://cdn.example.by/poster.jpg" });
    write({ title: "Без картинки" }, { location: "/competitions/2" });

    expect(document.head.querySelector('meta[property="og:image"]')).toBeNull();
  });

  it("never removes a tag it did not write", () => {
    // What a server-rendered head, or index.html, would have put there.
    document.head.innerHTML = '<meta name="author" content="VT">';
    write({ title: "Фестивали" });

    expect(meta('meta[name="author"]')).toBe("VT");
  });
});

describe("taking over a server-rendered head", () => {
  /**
   * What `config/spa.py` splices into the shell before the bundle loads. The
   * marker is the contract: it is how this writer knows which tags are its to
   * update and to clear.
   */
  function serverRendered(): void {
    document.title = "Весенний вокал — 2026 — Взлёт талантов";
    document.head.innerHTML = [
      '<meta name="description" content="Конкурс юных вокалистов" data-seo>',
      '<meta property="og:title" content="Весенний вокал — 2026 — Взлёт талантов" data-seo>',
      '<meta property="og:image" content="https://cdn.example.by/poster.jpg" data-seo>',
      '<link rel="canonical" href="https://example.by/competitions/vesenniy-vokal-2026" data-seo>',
    ].join("");
  }

  it("updates the server's tags in place instead of adding a second set", () => {
    // The failure this prevents: two og:title tags, where the crawler and the
    // browser both honour the first — which would be the stale server one.
    serverRendered();

    write({
      title: "Весенний вокал — 2026",
      description: "Конкурс юных вокалистов",
      canonical: "https://example.by/competitions/vesenniy-vokal-2026",
    });

    expect(document.head.querySelectorAll('meta[property="og:title"]')).toHaveLength(1);
    expect(document.head.querySelectorAll('meta[name="description"]')).toHaveLength(1);
    expect(document.head.querySelectorAll('link[rel="canonical"]')).toHaveLength(1);
  });

  it("clears a server tag the client-side page does not set", () => {
    serverRendered();

    write({ title: "Фестивали" }, { location: "/competitions" });

    expect(document.head.querySelector('meta[property="og:image"]')).toBeNull();
  });

  it("carries the canonical over to the page navigated to", () => {
    serverRendered();

    write({ title: "Фестивали", canonical: "https://example.by/competitions" }, { location: "/competitions" });

    expect(canonical()).toBe("https://example.by/competitions");
  });
});

describe("the priority contest", () => {
  it("lets a page outrank the layout that renders it", () => {
    // Effects run child-first: the page writes, then the layout's fallback.
    expect(write({ title: "Фестиваль «Гармония»" })).toBe(true);
    expect(write({ title: "Взлёт талантов" }, { priority: SEO_PRIORITY.layout })).toBe(false);
    expect(document.title).toBe("Фестиваль «Гармония» — Взлёт талантов");
  });

  it("lets the layout speak when the page says nothing", () => {
    expect(write({ title: "Взлёт талантов" }, { priority: SEO_PRIORITY.layout })).toBe(true);
    expect(document.title).toBe("Взлёт талантов — Взлёт талантов");
  });

  it("restarts the contest on the next location", () => {
    write({ title: "Страница" });
    expect(
      write({ title: "Раздел" }, { location: "/cabinet", priority: SEO_PRIORITY.layout }),
    ).toBe(true);
  });

  it("honours a section's refusal even though the page wrote last", () => {
    // The exact leak this guards: a cabinet page that names itself must not
    // re-open the cabinet to crawlers by outranking the guard's noindex.
    write({ title: "Мои заявки", canonical: "https://example.by/cabinet/applications" });
    write({ title: "Взлёт талантов", robots: "noindex" }, { priority: SEO_PRIORITY.layout });

    expect(meta('meta[name="robots"]')).toBe("noindex, nofollow");
    expect(document.title).toBe("Мои заявки — Взлёт талантов");
  });

  it("drops the refusal once the reader leaves the private section", () => {
    write({ title: "Мои заявки", robots: "noindex" }, { location: "/cabinet" });
    write({ title: "Фестивали" }, { location: "/competitions" });

    expect(document.head.querySelector('meta[name="robots"]')).toBeNull();
  });
});
