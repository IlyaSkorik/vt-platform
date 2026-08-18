import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SubmissionResource } from "@/shared/api/generated/model-applications";

import { useSetParticipantMembers } from "../api/hooks";
import { CollectiveMembers, isCollectiveEntry } from "./collective-members";

vi.mock("../api/hooks", () => ({ useSetParticipantMembers: vi.fn() }));

const SUBMISSION = "01900000-0000-7000-8000-0000000000aa";
const PARTICIPANT = "01900000-0000-7000-8000-0000000000bb";

type Participant = SubmissionResource["participants"][number];

const save = vi.fn();

function aCollective(overrides: Partial<Participant> = {}): Participant {
  return {
    id: PARTICIPANT,
    registryParticipantId: null,
    displayName: "Ансамбль «Созвездие»",
    firstName: null,
    lastName: null,
    middleName: null,
    birthDate: null,
    gender: null,
    memberCount: 3,
    members: [],
    ...overrides,
  };
}

beforeEach(() => {
  save.mockReset();
  vi.mocked(useSetParticipantMembers).mockReturnValue({
    mutate: save,
    isPending: false,
  } as unknown as ReturnType<typeof useSetParticipantMembers>);
});

function renderFor(participant: Participant) {
  return render(<CollectiveMembers submissionId={SUBMISSION} participant={participant} />);
}

describe("isCollectiveEntry", () => {
  it("recognises a collective by its headcount or its missing person data", () => {
    expect(isCollectiveEntry(aCollective())).toBe(true);
    expect(isCollectiveEntry(aCollective({ memberCount: 1 }))).toBe(true);
  });

  it("leaves a solo participant alone", () => {
    // A soloist is already named on their own diploma; an "individual" one would be a
    // second copy of the same sheet.
    expect(isCollectiveEntry(aCollective({ memberCount: 1, birthDate: "2014-05-01" }))).toBe(false);
  });
});

describe("CollectiveMembers", () => {
  it("hides the roster until individual diplomas are asked for", () => {
    renderFor(aCollective());

    // Optional by design: nothing to fill in unless the applicant wants them.
    expect(screen.queryByLabelText(/ФИО участников коллектива/)).not.toBeInTheDocument();
  });

  it("opens the roster already filled in when names are saved", () => {
    renderFor(aCollective({ members: ["Иванова Мария", "Петров Пётр"] }));

    expect(screen.getByLabelText(/ФИО участников коллектива/)).toHaveValue(
      "Иванова Мария\nПетров Пётр",
    );
  });

  it("saves one ФИО per line, dropping blanks and extra spaces", async () => {
    const user = userEvent.setup();
    renderFor(aCollective());

    await user.click(screen.getByRole("switch"));
    await user.type(
      screen.getByLabelText(/ФИО участников коллектива/),
      "  Иванова   Мария  {Enter}{Enter}Петров Пётр{Enter}",
    );
    await user.click(screen.getByRole("button", { name: "Сохранить состав" }));

    await waitFor(() => expect(save).toHaveBeenCalledTimes(1));
    expect(save.mock.calls[0]?.[0]).toEqual({
      participantId: PARTICIPANT,
      members: ["Иванова Мария", "Петров Пётр"],
    });
  });

  it("withdraws the request by clearing the roster", async () => {
    const user = userEvent.setup();
    renderFor(aCollective({ members: ["Иванова Мария"] }));

    await user.click(screen.getByRole("switch"));

    // Turning the switch off is the opt-out, so it saves an empty roster rather than
    // leaving the names behind where the applicant cannot see them.
    await waitFor(() => expect(save).toHaveBeenCalledTimes(1));
    expect(save.mock.calls[0]?.[0]).toEqual({ participantId: PARTICIPANT, members: [] });
  });

  it("says when fewer people are named than the headcount", async () => {
    const user = userEvent.setup();
    renderFor(aCollective({ memberCount: 12 }));

    await user.click(screen.getByRole("switch"));
    await user.type(screen.getByLabelText(/ФИО участников коллектива/), "Иванова Мария");

    expect(screen.getByText(/Указано 1 из 12 участников/)).toBeInTheDocument();
  });

  it("does not offer to save an unchanged roster", () => {
    renderFor(aCollective({ members: ["Иванова Мария"] }));

    expect(screen.getByRole("button", { name: "Сохранить состав" })).toBeDisabled();
  });
});
