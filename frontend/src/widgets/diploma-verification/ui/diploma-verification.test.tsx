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

/** No default: a test passing `undefined` means "no token in the URL". */
function renderVerification(token?: string) {
  return render(<DiplomaVerification verificationToken={token} />);
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("DiplomaVerification", () => {
  it("renders a skeleton while verifying", () => {
    mockQuery({ isPending: true });
    const { container } = renderVerification("tok-1");
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("confirms the diploma and shows its facts on success", () => {
    mockQuery({ data: makeVerifiedDiploma() });
    renderVerification("tok-1");
    expect(screen.getByText("Диплом подтверждён")).toBeInTheDocument();
    expect(screen.getByText("VT-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("Иванов Иван")).toBeInTheDocument();
    expect(screen.getByText("Лауреат I степени")).toBeInTheDocument();
  });

  it("says results are unpublished when no degree is awarded yet", () => {
    mockQuery({ data: makeVerifiedDiploma({ degree: null }) });
    renderVerification("tok-1");
    expect(screen.getByText("Степень")).toBeInTheDocument();
    expect(screen.getByText("Результаты конкурса ещё не опубликованы")).toBeInTheDocument();
  });

  it("hides the download until the official PDF exists", () => {
    mockQuery({ data: makeVerifiedDiploma({ officialPdfUrl: null }) });
    renderVerification("tok-1");
    expect(screen.queryByRole("link", { name: /скачать/i })).not.toBeInTheDocument();
  });

  it("links the official PDF once it exists", () => {
    mockQuery({ data: makeVerifiedDiploma() });
    renderVerification("tok-1");
    const link = screen.getByRole("link", { name: /скачать официальный диплом/i });
    // The stored `/media/…` reference is resolved against the API origin.
    expect(link).toHaveAttribute(
      "href",
      expect.stringContaining("/media/diplomas/official/VT-2026-000001.pdf"),
    );
  });

  it("renders the not-found state on a 404", () => {
    mockQuery({ isError: true, error: { status: 404 } as ApiError });
    renderVerification("tok-1");
    expect(screen.getByText("Диплом не найден")).toBeInTheDocument();
    expect(screen.getByText("Проверьте QR-код или номер диплома.")).toBeInTheDocument();
  });

  it("offers a retry on a non-404 error, never a failed check", () => {
    mockQuery({ isError: true, error: { status: 500 } as ApiError });
    renderVerification("tok-1");
    expect(screen.getByRole("button", { name: /повторить/i })).toBeInTheDocument();
    expect(screen.queryByText("Диплом не найден")).not.toBeInTheDocument();
  });

  it("treats a missing token as not found without querying", () => {
    mockQuery({});
    renderVerification(undefined);
    expect(screen.getByText("Диплом не найден")).toBeInTheDocument();
  });
});
