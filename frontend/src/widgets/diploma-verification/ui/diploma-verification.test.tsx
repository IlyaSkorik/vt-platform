import type { UseQueryResult } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useVerifyDiploma, type VerifiedDiploma } from "@/features/diploma-verification";
import { makeVerifiedDiploma } from "@/features/diploma-verification/lib/fixtures";
import type { ApiError } from "@/shared/api";
import { DiplomaVerification } from "./diploma-verification";

vi.mock("@/features/diploma-verification", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/diploma-verification")>()),
  useVerifyDiploma: vi.fn(),
}));

const mockedHook = vi.mocked(useVerifyDiploma);

type QueryResult = UseQueryResult<VerifiedDiploma, ApiError>;

/** A fixed answer time, so the check stamp is deterministic. */
const ANSWERED_AT = new Date(2026, 6, 26, 18, 42).getTime();

function mockQuery(overrides: Partial<QueryResult>): void {
  mockedHook.mockReturnValue({
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    dataUpdatedAt: ANSWERED_AT,
    refetch: vi.fn(),
    ...overrides,
  } as unknown as QueryResult);
}

/** No default: a test passing `undefined` means "no token in the URL". */
function renderVerification(token?: string) {
  return render(<DiplomaVerification verificationToken={token} />);
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("DiplomaVerification", () => {
  it("renders a skeleton while consulting the register", () => {
    mockQuery({ isPending: true });
    const { container } = renderVerification("tok-1");
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("confirms the diploma and records its facts on success", () => {
    mockQuery({ data: makeVerifiedDiploma() });
    renderVerification("tok-1");
    expect(screen.getByRole("heading", { name: "Диплом подтверждён" })).toBeInTheDocument();
    expect(
      screen.getByText("Подлинность данного диплома успешно подтверждена."),
    ).toBeInTheDocument();
    expect(screen.getByText("VT-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("Иванов Иван")).toBeInTheDocument();
    expect(screen.getByText("Лауреат I степени")).toBeInTheDocument();
  });

  it("nests the result headings under the page heading", () => {
    mockQuery({ data: makeVerifiedDiploma() });
    renderVerification("tok-1");
    // The page owns the h1; every result card is an h2 beneath it.
    expect(
      screen.getByRole("heading", { level: 2, name: "Диплом подтверждён" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Сведения о документе" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
  });

  it("stamps when the register answered", () => {
    mockQuery({ data: makeVerifiedDiploma() });
    renderVerification("tok-1");
    expect(screen.getByText("26.07.2026 18:42")).toBeInTheDocument();
    expect(
      screen.getByText(/Подлинность документа проверена через официальный реестр/),
    ).toBeInTheDocument();
  });

  it("says results are unpublished when no degree is awarded yet", () => {
    mockQuery({ data: makeVerifiedDiploma({ degree: null }) });
    renderVerification("tok-1");
    expect(screen.getByText("Степень")).toBeInTheDocument();
    expect(screen.getByText("Результаты фестиваля ещё не опубликованы")).toBeInTheDocument();
  });

  it("hides the download until the official PDF exists", () => {
    mockQuery({ data: makeVerifiedDiploma({ officialPdfUrl: null }) });
    renderVerification("tok-1");
    expect(screen.queryByRole("link", { name: /скачать/i })).not.toBeInTheDocument();
  });

  it("links the official PDF once it exists, with a described action", () => {
    mockQuery({ data: makeVerifiedDiploma() });
    renderVerification("tok-1");
    const link = screen.getByRole("link", {
      name: "Скачать официальный диплом в формате PDF (откроется в новой вкладке)",
    });
    // The stored `/media/…` reference is resolved against the API origin.
    expect(link).toHaveAttribute(
      "href",
      expect.stringContaining("/media/diplomas/official/VT-2026-000001.pdf"),
    );
  });

  it("renders the not-found record on a 404, with nothing technical", () => {
    mockQuery({ isError: true, error: { status: 404 } as ApiError });
    const { container } = renderVerification("tok-1");
    expect(screen.getByRole("heading", { name: "Диплом не найден" })).toBeInTheDocument();
    expect(
      screen.getByText("Мы не смогли подтвердить подлинность данного диплома."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Проверьте QR-код или обратитесь к организаторам фестиваля."),
    ).toBeInTheDocument();
    // No status code and no diagnostics anywhere on the page.
    expect(container.textContent).not.toMatch(/404|error/i);
  });

  it("separates an unreachable register from a missing diploma", () => {
    mockQuery({ isError: true, error: { status: 500 } as ApiError });
    const { container } = renderVerification("tok-1");
    expect(screen.getByRole("heading", { name: "Реестр временно недоступен" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /повторить проверку/i })).toBeInTheDocument();
    // A connection failure must never read as a failed authenticity check.
    expect(screen.queryByText("Диплом не найден")).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/500|error/i);
  });

  it("treats a missing token as not found without querying", () => {
    mockQuery({});
    renderVerification(undefined);
    expect(screen.getByRole("heading", { name: "Диплом не найден" })).toBeInTheDocument();
  });
});
