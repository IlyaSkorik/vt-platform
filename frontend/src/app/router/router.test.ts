import type { RouteObject } from "react-router";
import { describe, expect, it } from "vitest";

import { ROUTES } from "@/shared/config";

import { routes } from "./router";

/**
 * Every address in `ROUTES` must actually be reachable.
 *
 * This suite exists because of a real failure: `/vote/:slug` was added to
 * `ROUTES`, given a page and a test, and then never wired into the route tree —
 * so the type-checker was happy, every unit test passed, and the link an
 * organizer handed to a hall rendered the not-found page. A constant naming an
 * address the router has never heard of is a broken promise, and nothing but
 * walking the tree catches it.
 */

/**
 * Every concrete path the route tree can match, as full addresses.
 *
 * A layout route has no `path` of its own and only contributes its children; an
 * `index` route matches its parent's address, which is how `/` is reachable.
 */
function reachablePaths(tree: RouteObject[], prefix = ""): string[] {
  return tree.flatMap((route) => {
    if (route.index) {
      return [prefix || "/"];
    }
    const here =
      route.path === undefined ? prefix : `${prefix}/${route.path}`.replaceAll("//", "/");
    const children = route.children ? reachablePaths(route.children, here) : [];
    return route.path === undefined ? children : [here, ...children];
  });
}

const REACHABLE = new Set(reachablePaths(routes));

/**
 * Addresses `ROUTES` names that the router deliberately does not serve yet.
 *
 * Every one of these predates this suite. They are listed rather than quietly
 * excluded so the list can only shrink: adding a constant without a route is the
 * exact mistake this file exists to catch, and an implicit exemption would let
 * the next one through.
 *
 * `staffCompetitionsNew` is the odd one out — it *is* served, as the `new` child
 * of the festivals route, which this walker renders as its parent's path.
 */
const NOT_YET_ROUTED = new Set<string>([
  ROUTES.performances,
  ROUTES.judging,
  ROUTES.results,
  ROUTES.finance,
  ROUTES.analytics,
  ROUTES.emailVerified,
  ROUTES.staffCompetitionsNew,
]);

describe("the route tree", () => {
  it("matches the public voting page", () => {
    expect(REACHABLE).toContain(ROUTES.publicBallot);
  });

  it("matches the scoreboard", () => {
    expect(REACHABLE).toContain(ROUTES.publicBallotBoard);
  });

  it("matches the organizer's voting section", () => {
    expect(REACHABLE).toContain(ROUTES.staffVoting);
  });

  it("reaches every address ROUTES advertises", () => {
    const unreachable = Object.values(ROUTES).filter(
      (path) => !REACHABLE.has(path) && !NOT_YET_ROUTED.has(path),
    );

    expect(unreachable).toEqual([]);
  });
});
