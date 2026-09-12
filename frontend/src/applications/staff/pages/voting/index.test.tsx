import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Ballot, BallotSummary, ImportPreview } from "@/features/voting-builder";
import {
  useAddNominee,
  useBallot,
  useBallots,
  useCloseBallot,
  useCreateBallot,
  useDeleteBallot,
  useImportNominees,
  useOpenBallot,
  useRemoveNominee,
  useUpdateBallot,
} from "@/features/voting-builder";

import { StaffVotingPage } from "./index";

vi.mock("@/features/voting-builder", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/voting-builder")>()),
  useBallots: vi.fn(),
  useBallot: vi.fn(),
  useCreateBallot: vi.fn(),
  useUpdateBallot: vi.fn(),
  useOpenBallot: vi.fn(),
  useCloseBallot: vi.fn(),
  useAddNominee: vi.fn(),
  useRemoveNominee: vi.fn(),
  useDeleteBallot: vi.fn(),
  useImportNominees: vi.fn(),
}));

vi.mock("@/shared/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/ui")>();
  return { ...actual, toast: { ...actual.toast, error: vi.fn(), success: vi.fn() } };
});

// jsdom implements neither, and the Radix select the reveal picker is built on calls
// both while opening (the same stubs the Select suite installs).
Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};

const create = vi.fn();
const open = vi.fn();
const importNominees = vi.fn();
let preview: ImportPreview | null = null;

function summary(overrides: Partial<BallotSummary> = {}): BallotSummary {
  return {
    id: "b-1",
    title: "Приз зрительских симпатий",
    slug: "AbX82Kqm9p",
    status: "DRAFT",
    competitionId: null,
    standalone: true,
    nominees: 2,
    totalVotes: 0,
    opensAt: null,
    closesAt: null,
    createdAt: "2026-09-12T10:00:00Z",
    ...overrides,
  };
}

function detail(overrides: Partial<Ballot> = {}): Ballot {
  return {
    ...summary(),
    description: "",
    votesPerVoter: 1,
    cooldownHours: 0,
    reveal: "AFTER_CLOSE",
    voters: 0,
    updatedAt: null,
    nominees: [
      {
        id: "n-1",
        position: 1,
        title: "Ансамбль «Ритм»",
        subtitle: "«Калинка»",
        city: "",
        photo: null,
        number: 1,
        withdrawn: false,
        votes: 0,
        submissionId: null,
        programItemId: null,
      },
      {
        id: "n-2",
        position: 2,
        title: "Хор «Родник»",
        subtitle: "",
        city: "",
        photo: null,
        number: 2,
        withdrawn: false,
        votes: 0,
        submissionId: null,
        programItemId: null,
      },
    ],
    ...overrides,
  } as Ballot;
}

function show(ballot: Ballot, rows: BallotSummary[] = [summary()]) {
  vi.mocked(useBallots).mockReturnValue({ data: rows, isLoading: false } as ReturnType<
    typeof useBallots
  >);
  vi.mocked(useBallot).mockReturnValue({ data: ballot, isLoading: false } as ReturnType<
    typeof useBallot
  >);

  render(
    <MemoryRouter>
      <StaffVotingPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  create.mockReset();
  open.mockReset();
  importNominees.mockReset();
  preview = null;

  const idle = { mutate: vi.fn(), isPending: false };
  vi.mocked(useCreateBallot).mockReturnValue({ mutate: create, isPending: false } as never);
  vi.mocked(useOpenBallot).mockReturnValue({ mutate: open, isPending: false } as never);
  vi.mocked(useUpdateBallot).mockReturnValue(idle as never);
  vi.mocked(useCloseBallot).mockReturnValue(idle as never);
  vi.mocked(useAddNominee).mockReturnValue(idle as never);
  vi.mocked(useRemoveNominee).mockReturnValue(idle as never);
  vi.mocked(useDeleteBallot).mockReturnValue(idle as never);
  vi.mocked(useImportNominees).mockReturnValue({
    mutate: importNominees.mockImplementation((_input, options) => {
      if (preview) options?.onSuccess?.(preview);
    }),
    isPending: false,
  } as never);
});

describe("creating a ballot", () => {
  it("needs nothing but a name — no festival", async () => {
    show(detail());

    await userEvent.type(screen.getByLabelText(/Название/), "Голосование зала");
    await userEvent.click(screen.getByRole("button", { name: /Создать/ }));

    expect(create).toHaveBeenCalledWith({ title: "Голосование зала" }, expect.anything());
  });

  it("says out loud that a festival is not required", () => {
    show(detail());

    expect(screen.getByText(/Фестиваль на платформе для этого не нужен/)).toBeInTheDocument();
  });
});

describe("the editor", () => {
  it("shows the link the hall will be given", () => {
    show(detail());

    expect(screen.getByText(/\/vote\/AbX82Kqm9p/)).toBeInTheDocument();
  });

  it("opens a ballot that has enough nominees", async () => {
    show(detail());

    await userEvent.click(screen.getByRole("button", { name: "Открыть голосование" }));

    expect(open).toHaveBeenCalled();
  });

  it("refuses to open one with a single nominee, and says why", () => {
    const [only] = detail().nominees;
    show(detail({ nominees: only ? [only] : [] }));

    expect(screen.getByText("Добавьте хотя бы двух номинантов")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Открыть голосование" })).toBeDisabled();
  });

  it("tells the organizer what this protection actually stops", () => {
    show(detail());

    expect(screen.getByText(/не человека с VPN в режиме инкогнито/)).toBeInTheDocument();
  });

  it("warns that a live count helps whoever wants to rig it", () => {
    show(detail({ reveal: "ALWAYS" }));

    expect(screen.getByText(/подсказывает накрутчику/)).toBeInTheDocument();
  });

  it("offers a close button once the vote is running", () => {
    show(detail({ status: "OPEN" }));

    expect(screen.getByRole("button", { name: "Завершить" })).toBeInTheDocument();
  });

  it("shows the turnout beside the vote count", () => {
    show(detail({ voters: 41 }));

    expect(screen.getByText(/проголосовало: 41/)).toBeInTheDocument();
  });
});

describe("importing a list", () => {
  it("previews before it writes anything", async () => {
    preview = { added: [], errors: [], missingColumns: [], dryRun: true };
    show(detail());

    const file = new File(["x"], "nominees.xlsx");
    await userEvent.upload(screen.getByTestId("import-input"), file);

    expect(importNominees).toHaveBeenCalledWith({ file, dryRun: true }, expect.anything());
  });

  it("reports a bad row by the number Excel shows", async () => {
    preview = {
      added: [],
      errors: [{ row: 14, message: "Не заполнено: «Участник»." }],
      missingColumns: [],
      dryRun: true,
    };
    show(detail());

    await userEvent.upload(screen.getByTestId("import-input"), new File(["x"], "nominees.xlsx"));

    expect(screen.getByText(/Строка 14/)).toBeInTheDocument();
  });

  it("names the columns the file did not have", async () => {
    preview = { added: [], errors: [], missingColumns: ["Город"], dryRun: true };
    show(detail());

    await userEvent.upload(screen.getByTestId("import-input"), new File(["x"], "nominees.xlsx"));

    expect(screen.getByText(/Колонки не найдены и пропущены: Город/)).toBeInTheDocument();
  });
});
