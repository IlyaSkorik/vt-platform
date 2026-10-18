import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useCompetitionsList } from "@/features/competitions";
import {
  type DocumentSlot,
  type PrintPackageNomination,
  useDocumentJob,
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
  useDocumentJob: vi.fn(),
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
    withoutTemplate: 0,
    disciplines: [],
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
  withoutTemplate: 0,
  disciplines: [],
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
  individualDiploma: slot({ templateName: "Вокал: участнику", willCreate: 3 }),
  thankYou: slot({ templateName: "Вокал: благодарность", willCreate: 2 }),
};

const DANCE_ROW: PrintPackageNomination = {
  categoryId: DANCE,
  nomination: "Танец",
  submissions: 1,
  diploma: slot({ templateName: "Танец A4" }),
  individualDiploma: EMPTY_SLOT,
  thankYou: EMPTY_SLOT,
};

const NOMINATIONS: PrintPackageNomination[] = [VOCALS_ROW, DANCE_ROW];

const THANKS_JOB_ID = "01900000-0000-7000-8000-0000000000j1";
const THANKS_ZIP = "/media/diplomas/documents/c1/thank_you/ThankYou.zip";

/**
 * The job a settled thank-you run comes back as.
 *
 * ``bundle`` is read off the request the component made, because that is what
 * the real job records and what the page reads to decide between "published to
 * the cabinets" and "here is the archive".
 */
function settledJob(request: { bundle?: boolean } | undefined, status = "COMPLETED"): unknown {
  return {
    jobId: THANKS_JOB_ID,
    competitionId: COMPETITION_ID,
    categoryIds: [VOCALS],
    documentType: "THANK_YOU",
    force: false,
    bundle: Boolean(request?.bundle),
    publish: !request?.bundle,
    status,
    error: status === "FAILED" ? "Для этого жанра не назначен шаблон такого типа." : null,
    result:
      status === "COMPLETED"
        ? {
            documentType: "THANK_YOU",
            created: 2,
            regenerated: 0,
            withoutRecipient: 0,
            withoutTemplate: 0,
            nominations: 1,
            documents: 2,
            published: 2,
            zipUrl: THANKS_ZIP,
          }
        : null,
    createdAt: "2026-05-20T12:00:00Z",
    updatedAt: "2026-05-20T12:00:05Z",
  };
}

function setup(
  nominations: PrintPackageNomination[] = NOMINATIONS,
  jobStatus = "COMPLETED",
): {
  startPrintPackage: ReturnType<typeof vi.fn>;
  generateThanks: ReturnType<typeof vi.fn>;
} {
  const startPrintPackage = vi.fn();
  // The request answers with a job; the outcome arrives by polling it.
  const generateThanks = vi.fn().mockResolvedValue({ jobId: THANKS_JOB_ID });

  // Nothing to poll until a run is queued, so the hook is asked with `undefined`
  // on first render and with the id afterwards — exactly as the component does.
  vi.mocked(useDocumentJob).mockImplementation(
    (jobId?: string) =>
      ({
        data: jobId ? settledJob(generateThanks.mock.lastCall?.[0], jobStatus) : undefined,
      }) as unknown as ReturnType<typeof useDocumentJob>,
  );

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
  await user.click(screen.getByRole("combobox", { name: "Фестиваль" }));
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
    // «Танец» has neither a thank-you nor an individual-diploma template, and the
    // table says so for each instead of borrowing the diploma one's readiness.
    expect(screen.getAllByText("шаблон не назначен")).toHaveLength(2);
  });

  it("sends only thank-you-ready nominations to a letter run", async () => {
    const { generateThanks } = setup();
    render(<GenerationSection />);
    await chooseCompetition();

    await userEvent.setup().click(screen.getByRole("button", { name: /опубликовать в ЛК/ }));

    expect(generateThanks).toHaveBeenCalledWith({
      competitionId: COMPETITION_ID,
      categoryIds: [VOCALS],
      documentType: "THANK_YOU",
      force: false,
      bundle: false,
      publish: true,
    });
  });

  it("prepares a print run without publishing anything, and offers the download", async () => {
    const { generateThanks } = setup();
    render(<GenerationSection />);
    await chooseCompetition();

    await userEvent.setup().click(screen.getByRole("button", { name: /скачать для печати/ }));

    // The print action asks for the archive and withholds publication: preparing
    // sheets to hand out is not the same decision as showing them in a cabinet.
    expect(generateThanks).toHaveBeenCalledWith({
      competitionId: COMPETITION_ID,
      categoryIds: [VOCALS],
      documentType: "THANK_YOU",
      force: false,
      bundle: true,
      publish: false,
    });
    const download = await screen.findByRole("link", { name: /Скачать ZIP с благодарностями/ });
    expect(download).toHaveAttribute("href", expect.stringContaining(THANKS_ZIP));
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

  it("keeps the letter actions busy until the queued run settles", async () => {
    setup(NOMINATIONS, "RUNNING");
    render(<GenerationSection />);
    await chooseCompetition();

    await userEvent.setup().click(screen.getByRole("button", { name: /скачать для печати/ }));

    // The run is the worker's now, so the page waits on the job rather than on the
    // request — and offers no archive before there is one.
    expect(await screen.findByRole("button", { name: /скачать для печати/ })).toBeDisabled();
    expect(
      screen.queryByRole("link", { name: /Скачать ZIP с благодарностями/ }),
    ).not.toBeInTheDocument();
  });

  it("disables a run with nothing of its kind to produce", async () => {
    setup([DANCE_ROW]);
    render(<GenerationSection />);
    await chooseCompetition();

    expect(screen.getByRole("button", { name: /опубликовать в ЛК/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /скачать для печати/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Сформировать комплект для печати/ })).toBeEnabled();
  });
});
