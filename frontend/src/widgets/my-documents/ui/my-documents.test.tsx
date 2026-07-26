import type { UseQueryResult } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type MyDocument, useMyDocuments } from "@/features/my-documents";
import type { ApiError } from "@/shared/api";
import { MyDocuments } from "./my-documents";

vi.mock("@/features/my-documents", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/my-documents")>()),
  useMyDocuments: vi.fn(),
}));

const mockedHook = vi.mocked(useMyDocuments);

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
    number: null,
    participantName: "Иванов Иван",
    competitionTitle: "Восходящие таланты",
    nomination: "Вокал",
    degree: null,
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

  it("offers a retry on failure", () => {
    mockQuery({ isError: true, error: { status: 500 } as ApiError });
    render(<MyDocuments />);
    expect(screen.getByRole("button", { name: /повторить/i })).toBeInTheDocument();
  });
});
