import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useCompetitionsList } from "@/features/competitions";
import {
  type DocumentSlot,
  type PrintPackageNomination,
  useGenerateDocumentsMutation,
  usePrintJob,
  usePrintPackageSummary,
  useStartPrintPackageMutation,
} from "@/features/diplomas";
import { GenerationSection } from "./generation-section";

Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};

vi.mock("@/features/competitions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/competitions")>()),
  useCompetitionsList: vi.fn(),
}));

vi.mock("@/features/diplomas", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/diplomas")>()),
  useGenerateDocumentsMutation: vi.fn(),
  usePrintJob: vi.fn(),
  usePrintPackageSummary: vi.fn(),
  useStartPrintPackageMutation: vi.fn(),
}));

const COMPETITION_ID = "01900000-0000-7000-8000-0000000000c0";
const VOCALS = "01900000-0000-7000-8000-000000000001";
const DANCE = "01900000-0000-7000-8000-000000000002";

function slot(overrides: Partial<DocumentSlot> = {}): DocumentSlot {
  return {
    templateId: "01900000-0000-7000-8000-0000000000t1",
    templateName: "Шаблон",
    ready: true,
    existing: 0,
    willCreate: 1,
    withoutRecipient: 0,
    ...overrides,
  };
}

const EMPTY_SLOT: DocumentSlot = {
  templateId: null,
  templateName: null,
  ready: false,
  existing: 0,
  willCreate: 0,
  withoutRecipient: 0,
};

/**
 * «Вокал» holds both templates; «Танец» only a diploma one — the shape that used
 * to send «Танец» into a thank-you run and earn a 409 from the backend.
 */
const VOCALS_ROW: PrintPackageNomination = {
  categoryId: VOCALS,
  nomination: "Вокал",
  submissions: 1,
  diploma: slot({ templateName: "Вокал A4" }),
  thankYou: slot({ templateName: "Вокал: благодарность", willCreate: 2 }),
};

const DANCE_ROW: PrintPackageNomination = {
  categoryId: DANCE,
  nomination: "Танец",
  submissions: 1,
  diploma: slot({ templateName: "Танец A4" }),
  thankYou: EMPTY_SLOT,
};

const NOMINATIONS: PrintPackageNomination[] = [VOCALS_ROW, DANCE_ROW];

function setup(nominations: PrintPackageNomination[] = NOMINATIONS): {
  startPrintPackage: ReturnType<typeof vi.fn>;
  generateThanks: ReturnType<typeof vi.fn>;
} {
  const startPrintPackage = vi.fn();
  const generateThanks = vi.fn().mockResolvedValue({
    documentType: "THANK_YOU",
    created: 2,
    regenerated: 0,
    withoutRecipient: 0,
    nominations: 1,
  });

  vi.mocked(useCompetitionsList).mockReturnValue({
    data: [{ id: COMPETITION_ID, title: "Восходящие таланты" }],
    isLoading: false,
  } as unknown as ReturnType<typeof useCompetitionsList>);

  vi.mocked(usePrintPackageSummary).mockReturnValue({
    data: { competitionId: COMPETITION_ID, nominations },
    isLoading: false,
  } as unknown as ReturnType<typeof usePrintPackageSummary>);

  vi.mocked(usePrintJob).mockReturnValue({
    data: undefined,
  } as unknown as ReturnType<typeof usePrintJob>);

  vi.mocked(useStartPrintPackageMutation).mockReturnValue({
    mutate: startPrintPackage,
    reset: vi.fn(),
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useStartPrintPackageMutation>);

  vi.mocked(useGenerateDocumentsMutation).mockReturnValue({
    mutateAsync: generateThanks,
    isPending: false,
  } as unknown as ReturnType<typeof useGenerateDocumentsMutation>);

  return { startPrintPackage, generateThanks };
}

async function chooseCompetition(): Promise<void> {
  const user = userEvent.setup();
  await user.click(screen.getByRole("combobox", { name: "Конкурс" }));
  await user.click(await screen.findByRole("option", { name: "Восходящие таланты" }));
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("GenerationSection", () => {
  it("reports each nomination's template per document type", async () => {
    setup();
    render(<GenerationSection />);
    await chooseCompetition();

    expect(screen.getByText("Вокал A4")).toBeInTheDocument();
    expect(screen.getByText("Вокал: благодарность")).toBeInTheDocument();
    expect(screen.getByText("Танец A4")).toBeInTheDocument();
    // «Танец» has no thank-you template, and the table says so instead of
    // borrowing the diploma one's readiness.
    expect(screen.getByText("шаблон не назначен")).toBeInTheDocument();
  });

  it("sends only thank-you-ready nominations to a letter run", async () => {
    const { generateThanks } = setup();
    render(<GenerationSection />);
    await chooseCompetition();

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: /Сформировать благодарности/ }));

    expect(generateThanks).toHaveBeenCalledWith({
      competitionId: COMPETITION_ID,
      categoryIds: [VOCALS],
      documentType: "THANK_YOU",
      force: false,
    });
  });

  it("still sends every diploma-ready nomination to the print package", async () => {
    const { startPrintPackage } = setup();
    render(<GenerationSection />);
    await chooseCompetition();

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: /Сформировать комплект для печати/ }));

    // The print package also takes an onSuccess handler, so only the payload is
    // asserted rather than the whole call.
    expect(startPrintPackage).toHaveBeenCalledWith(
      { competitionId: COMPETITION_ID, categoryIds: [VOCALS, DANCE], force: false },
      expect.anything(),
    );
  });

  it("disables a run with nothing of its kind to produce", async () => {
    setup([DANCE_ROW]);
    render(<GenerationSection />);
    await chooseCompetition();

    expect(screen.getByRole("button", { name: /Сформировать благодарности/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Сформировать комплект для печати/ })).toBeEnabled();
  });
});
