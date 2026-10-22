import { expect, type Page, test } from "@playwright/test";

/**
 * The programme is the widest table on the platform, and twice now a single
 * absolutely positioned descendant has escaped its scroll container and dragged the
 * whole document sideways with it — most recently a 1px `sr-only` column header,
 * which nothing in a unit test can see. So the invariant is asserted where layout
 * actually happens: the table scrolls inside its own container, and the *page* never
 * scrolls sideways.
 *
 * Runs at both project viewports, so the phone is covered too.
 */

const env = <T>(data: T) => ({ data, meta: { requestId: "req-scroll" } });

const COLUMN_LABELS: [string, string][] = [
  ["POSITION", "№"],
  ["TIME", "Время"],
  ["PARTICIPANT", "Участник"],
  ["TITLE", "Номер"],
  ["DURATION", "Хронометраж"],
  ["NOMINATION", "Номинация"],
  ["DISCIPLINE", "Дисциплина"],
  ["PARTICIPANT_GROUP", "Состав участников"],
  ["PARTICIPANT_COUNT", "Человек"],
  ["AGE_CATEGORY", "Возрастная категория"],
  ["PARTICIPATION_FORMAT", "Формат участия"],
  ["TEACHERS", "Педагоги"],
  ["ORGANIZATION", "Организация"],
  ["CONTACTS", "Контакты"],
  ["COMMENT", "Комментарий"],
];

const columns = COLUMN_LABELS.map(([key, label]) => ({ key, label, custom: false }));

/** Long, realistic cell text — the point of the test is a table too wide to fit. */
const performance = (index: number) => ({
  id: `item-${index}`,
  kind: "PERFORMANCE" as const,
  title: `Сюита для фортепиано в четыре руки, часть ${index}`,
  number: index,
  durationSeconds: 200,
  schedule: {
    position: index,
    offsetSeconds: (index - 1) * 230,
    slotSeconds: 230,
    startsAt: `2026-09-01T10:${String(index * 4).padStart(2, "0")}:00Z`,
    endsAt: `2026-09-01T10:${String(index * 4 + 3).padStart(2, "0")}:00Z`,
  },
  submissionId: `sub-${index}`,
  participants: [`Александрова Анастасия ${index}`],
  participantCount: 1,
  teachers: ["Преподаватель Иванова Мария Сергеевна"],
  contacts: ["+375291112233"],
  nomination: "Инструментальное исполнительство",
  discipline: "фортепиано",
  ageCategory: "10-12 лет",
  participantGroup: "Соло",
  participationFormat: "Очное участие",
  organization: "Детская школа искусств номер 4 города Москвы",
  comment: "Выход из-за левой кулисы, фонограмма со второго куплета",
  missingPerformance: false,
  customValues: {},
  progress: "PENDING" as const,
});

const items = [1, 2, 3, 4, 5, 6].map(performance);

/**
 * Ask the browser the only two questions that matter: how the table sits in its own
 * container, and whether the document can be scrolled sideways (which is the bug).
 */
async function measure(page: Page) {
  return page.evaluate(() => {
    const doc = document.documentElement;
    const table = document.querySelector("table");
    const box = table?.parentElement ?? null;
    // `scroll-behavior: smooth` would make this read back 0 before it has moved.
    const previous = doc.style.scrollBehavior;
    doc.style.scrollBehavior = "auto";
    window.scrollTo(1000, 0);
    const scrolledTo = window.scrollX;
    window.scrollTo(0, 0);
    doc.style.scrollBehavior = previous;
    return {
      tableOverflowsItsBox: box ? box.scrollWidth > box.clientWidth + 1 : false,
      documentScrollWidth: doc.scrollWidth,
      viewportWidth: doc.clientWidth,
      scrolledTo,
    };
  });
}

