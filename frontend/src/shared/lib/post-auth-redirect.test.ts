import { afterEach, describe, expect, it } from "vitest";

import {
  authPathWithNext,
  clearPostAuthRedirect,
  isSafeRedirect,
  readPostAuthRedirect,
  rememberPostAuthRedirect,
} from "./post-auth-redirect";

/**
 * The parked destination that survives registration.
 *
 * Two properties are load-bearing: it only ever holds an in-app path (this feeds a
 * redirect, and an open redirect turns a sign-in page into a phishing page), and it
 * survives the detour out through a verification e-mail — which is the whole reason it
 * is storage rather than a query parameter.
 */
describe("post-auth redirect", () => {
  afterEach(() => {
    clearPostAuthRedirect();
  });

  it("accepts an in-app path and nothing else", () => {
    expect(isSafeRedirect("/jury/invite/abc")).toBe(true);
    expect(isSafeRedirect("https://evil.test")).toBe(false);
    expect(isSafeRedirect("//evil.test")).toBe(false);
    expect(isSafeRedirect("../elsewhere")).toBe(false);
    expect(isSafeRedirect(null)).toBe(false);
  });

  it("remembers where the account was going, across a reload", () => {
    rememberPostAuthRedirect("/jury/invite/abc");

    expect(readPostAuthRedirect()).toBe("/jury/invite/abc");
  });

  it("refuses to park an off-site destination", () => {
    rememberPostAuthRedirect("https://evil.test/steal");

    expect(readPostAuthRedirect()).toBeNull();
  });

  it("builds a sign-in link that carries the destination", () => {
    expect(authPathWithNext("/login", "/jury/invite/abc")).toBe(
      "/login?next=%2Fjury%2Finvite%2Fabc",
    );
  });

  it("builds links without writing anything — that is a separate, deliberate call", () => {
    authPathWithNext("/login", "/jury/invite/abc");

    expect(readPostAuthRedirect()).toBeNull();
  });

  it("leaves the link alone when there is nowhere particular to go", () => {
    expect(authPathWithNext("/register", null)).toBe("/register");
    expect(authPathWithNext("/register", "https://evil.test")).toBe("/register");
  });
});
