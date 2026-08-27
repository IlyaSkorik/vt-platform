import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SubmissionResource } from "@/shared/api/generated/model-applications";

import { useSetParticipantMemberCount } from "../api/hooks";
import { CollectiveHeadcount, headcountMissing } from "./collective-headcount";

vi.mock("../api/hooks", () => ({ useSetParticipantMemberCount: vi.fn() }));

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
    memberCount: 1,
    members: [],
    ...overrides,
  };
}

beforeEach(() => {
  save.mockReset();
  vi.mocked(useSetParticipantMemberCount).mockReturnValue({
    mutate: save,
    isPending: false,
  } as unknown as ReturnType<typeof useSetParticipantMemberCount>);
});

function renderFor(participant: Participant, bandLabel?: string) {
  return render(
    <CollectiveHeadcount
      submissionId={SUBMISSION}
      participant={participant}
      {...(bandLabel ? { bandLabel } : {})}
    />,
  );
}

describe("headcountMissing", () => {
  it("treats the domain's floor of one as nobody having said yet", () => {
    // One person is not a collective, so the number the entry arrives with cannot be
    // an answer — it is the absence of one.
    expect(headcountMissing(aCollective())).toBe(true);
    expect(headcountMissing(aCollective({ memberCount: 12 }))).toBe(false);
  });
});

describe("CollectiveHeadcount", () => {
  it("starts empty and says the number is required", () => {
    renderFor(aCollective());

    // Nothing pre-filled: a seeded default is accepted without reading, which is the
    // whole reason the field moved out of the picker.
    expect(screen.getByLabelText(/Сколько человек выступает/)).toHaveValue(null);
    expect(screen.getByText(/Укажите численность/)).toBeInTheDocument();
  });

  it("shows the band the festival requires", () => {
    renderFor(aCollective(), "6–12");

    expect(screen.getByText(/6–12/)).toBeInTheDocument();
  });

  it("opens filled in when the headcount is already stated", () => {
    renderFor(aCollective({ memberCount: 12 }));

    expect(screen.getByLabelText(/Сколько человек выступает/)).toHaveValue(12);
    expect(screen.queryByText(/Укажите численность/)).not.toBeInTheDocument();
  });

  it("saves the typed headcount once, after the typing settles", async () => {
    const user = userEvent.setup();
    renderFor(aCollective());

    await user.type(screen.getByLabelText(/Сколько человек выступает/), "12");

    // Debounced: "12" passes through "1", and saving that would put a wrong number on
    // the entry.
    await waitFor(() => expect(save).toHaveBeenCalledTimes(1), { timeout: 3_000 });
    expect(save.mock.calls[0]?.[0]).toEqual({ participantId: PARTICIPANT, memberCount: 12 });
  });

  it("does not save a number the backend would refuse", async () => {
    const user = userEvent.setup();
    renderFor(aCollective());

    await user.type(screen.getByLabelText(/Сколько человек выступает/), "0");

    expect(await screen.findByText(/Укажите целое число/)).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 1_000));
    expect(save).not.toHaveBeenCalled();
  });
});
