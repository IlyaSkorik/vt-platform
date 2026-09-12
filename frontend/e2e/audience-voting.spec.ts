import { expect, test } from "@playwright/test";

/**
 * The audience's journey: scan a code, read the list, tap a name, be thanked.
 *
 * Runs against stubbed API routes rather than a seeded backend, because what this
 * spec is about is the *screen in the hall* — a phone held at arm's length in the
 * dark — and not the correctness of the count, which the backend suite covers in
 * detail. The one server behaviour it does assert is the one the page is built
 * around: a vote answers with the whole page state, so the screen is exact the
 * instant somebody taps.
 */

const SLUG = "AbX82Kqm9p";

type Nominee = {
  id: string;
  position: number;
  title: string;
  subtitle: string;
  city: string;
  photo: null;
  number: number;
  votes: number | null;
  chosen: boolean;
};

function nominee(id: string, position: number, title: string, chosen = false): Nominee {
  return {
    id,
    position,
    number: position,
    title,
    subtitle: "«Калинка»",
    city: "Минск",
    photo: null,
    votes: null,
    chosen,
  };
}

function ballot(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      title: "Приз зрительских симпатий",
      description: "Выберите номер, который понравился больше всего",
      slug: SLUG,
      status: "OPEN",
      open: true,
      votesPerVoter: 1,
      votesLeft: 1,
      revealTotals: false,
      nominees: [nominee("n-1", 1, "Ансамбль «Ритм»"), nominee("n-2", 2, "Хор «Родник»")],
      totalVotes: null,
      closesAt: null,
      closedReason: null,
      ...overrides,
    },
    meta: { requestId: "req-ballot" },
  };
}

test.describe("the audience vote", () => {
  test("somebody in the hall reads the list and votes with one tap", async ({ page }) => {
    let voted = false;

    await page.route(`**/api/v1/public/ballots/${SLUG}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          voted
            ? ballot({
                votesLeft: 0,
                nominees: [
                  nominee("n-1", 1, "Ансамбль «Ритм»", true),
                  nominee("n-2", 2, "Хор «Родник»"),
                ],
              })
            : ballot(),
        ),
      });
    });

    await page.route(`**/api/v1/public/ballots/${SLUG}/votes`, async (route) => {
      voted = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            ballot: ballot({
              votesLeft: 0,
              nominees: [
                nominee("n-1", 1, "Ансамбль «Ритм»", true),
                nominee("n-2", 2, "Хор «Родник»"),
              ],
            }).data,
            accepted: ["n-1"],
          },
          meta: { requestId: "req-vote" },
        }),
      });
    });

    await page.goto(`/vote/${SLUG}`);

    await expect(page.getByRole("heading", { name: "Приз зрительских симпатий" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Ансамбль/ })).toBeVisible();

    await page.getByRole("button", { name: /Ансамбль/ }).click();

    // The vote's own answer carries the new page state, so the thank-you appears
    // without waiting for a poll.
    await expect(page.getByText("Спасибо! Ваш голос учтён.")).toBeVisible();
  });

  test("a closed ballot says so instead of offering a dead button", async ({ page }) => {
    await page.route(`**/api/v1/public/ballots/${SLUG}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          ballot({ open: false, status: "CLOSED", closedReason: "Голосование завершено." }),
        ),
      });
    });

    await page.goto(`/vote/${SLUG}`);

    await expect(page.getByText("Голосование завершено.")).toBeVisible();
  });

  test("a dead link says so rather than showing an empty page", async ({ page }) => {
    await page.route(`**/api/v1/public/ballots/${SLUG}`, async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/problem+json",
        body: JSON.stringify({ detail: "Голосование не найдено." }),
      });
    });

    await page.goto(`/vote/${SLUG}`);

    await expect(page.getByText("Голосование не найдено")).toBeVisible();
  });

  test("the board beside the stage ranks by votes", async ({ page }) => {
    await page.route(`**/api/v1/public/ballots/${SLUG}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          ballot({
            revealTotals: true,
            totalVotes: 12,
            nominees: [
              { ...nominee("n-1", 1, "Ансамбль «Ритм»"), votes: 3 },
              { ...nominee("n-2", 2, "Хор «Родник»"), votes: 9 },
            ],
          }),
        ),
      });
    });

    await page.goto(`/vote/${SLUG}/board`);

    await expect(page.getByText("Всего голосов: 12")).toBeVisible();
    const rows = page.getByRole("listitem");
    await expect(rows.first()).toContainText("Хор «Родник»");
  });
});
