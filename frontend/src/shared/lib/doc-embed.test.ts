import { describe, expect, it } from "vitest";
import { isExternalDocLink, isGoogleDocsUrl, toEmbeddableDocUrl } from "./doc-embed";

describe("isExternalDocLink", () => {
  it("recognises absolute http(s) links", () => {
    expect(isExternalDocLink("https://docs.google.com/document/d/abc/edit")).toBe(true);
    expect(isExternalDocLink("http://example.com/x")).toBe(true);
  });

  it("rejects stored media paths and empty input", () => {
    expect(isExternalDocLink("/media/competitions/1/regulations/x.pdf")).toBe(false);
    expect(isExternalDocLink("")).toBe(false);
    expect(isExternalDocLink(null)).toBe(false);
  });
});

describe("isGoogleDocsUrl", () => {
  it("matches Google Docs and Drive hosts", () => {
    expect(isGoogleDocsUrl("https://docs.google.com/document/d/abc/edit")).toBe(true);
    expect(isGoogleDocsUrl("https://drive.google.com/file/d/abc/view")).toBe(true);
  });

  it("rejects other hosts and invalid URLs", () => {
    expect(isGoogleDocsUrl("https://example.com/doc")).toBe(false);
    expect(isGoogleDocsUrl("not a url")).toBe(false);
  });
});

describe("toEmbeddableDocUrl", () => {
  it("rewrites a Docs edit URL to /preview", () => {
    expect(toEmbeddableDocUrl("https://docs.google.com/document/d/abc123/edit?usp=sharing")).toBe(
      "https://docs.google.com/document/d/abc123/preview",
    );
  });

  it("rewrites Sheets and Slides URLs", () => {
    expect(toEmbeddableDocUrl("https://docs.google.com/spreadsheets/d/s1/edit#gid=0")).toBe(
      "https://docs.google.com/spreadsheets/d/s1/preview",
    );
    expect(toEmbeddableDocUrl("https://docs.google.com/presentation/d/p1/edit")).toBe(
      "https://docs.google.com/presentation/d/p1/preview",
    );
  });

  it("rewrites Drive file and open URLs", () => {
    expect(toEmbeddableDocUrl("https://drive.google.com/file/d/f1/view?usp=drive_link")).toBe(
      "https://drive.google.com/file/d/f1/preview",
    );
    expect(toEmbeddableDocUrl("https://drive.google.com/open?id=f2")).toBe(
      "https://drive.google.com/file/d/f2/preview",
    );
  });

  it("leaves already-embeddable and non-Google URLs untouched", () => {
    expect(toEmbeddableDocUrl("https://docs.google.com/document/d/abc/preview")).toBe(
      "https://docs.google.com/document/d/abc/preview",
    );
    expect(toEmbeddableDocUrl("https://docs.google.com/document/d/e/2PACX/pub")).toBe(
      "https://docs.google.com/document/d/e/2PACX/pub",
    );
    expect(toEmbeddableDocUrl("https://example.com/x.pdf")).toBe("https://example.com/x.pdf");
  });

  it("returns null for empty input", () => {
    expect(toEmbeddableDocUrl("")).toBeNull();
    expect(toEmbeddableDocUrl(null)).toBeNull();
  });
});
