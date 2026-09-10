import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The ids are build-time constants, so the module under test is imported after the
// config is mocked — one counter of each kind, which is the production shape.
vi.mock("@/shared/config", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/config")>();
  return {
    ...actual,
    env: { ...actual.env, yandexMetricaId: "12345678", googleAnalyticsId: "G-TESTID123" },
  };
});

const {
  analyticsConfigured,
  resetAnalyticsForTests,
  startAnalytics,
  stopAnalytics,
  trackPageView,
} = await import("./trackers");

function loadedScripts(): string[] {
  return [...document.querySelectorAll("script")].map((script) => script.src);
}

/**
 * The gtag commands sitting on `dataLayer`, as command name and arguments.
 *
 * Every entry is asserted to be an Arguments object first, because that is the
 * one thing gtag.js requires and the one thing a plain array silently fails: a
 * command pushed as an array is read as data and never executed.
 */
function gtagCommands(): unknown[][] {
  return (window.dataLayer ?? []).map((entry) => {
    expect(Object.prototype.toString.call(entry)).toBe("[object Arguments]");
    return [...(entry as IArguments)];
  });
}

beforeEach(() => {
  resetAnalyticsForTests();
  document.head.innerHTML = "";
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the counters", () => {
  it("loads nothing until it is started", () => {
    expect(analyticsConfigured()).toBe(true);
    expect(loadedScripts()).toEqual([]);
    expect(window.ym).toBeUndefined();
  });

  it("loads both tags once started", () => {
    expect(startAnalytics()).toBe(true);

    const scripts = loadedScripts();
    expect(scripts.some((src) => src.includes("mc.yandex.ru/metrika/tag.js?id=12345678"))).toBe(
      true,
    );
    expect(scripts.some((src) => src.includes("googletagmanager.com/gtag/js?id=G-TESTID123"))).toBe(
      true,
    );
  });

  it("puts both counters in manual page-view mode", () => {
    startAnalytics();

    const init = window.ym?.a?.find((call) => call[1] === "init");
    expect(init?.[2]).toMatchObject({ defer: true });
    const config = gtagCommands().find((command) => command[0] === "config");
    expect(config?.[1]).toBe("G-TESTID123");
    expect(config?.[2]).toMatchObject({ send_page_view: false });
  });

  it("queues Google's commands as Arguments objects, the only form gtag.js runs", () => {
    startAnalytics();
    trackPageView("/festivals");

    // `gtagCommands` fails the entry that is not an Arguments object; an array
    // reaching `dataLayer` is how the tag loads and reports nothing at all.
    expect(gtagCommands().map((command) => command[0])).toEqual(["js", "config", "event"]);
  });

  it("loads each tag once however often it is started", () => {
    startAnalytics();
    startAnalytics();

    expect(loadedScripts().filter((src) => src.includes("mc.yandex.ru")).length).toBe(1);
  });

  it("sends a hit to both counters for a navigation", () => {
    startAnalytics();

    trackPageView("/festivals?page=2", "Фестивали");

    const hit = window.ym?.a?.find((call) => call[1] === "hit");
    expect(hit?.[2]).toBe(`${window.location.origin}/festivals?page=2`);
    const pageView = gtagCommands().find((command) => command[1] === "page_view");
    expect(pageView?.[2]).toMatchObject({
      page_path: "/festivals?page=2",
      page_title: "Фестивали",
    });
  });

  it("sends nothing while it has not been started", () => {
    trackPageView("/festivals");

    expect(window.ym).toBeUndefined();
    expect(window.dataLayer).toBeUndefined();
  });
});

describe("withdrawing consent", () => {
  it("disables Google and expires the cookies both services set", () => {
    // biome-ignore-start lint/suspicious/noDocumentCookie: setting up the cookies the counters would have written
    document.cookie = "_ym_uid=42; path=/";
    document.cookie = "_ga=GA1.1.7; path=/";
    document.cookie = "vt-session=keep-me; path=/";
    // biome-ignore-end lint/suspicious/noDocumentCookie: setup done
    startAnalytics();

    expect(stopAnalytics()).toBe(true);

    expect((window as unknown as Record<string, boolean>)["ga-disable-G-TESTID123"]).toBe(true);
    expect(document.cookie).not.toContain("_ym_uid");
    expect(document.cookie).not.toContain("_ga=");
    // Only the analytics ones: the session cookie is nobody's business here.
    expect(document.cookie).toContain("vt-session=keep-me");
  });

  it("reports that nothing was running when nothing was", () => {
    expect(stopAnalytics()).toBe(false);
  });

  it("stops sending hits", () => {
    startAnalytics();
    stopAnalytics();
    const before = window.ym?.a?.length ?? 0;

    trackPageView("/festivals");

    expect(window.ym?.a?.length ?? 0).toBe(before);
  });
});
