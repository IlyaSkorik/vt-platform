import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useRemoveReceipt, useUploadReceipt } from "@/entities/application";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";

import { ReceiptCard } from "./receipt-card";

vi.mock("@/entities/application", () => ({
  useUploadReceipt: vi.fn(),
  useRemoveReceipt: vi.fn(),
}));

const remove = vi.fn();

function aReceipt(id: string, file: string) {
  return { id, fileReference: `uploads/2026/${file}`, uploadedAt: "2026-03-01T12:00:00Z" };
}

function anApplication(
  receipts: ReturnType<typeof aReceipt>[],
  status = "WAITING_PAYMENT",
): ApplicationResource {
  return {
    id: "01900000-0000-7000-8000-0000000000ff",
    status,
    paymentReceipts: receipts,
  } as unknown as ApplicationResource;
}

beforeEach(() => {
  remove.mockClear();
  vi.mocked(useUploadReceipt).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useUploadReceipt>);
  vi.mocked(useRemoveReceipt).mockReturnValue({
    mutate: remove,
    isPending: false,
  } as unknown as ReturnType<typeof useRemoveReceipt>);
});

describe("ReceiptCard", () => {
  it("asks for a receipt while none is attached", () => {
    render(<ReceiptCard application={anApplication([])} />);
    expect(screen.getByText(/Квитанция ещё не загружена/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Загрузить квитанцию" })).toBeInTheDocument();
  });

  it("lists every slip a fee paid in several transfers produced", () => {
    render(
      <ReceiptCard
        application={anApplication([
          aReceipt("r-1", "part-one.pdf"),
          aReceipt("r-2", "part-two.jpg"),
        ])}
      />,
    );
    expect(screen.getByText("part-one.pdf")).toBeInTheDocument();
    expect(screen.getByText("part-two.jpg")).toBeInTheDocument();
    expect(screen.getByText("Квитанций: 2")).toBeInTheDocument();
  });

  it("offers to add another receipt rather than to replace the first", () => {
    render(<ReceiptCard application={anApplication([aReceipt("r-1", "part-one.pdf")])} />);
    expect(screen.getByRole("button", { name: "Добавить квитанцию" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Заменить/ })).not.toBeInTheDocument();
  });

  it("removes the receipt whose row the applicant used", async () => {
    render(
      <ReceiptCard
        application={anApplication([
          aReceipt("r-1", "part-one.pdf"),
          aReceipt("r-2", "wrong-file.pdf"),
        ])}
      />,
    );
    const rows = screen.getAllByRole("button", { name: /Удалить/ });
    await userEvent.click(rows[1]);
    expect(remove).toHaveBeenCalledWith("r-2", expect.anything());
  });

  it("keeps showing a settled order's receipts but offers no controls", () => {
    render(<ReceiptCard application={anApplication([aReceipt("r-1", "paid.pdf")], "PAID")} />);
    expect(screen.getByText("paid.pdf")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /квитанцию/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Удалить/ })).not.toBeInTheDocument();
  });

  it("renders nothing for a settled order that never paid", () => {
    const { container } = render(<ReceiptCard application={anApplication([], "CANCELLED")} />);
    expect(container).toBeEmptyDOMElement();
  });
});
