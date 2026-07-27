import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type GenerationRunResponse, useGenerationArchive } from "@/features/diplomas";
import { ArchiveSection } from "./archive-section";

vi.mock("@/features/diplomas", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/diplomas")>()),
  useGenerationArchive: vi.fn(),
}));

const PRINT_RUN: GenerationRunResponse = {
  id: "01900000-0000-7000-8000-0000000000r1",
  documentType: "THANK_YOU",
  competitionId: "01900000-0000-7000-8000-0000000000c0",
  competition: "Восходящие таланты",
  nominations: 2,
  documents: 40,
  created: 2,
  published: 0,
  zipUrl: "/media/diplomas/documents/c0/thank_you/ThankYou.zip",
  user: "Петрова Ольга",
  createdAt: "2026-05-20T09:30:00Z",
};

const PUBLISH_RUN: GenerationRunResponse = {
  ...PRINT_RUN,
  id: "01900000-0000-7000-8000-0000000000r2",
  documents: 40,
  created: 0,
  published: 40,
  zipUrl: null,
  user: null,
};

function setup(runs: GenerationRunResponse[]): void {
  vi.mocked(useGenerationArchive).mockReturnValue({
    data: runs,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useGenerationArchive>);
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("ArchiveSection", () => {
  it("reports a run with its author, its size and its archive", () => {
    setup([PRINT_RUN]);
    render(<ArchiveSection />);

    expect(screen.getByText("Восходящие таланты")).toBeInTheDocument();
    expect(screen.getByText("Благодарность")).toBeInTheDocument();
    expect(screen.getByText("Петрова Ольга")).toBeInTheDocument();
    // Both counts: 40 documents of which 2 are new says "reprint", not "generation".
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(screen.getByText(/новых: 2/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Скачать архив/ })).toHaveAttribute(
      "href",
      expect.stringContaining("ThankYou.zip"),
    );
  });

  it("offers no download for a run that printed nothing", () => {
    setup([PUBLISH_RUN]);
    render(<ArchiveSection />);

    const row = screen.getByText("без архива").closest("tr");
    expect(row).not.toBeNull();
    // A publish-only run built no ZIP, so there is no dead link in its place.
    expect(within(row as HTMLElement).queryByRole("link")).not.toBeInTheDocument();
    // …and an unattributed run still lists, with a dash where the name would be.
    expect(within(row as HTMLElement).getByText("—")).toBeInTheDocument();
  });

  it("says the archive is empty before the first generation", () => {
    setup([]);
    render(<ArchiveSection />);

    expect(screen.getByText("Архив пуст")).toBeInTheDocument();
  });
});
