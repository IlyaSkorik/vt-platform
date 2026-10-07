import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useRemoveSubmissionAttachment,
  useSubmissionDetail,
  useUploadSubmissionAttachment,
} from "@/entities/application";
import type {
  ApplicationResource,
  SubmissionResource,
} from "@/shared/api/generated/model-applications";

import { BenefitDocumentsCard } from "./benefit-documents-card";

vi.mock("@/entities/application", () => ({
  useSubmissionDetail: vi.fn(),
  useUploadSubmissionAttachment: vi.fn(),
  useRemoveSubmissionAttachment: vi.fn(),
}));

const HOLDER = "01900000-0000-7000-8000-000000000001";

function anApplication(submissionStatus = "DRAFT"): ApplicationResource {
  return {
    id: "01900000-0000-7000-8000-0000000000ff",
    status: "DRAFT",
    submissions: [{ submissionId: HOLDER, status: submissionStatus }],
  } as unknown as ApplicationResource;
}

function aSubmission(attachments: SubmissionResource["attachments"]): SubmissionResource {
  return { id: HOLDER, attachments } as unknown as SubmissionResource;
}

function anAttachment(type: string, caption: string | null) {
  return {
    id: `${type}-1`,
    type,
    fileReference: "uploads/2026/spravka.pdf",
    caption,
  } as unknown as NonNullable<SubmissionResource["attachments"]>[number];
}

beforeEach(() => {
  vi.mocked(useUploadSubmissionAttachment).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useUploadSubmissionAttachment>);
  vi.mocked(useRemoveSubmissionAttachment).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRemoveSubmissionAttachment>);
});

function stubSubmission(attachments: SubmissionResource["attachments"]): void {
  vi.mocked(useSubmissionDetail).mockReturnValue({
    data: aSubmission(attachments),
  } as unknown as ReturnType<typeof useSubmissionDetail>);
}

describe("BenefitDocumentsCard", () => {
  it("warns that the discount will not stack before a file is chosen", () => {
    stubSubmission([]);
    render(<BenefitDocumentsCard application={anApplication()} />);
    expect(screen.getByText(/Документы не приложены/)).toBeInTheDocument();
    expect(screen.getByText(/Скидки не суммируются/)).toBeInTheDocument();
  });

  it("lists benefit documents by their caption and ignores other attachment kinds", () => {
    stubSubmission([
      anAttachment("BENEFIT", "Справка о многодетной семье"),
      anAttachment("MUSIC", "Фонограмма"),
      anAttachment("DOCUMENT", "Свидетельство о рождении"),
    ]);
    render(<BenefitDocumentsCard application={anApplication()} />);
    expect(screen.getByText("Справка о многодетной семье")).toBeInTheDocument();
    expect(screen.queryByText("Фонограмма")).not.toBeInTheDocument();
    expect(screen.queryByText("Свидетельство о рождении")).not.toBeInTheDocument();
  });

  it("falls back to the file name when the applicant left the caption empty", () => {
    stubSubmission([anAttachment("BENEFIT", null)]);
    render(<BenefitDocumentsCard application={anApplication()} />);
    expect(screen.getByText("spravka.pdf")).toBeInTheDocument();
  });

  it("hides the controls once the submission is frozen, but keeps showing the files", () => {
    stubSubmission([anAttachment("BENEFIT", "Справка")]);
    render(<BenefitDocumentsCard application={anApplication("COMPLETED")} />);
    expect(screen.getByText("Справка")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Прикрепить документ/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Удалить/ })).not.toBeInTheDocument();
  });

  it("renders nothing for a frozen submission with no documents", () => {
    stubSubmission([]);
    const { container } = render(<BenefitDocumentsCard application={anApplication("COMPLETED")} />);
    expect(container).toBeEmptyDOMElement();
  });
});
