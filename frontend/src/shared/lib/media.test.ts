import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveMediaUrl } from "./media";

/**
 * Point `env.apiBaseUrl` at a value and re-import the module under test.
 *
 * The base is read through the frozen `env` object, so it cannot be poked at
 * directly — and the case that matters is precisely the one the deployment uses.
 */
async function withApiBase(apiBaseUrl: string) {
  vi.resetModules();
  vi.doMock("@/shared/config", () => ({
    env: { apiBaseUrl, siteUrl: "https://vzlettalantov.by" },
  }));
  return (await import("./media")).resolveMediaUrl;
}

afterEach(() => {
  vi.doUnmock("@/shared/config");
  vi.resetModules();
});

describe("resolveMediaUrl", () => {
  it("resolves a stored path against the serving origin when the API base is relative", async () => {
    // How this is deployed: VITE_API_BASE_URL is empty, so `env.apiBaseUrl` is
    // "/api/v1". `new URL("/api/v1")` throws — which took down the whole diploma
    // editor the moment a font came back as a `/media/…` path rather than a
    // bucket URL.
    const resolve = await withApiBase("/api/v1");

    expect(resolve("/media/fonts/montserrat.ttf")).toBe(
      `${window.location.origin}/media/fonts/montserrat.ttf`,
    );
  });

  it("uses the configured origin when the API base is absolute", async () => {
    const resolve = await withApiBase("http://localhost:8000/api/v1");

    expect(resolve("/media/fonts/montserrat.ttf")).toBe(
      "http://localhost:8000/media/fonts/montserrat.ttf",
    );
  });

  it("adds the missing slash on a bare path", async () => {
    const resolve = await withApiBase("/api/v1");

    expect(resolve("media/a.pdf")).toBe(`${window.location.origin}/media/a.pdf`);
  });

  it("passes absolute references through untouched", () => {
    // What a configured bucket returns — and the reason the bug stayed hidden.
    expect(resolveMediaUrl("https://bucket.example/x.pdf")).toBe("https://bucket.example/x.pdf");
    expect(resolveMediaUrl("blob:http://localhost/abc")).toBe("blob:http://localhost/abc");
    expect(resolveMediaUrl("data:application/pdf;base64,AA")).toBe(
      "data:application/pdf;base64,AA",
    );
  });

  it("returns null for nothing to resolve, so callers can render a placeholder", () => {
    expect(resolveMediaUrl(null)).toBeNull();
    expect(resolveMediaUrl(undefined)).toBeNull();
    expect(resolveMediaUrl("   ")).toBeNull();
  });
});
