import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  buildPublicationChecklist,
  defaultCompetitionSettings,
  defaultContactsConfig,
} from "@/features/competitions";
import type {
  CompetitionDetail,
  UpdateCompetitionSettings,
} from "@/shared/api/generated/model-competitions";
import { SettingsSection } from "./settings-section";

const mutateAsync = vi.fn(
  async (_variables: { competitionId: string; payload: UpdateCompetitionSettings }) => ({}),
);

/** The rules the last save actually carried to the server. */
function lastSaved(): UpdateCompetitionSettings {
  const call = mutateAsync.mock.calls.at(-1);
  if (call === undefined) throw new Error("Nothing was saved.");
  return call[0].payload;
}

vi.mock("@/features/competitions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/competitions")>();
  return {
    ...actual,
    useUpdateCompetitionSettingsMutation: () => ({ mutateAsync }),
  };
});

function competition(): CompetitionDetail {
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
    landingConfig: { blocks: [] },
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
  };
}

function renderSection(
  detail: CompetitionDetail = competition(),
  { strict = false }: { strict?: boolean } = {},
): { unmount: () => void } {
  const section = (
    <SettingsSection
      competition={detail}
      checklist={buildPublicationChecklist(detail)}
      onAutosaveStateChange={() => {}}
      onNavigateSection={() => {}}
    />
  );
  return render(strict ? <StrictMode>{section}</StrictMode> : section);
}

describe("SettingsSection", () => {
  beforeEach(() => {
    mutateAsync.mockClear();
  });

  it("sends a flipped switch straight away rather than waiting out a debounce", async () => {
    // The bug this covers: the switch was saved 500 ms later, and switching section in
    // the meantime dropped the pending save with the timer. The organizer turned
    // «Педагог обязателен» off, the screen agreed, and the festival still refused every
    // entry without a teacher — the rule never reached the server. Hence no `waitFor`:
    // the request has to be out by the time the click is over, not merely eventually.
    const user = userEvent.setup();
    renderSection();

    await user.click(screen.getByRole("switch", { name: /Педагог обязателен/ }));

    expect(mutateAsync).toHaveBeenCalledTimes(1);
    expect(lastSaved().requireTeacher).toBe(false);
  });

  it("saves the flipped switch once under StrictMode's double render", async () => {
    // Saving from inside a `setSettings` updater would send the change twice, and the
    // second arrives against a version the first has already moved on from.
    const user = userEvent.setup();
    renderSection(competition(), { strict: true });

    await user.click(screen.getByRole("switch", { name: /Педагог обязателен/ }));

    expect(mutateAsync).toHaveBeenCalledTimes(1);
    expect(lastSaved().requireTeacher).toBe(false);
  });

  it("flushes a rule still waiting out its debounce when the section closes", async () => {
    // The upload ceilings are typed a digit at a time, so they keep the debounce — and
    // with it the window in which the organizer moves to another section. Leaving has to
    // send what is pending, not discard it with the timer.
    const withFormat: CompetitionDetail = {
      ...competition(),
      participationFormats: [
        {
          id: "01900000-0000-7000-8000-00000000000f",
          name: "Очно",
          description: null,
          enabled: true,
          sortOrder: 0,
        },
      ],
    };
    const { unmount } = renderSection(withFormat);

    // Typed as one edit rather than keystroke by keystroke: the field clamps every
    // intermediate value, so "3" then "0" would land on a number nobody typed.
    fireEvent.change(screen.getByLabelText("Максимальный размер (МБ)"), {
      target: { value: "30" },
    });
    expect(mutateAsync).not.toHaveBeenCalled();

    unmount();

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(lastSaved().formatRequirements[0]?.music.maxUploadSizeMb).toBe(30);
  });

  it("keeps every other rule intact when one switch is flipped", async () => {
    const user = userEvent.setup();
    renderSection();

    await user.click(screen.getByRole("switch", { name: /Педагог обязателен/ }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    const saved = lastSaved();
    expect(saved.requireTeacher).toBe(false);
    expect(saved.participantCommentEnabled).toBe(true);
    expect(saved.requireRegulationsAcceptance).toBe(true);
  });

  it("leaves an archived festival's rules alone", async () => {
    const user = userEvent.setup();
    const archived = { ...competition(), status: "COMPLETED" };
    renderSection(archived);

    const teacherSwitch = screen.getByRole("switch", { name: /Педагог обязателен/ });
    expect(teacherSwitch).toBeDisabled();
    await user.click(teacherSwitch).catch(() => undefined);
    expect(mutateAsync).not.toHaveBeenCalled();
  });
});