test.describe("the programme table never scrolls the page", () => {
  test("public programme", async ({ page }) => {
    await page.route("**/api/v1/public/programs/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          env({
            name: "Программа первого дня",
            competitionTitle: "Взлёт талантов",
            nomination: "Инструментальное исполнительство",
            startsAt: "2026-09-01T10:00:00Z",
            totalSeconds: 1380,
            endsAt: "2026-09-01T10:23:00Z",
            controlsRunningOrder: false,
            columns,
            rows: items.map((item) => ({
              kind: "PERFORMANCE",
              progress: "PENDING",
              id: null,
              cells: [
                String(item.number),
                "10:00",
                item.participants.join(", "),
                item.title,
                "3:20",
                item.nomination,
                item.discipline,
                item.participantGroup,
                String(item.participantCount),
                item.ageCategory,
                item.participationFormat,
                item.teachers.join(", "),
                item.organization,
                item.contacts.join(", "),
                item.comment,
              ],
            })),
          }),
        ),
      }),
    );

    await page.goto("/program/Sound2345");
    await expect(page.getByRole("table")).toBeVisible();

    const result = await measure(page);
    expect(result.tableOverflowsItsBox).toBe(true);
    expect(result.scrolledTo).toBe(0);
    expect(result.documentScrollWidth).toBeLessThanOrEqual(result.viewportWidth);
  });

  test("programme constructor", async ({ page }) => {
    // Registered first on purpose: Playwright gives priority to the last matching
    // route, so this fallback must not shadow the specific ones below.
    await page.route("**/api/v1/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(env(null)),
      }),
    );
    await page.route("**/api/v1/users/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          env({
            user: {
              id: "user-1",
              email: "organizer@example.com",
              firstName: "Organizer",
              lastName: "User",
              status: "ACTIVE",
              type: "ADULT",
              emailVerified: true,
            },
            staffMembership: { role: "COMPETITION_MANAGER", status: "ACTIVE" },
          }),
        ),
      }),
    );
    await page.route("**/api/v1/auth/token/refresh", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(env({ accessToken: "mock-token", tokenType: "Bearer" })),
      }),
    );
    await page.route("**/api/v1/competitions**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          env([
            { id: "comp-1", title: "Взлёт талантов", season: "2026/2027", status: "PUBLISHED" },
          ]),
        ),
      }),
    );
    await page.route("**/api/v1/competitions/comp-1**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          env({
            id: "comp-1",
            title: "Взлёт талантов",
            season: "2026/2027",
            status: "PUBLISHED",
            nominations: [],
            version: 1,
          }),
        ),
      }),
    );
    await page.route("**/api/v1/staff/programs?**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          env([
            {
              id: "prog-1",
              competitionId: "comp-1",
              nominationId: null,
              name: "Программа первого дня",
              bufferSeconds: 30,
              startsAt: "2026-09-01T10:00:00Z",
              itemCount: items.length,
              performanceCount: items.length,
              totalSeconds: 1380,
              shareCount: 0,
              createdAt: "2026-08-01T10:00:00Z",
              updatedAt: "2026-08-01T10:00:00Z",
            },
          ]),
        ),
      }),
    );
    await page.route("**/api/v1/staff/programs/prog-1/candidates**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(env([])),
      }),
    );
    await page.route("**/api/v1/staff/programs/prog-1", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          env({
            id: "prog-1",
            competitionId: "comp-1",
            nominationId: null,
            name: "Программа первого дня",
            bufferSeconds: 30,
            startsAt: "2026-09-01T10:00:00Z",
            items,
            shares: [],
            availableColumns: columns,
            numbersFrozen: false,
            numbersFrozenAt: null,
            totalSeconds: 1380,
            endsAt: "2026-09-01T10:23:00Z",
            createdAt: "2026-08-01T10:00:00Z",
            updatedAt: "2026-08-01T10:00:00Z",
            version: 1,
          }),
        ),
      }),
    );

    await page.goto("/staff/program");
    // The running order only exists once a programme is open, which is also the state
    // the bug was reported in.
    await page.getByText("Программа первого дня").first().click();
    await expect(page.getByRole("table")).toBeVisible();

    const result = await measure(page);
    // Fifteen columns of long, realistic text — and no sideways scroll anywhere. That
    // is the point: the organizer drags a row to a number they can still see.
    expect(result.tableOverflowsItsBox).toBe(false);
    expect(result.scrolledTo).toBe(0);
    expect(result.documentScrollWidth).toBeLessThanOrEqual(result.viewportWidth);
  });
});
