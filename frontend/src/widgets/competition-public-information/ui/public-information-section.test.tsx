import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  buildPublicationChecklist,
  defaultCompetitionSettings,
  defaultContactsConfig,
  defaultLandingConfig,
  SYSTEM_BLOCK_IDS,
} from "@/features/competitions";
import type {
  _LandingBlock,
  CompetitionDetail,
  UpdateLandingConfig,
} from "@/shared/api/generated/model-competitions";
import { PublicInformationSection } from "./public-information-section";

const mutateAsync = vi.fn(
  async (_variables: { competitionId: string; payload: UpdateLandingConfig }) => ({}),
);

/** The configuration the last save actually carried to the server. */
function lastSaved(): UpdateLandingConfig {
  const call = mutateAsync.mock.calls.at(-1);
  if (call === undefined) throw new Error("Nothing was saved.");
  return call[0].payload;
}

function savedBlock(type: string): _LandingBlock {
  const block = lastSaved().blocks.find((item) => item.type === type);
  if (block === undefined) throw new Error(`No ${type} block was saved.`);
  return block as _LandingBlock;
}

vi.mock("@/features/competitions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/competitions")>();
  return {
    ...actual,
    useUpdateLandingConfigurationMutation: () => ({ mutateAsync }),
    useUploadLandingImageMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

const JURY_CARD_ID = "01900000-0000-7000-8000-0000000000aa";

/** The default landing with one jury card, so the JURY block has a name to edit. */
function landingWithJury(name: string): { blocks: _LandingBlock[] } {
  const config = defaultLandingConfig();
  return {
    blocks: config.blocks.map((block) =>
      block.id === SYSTEM_BLOCK_IDS.JURY
        ? {
            ...block,
            enabled: true,
            cards: [
              {
                id: JURY_CARD_ID,
                name,
                photo: null,
                position: null,
                description: null,
                sortOrder: 0,
              },
            ],
          }
        : block,
    ),
  };
}

function competition(overrides: Partial<CompetitionDetail> = {}): CompetitionDetail {
  return {
    id: "01900000-0000-7000-8000-000000000001",
    title: "Spring Festival",
    season: "2025/2026",
    status: "PUBLISHED",
    organizerId: "01900000-0000-7000-8000-0000000000ff",
    description: "A showcase",
    branding: { logo: null, banner: null, poster: null },
    venue: { name: "Hall", address: "Street 1" },
    registrationPeriod: { start: "2026-03-01", end: "2026-04-01" },
    competitionPeriod: { start: "2026-05-10", end: "2026-05-12" },
    settings: defaultCompetitionSettings(),
    contactsConfig: defaultContactsConfig(),
    landingConfig: landingWithJury("Анна Петрова"),
    deadlines: {
      application: null,
      payment: null,
      musicUpload: null,
      documentUpload: null,
      correction: null,
    },
    participationFormats: [],
    categories: [],
    disciplines: [],
    ageCategories: [],
    participantGroups: [],
    admissionRules: [],
    pricingRules: [],
    regulations: [],
    currentRegulationId: null,
    documents: [],
    additionalServices: [],
    contacts: [],
    informationBlocks: [],
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    version: 1,
    ...overrides,
  } as CompetitionDetail;
}

function renderSection(detail: CompetitionDetail = competition()): {
  rerender: (next: CompetitionDetail) => void;
  unmount: () => void;
} {
  const element = (next: CompetitionDetail): React.JSX.Element => (
    <PublicInformationSection
      competition={next}
      checklist={buildPublicationChecklist(next)}
      onAutosaveStateChange={() => {}}
      onNavigateSection={() => {}}
    />
  );
  const view = render(element(detail));
  return {
    rerender: (next) => view.rerender(element(next)),
    unmount: view.unmount,
  };
}

/** The «Показывать» switch of the first block (HERO). */
function firstBlockToggle(): HTMLElement {
  const [toggle] = screen.getAllByRole("switch", { name: /Показывать/ });
  if (toggle === undefined) throw new Error("No block toggle rendered.");
  return toggle;
}

/** Open a block's editor — collapsed blocks render no fields. */
async function expand(user: ReturnType<typeof userEvent.setup>, title: string): Promise<void> {
  await user.click(screen.getByRole("button", { name: title }));
}

describe("PublicInformationSection", () => {
  beforeEach(() => {
    mutateAsync.mockClear();
  });

  it("keeps what is being typed when a save echoes the festival back", async () => {
    // The bug this covers: every save (and every edit in another section) puts a fresh
    // CompetitionDetail in the query cache, and the editor adopted it. The payload is
    // trimmed on the way out, so the echo of a name still being typed arrived a space
    // short — the field lost the separator the organizer had just entered and the rest
    // of the name ran into the first one.
    const user = userEvent.setup();
    const { rerender } = renderSection();
    await expand(user, "Жюри");

    const name = screen.getByLabelText("Имя");
    await user.clear(name);
    await user.type(name, "Мария ");
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());

    rerender(
      competition({
        version: 2,
        updatedAt: "2026-01-02T00:00:00Z",
        landingConfig: landingWithJury("Мария"),
      }),
    );
    await user.type(name, "Ивановна");

    expect(name).toHaveValue("Мария Ивановна");
  });

  it("leaves a cleared field cleared even though the save fills in a placeholder", async () => {
    // A blank jury name fails domain validation, so the payload carries «Без имени».
    // Adopting that answer back into the form overwrote the name the organizer had
    // already started typing in its place.
    const user = userEvent.setup();
    const { rerender } = renderSection();
    await expand(user, "Жюри");

    const name = screen.getByLabelText("Имя");
    await user.clear(name);

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(savedBlock("JURY").cards?.[0]?.name).toBe("Без имени");

    rerender(
      competition({
        version: 2,
        updatedAt: "2026-01-02T00:00:00Z",
        landingConfig: landingWithJury("Без имени"),
      }),
    );

    expect(name).toHaveValue("");
  });

  it("saves a block toggle on the click rather than after a debounce", async () => {
    const user = userEvent.setup();
    renderSection();

    await user.click(firstBlockToggle());

    expect(mutateAsync).toHaveBeenCalledTimes(1);
    expect(savedBlock("HERO").enabled).toBe(false);
  });

  it("flushes text still waiting out its debounce when the section closes", async () => {
    // Switching section unmounts the editor. Dropping the pending save with the timer
    // is how a typed name reads as saved on screen and reappears unchanged later.
    const user = userEvent.setup();
    const { unmount } = renderSection();
    await expand(user, "Жюри");

    await user.clear(screen.getByLabelText("Должность"));
    await user.type(screen.getByLabelText("Должность"), "Председатель");
    mutateAsync.mockClear();

    unmount();

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(savedBlock("JURY").cards?.[0]?.position).toBe("Председатель");
  });

  it("leaves an archived festival's landing alone", async () => {
    const user = userEvent.setup();
    renderSection(competition({ status: "COMPLETED" }));

    const toggle = firstBlockToggle();
    expect(toggle).toBeDisabled();
    await user.click(toggle).catch(() => undefined);
    expect(mutateAsync).not.toHaveBeenCalled();
  });
});
