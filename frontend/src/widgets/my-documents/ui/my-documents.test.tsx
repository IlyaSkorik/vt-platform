import type { UseQueryResult } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  downloadIndividualDiplomas,
  type MyDocument,
  useMyDocuments,
} from "@/features/my-documents";
import type { ApiError } from "@/shared/api";
import { MyDocuments } from "./my-documents";

vi.mock("@/features/my-documents", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/my-documents")>()),
  useMyDocuments: vi.fn(),
  downloadIndividualDiplomas: vi.fn(),
}));

const mockedHook = vi.mocked(useMyDocuments);
const mockedArchive = vi.mocked(downloadIndividualDiplomas);

/** One member's own diploma inside a collective's entry. */
function makeIndividual(recipient: string, id: string): MyDocument {
  return makeDocument({
    id,
    documentType: "INDIVIDUAL_DIPLOMA",
    number: `VT-2026-00000${id}`,
    participantName: "Ансамбль «Созвездие»",
    degree: "Лауреат I степени",
    recipient,
    fileUrl: `/media/diplomas/official/x/${id}.pdf`,
  });
}

type QueryResult = UseQueryResult<MyDocument[], ApiError>;

function mockQuery(overrides: Partial<QueryResult>): void {
  mockedHook.mockReturnValue({
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    refetch: vi.fn(),
    ...overrides,
  } as unknown as QueryResult);
}

function makeDocument(overrides: Partial<MyDocument> = {}): MyDocument {
  return {
    id: "01900000-0000-7000-8000-000000000001",
    documentType: "THANK_YOU",
    submissionId: "01900000-0000-7000-8000-0000000000aa",
    number: null,
    participantName: "Иванов Иван",
    competitionTitle: "Восходящие таланты",
    nomination: "Вокал",
    degree: null,
    recipient: "Петрова Ольга",
    fileUrl: "/media/diplomas/documents/x/thank_you/1.pdf",
    issuedAt: "2026-05-20T12:00:00Z",
    ...overrides,
  };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("MyDocuments", () => {
  it("renders a skeleton while loading", () => {
    mockQuery({ isPending: true });
    const { container } = render(<MyDocuments />);
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("invites patience rather than reporting a failure when empty", () => {
    mockQuery({ data: [] });
    render(<MyDocuments />);
    expect(screen.getByText("Документов пока нет")).toBeInTheDocument();
    // Nothing for the participant to do — documents arrive on their own.
    expect(screen.getByText(/Ничего делать не нужно/)).toBeInTheDocument();
  });

  it("lists a thank-you letter with a download", () => {
    mockQuery({ data: [makeDocument()] });
    render(<MyDocuments />);
    expect(screen.getByText("Благодарность")).toBeInTheDocument();
    expect(screen.getByText("Восходящие таланты · Вокал")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Скачать: Благодарность.*PDF, откроется в новой вкладке/ }),
    ).toBeInTheDocument();
  });

  it("shows a number and a degree for a diploma but not for a letter", () => {
    mockQuery({
      data: [
        makeDocument({
          id: "d1",
          documentType: "DIPLOMA",
          number: "VT-2026-000001",
          degree: "Лауреат I степени",
        }),
        makeDocument({ id: "t1" }),
      ],
    });
    render(<MyDocuments />);
    expect(screen.getByText("VT-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("Лауреат I степени")).toBeInTheDocument();
    expect(screen.getByText("Диплом")).toBeInTheDocument();
    expect(screen.getByText("Благодарность")).toBeInTheDocument();
  });

  it("hides a degree that the diploma does not carry yet", () => {
    mockQuery({ data: [makeDocument({ documentType: "DIPLOMA", number: "VT-2026-000001" })] });
    render(<MyDocuments />);
    expect(screen.getByText("VT-2026-000001")).toBeInTheDocument();
    expect(screen.queryByText(/Лауреат/)).not.toBeInTheDocument();
  });

  it("tells two letters on one entry apart by recipient", () => {
    mockQuery({
      data: [
        makeDocument({ id: "t1", recipient: "Петрова Ольга" }),
        makeDocument({ id: "t2", recipient: "Сидоров Иван" }),
      ],
    });
    render(<MyDocuments />);
    expect(screen.getByText("Петрова Ольга")).toBeInTheDocument();
    expect(screen.getByText("Сидоров Иван")).toBeInTheDocument();
    // Each download names its recipient, so the choice is never a coin toss.
    expect(screen.getByRole("link", { name: /Благодарность, Петрова Ольга/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Благодарность, Сидоров Иван/ })).toBeInTheDocument();
  });

  it("shows no recipient line for a diploma", () => {
    mockQuery({ data: [makeDocument({ documentType: "DIPLOMA", recipient: "" })] });
    render(<MyDocuments />);
    expect(screen.queryByText("Петрова Ольга")).not.toBeInTheDocument();
  });

  it("offers a retry on failure", () => {
    mockQuery({ isError: true, error: { status: 500 } as ApiError });
    render(<MyDocuments />);
    expect(screen.getByRole("button", { name: /повторить/i })).toBeInTheDocument();
  });
});

describe("MyDocuments — an ensemble's individual diplomas", () => {
  it("collapses them into one row with one archive", () => {
    mockQuery({
      data: [
        makeIndividual("Иванова Мария", "1"),
        makeIndividual("Петров Пётр", "2"),
        makeIndividual("Сидорова Анна", "3"),
      ],
    });

    render(<MyDocuments />);

    // One row, not three, and the count is what says why.
    expect(screen.getByText("Индивидуальный диплом")).toBeInTheDocument();
    expect(screen.getByText("3 шт.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Скачать архив/ })).toHaveLength(1);
    expect(screen.queryByText("Иванова Мария")).not.toBeInTheDocument();
  });

  it("downloads the entry's archive", async () => {
    const user = userEvent.setup();
    mockQuery({ data: [makeIndividual("Иванова Мария", "1"), makeIndividual("Петров Пётр", "2")] });

    render(<MyDocuments />);
    await user.click(screen.getByRole("button", { name: /Скачать архив/ }));

    await waitFor(() => expect(mockedArchive).toHaveBeenCalledTimes(1));
    // Scoped to the entry, which is what the server bundles by.
    expect(mockedArchive).toHaveBeenCalledWith("01900000-0000-7000-8000-0000000000aa");
  });

  it("still reaches one member's own sheet", async () => {
    const user = userEvent.setup();
    mockQuery({ data: [makeIndividual("Иванова Мария", "1"), makeIndividual("Петров Пётр", "2")] });

    render(<MyDocuments />);
    await user.click(screen.getByRole("button", { name: /Показать по одному/ }));

    // A parent came for exactly one diploma and should not unpack a ZIP for it.
    expect(screen.getByText("Иванова Мария")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Скачать диплом: Петров Пётр/ })).toBeInTheDocument();
  });
});
