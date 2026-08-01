import { FileText, Trash2 } from "lucide-react";
import { useRef } from "react";

import { useRemoveReceipt, useUploadReceipt } from "@/entities/application";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  toast,
} from "@/shared/ui";

/** Order statuses in which the applicant may still change the order's receipts. */
const RECEIPT_STATUSES = new Set(["DRAFT", "SUBMITTED", "WAITING_PAYMENT"]);
const RECEIPT_ACCEPT = ".pdf,image/*";

/** The last segment of a stored file reference, which is what a person recognises. */
function fileName(reference: string): string {
  return reference.split("/").pop() || reference;
}

/**
 * The order-level payment-receipt card, shared by the registration wizard (so a
 * receipt can be attached upfront while the order is still a draft) and the
 * application detail page. It renders nothing for a settled order with no receipt.
 *
 * The receipts are a list, not one document: an order's fee is regularly settled
 * by more than one transfer — a school pays for part of a group and a parent for
 * the rest, or it goes out in instalments — and each transfer produces its own
 * slip. Uploading therefore adds; a file attached by mistake is removed by name.
 */
export function ReceiptCard({
  application,
}: {
  application: ApplicationResource;
}): React.JSX.Element | null {
  const upload = useUploadReceipt(application.id);
  const remove = useRemoveReceipt(application.id);
  const inputRef = useRef<HTMLInputElement>(null);
  const receipts = application.paymentReceipts;
  const canUpload = RECEIPT_STATUSES.has(application.status);

  if (!canUpload && receipts.length === 0) {
    return null;
  }

  const onFileChosen = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    upload.mutate(file, {
      onSuccess: () => toast.success("Квитанция загружена"),
      onError: () => toast.error("Не удалось загрузить квитанцию"),
      onSettled: () => {
        if (inputRef.current) {
          inputRef.current.value = "";
        }
      },
    });
  };

  const onRemove = (receiptId: string) => {
    remove.mutate(receiptId, {
      onSuccess: () => toast.success("Квитанция удалена"),
      onError: () => toast.error("Не удалось удалить квитанцию"),
    });
  };

  const badge =
    receipts.length > 0
      ? ({ label: `Квитанций: ${receipts.length}`, variant: "success" } as const)
      : canUpload
        ? ({ label: "Ожидает квитанцию", variant: "warning" } as const)
        : ({ label: "Квитанция не загружена", variant: "neutral" } as const);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>Квитанции об оплате</CardTitle>
          <Badge variant={badge.variant}>{badge.label}</Badge>
        </div>
        <CardDescription>
          Загрузите подтверждение оплаты организационного взноса (PDF или изображение). Если взнос
          оплачен несколькими платежами, прикрепите квитанцию по каждому. Можно прикрепить сразу при
          подаче заявки.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {receipts.length === 0 ? (
          <p className="text-sm text-muted-foreground">Квитанция ещё не загружена.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {receipts.map((receipt) => (
              <li
                key={receipt.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
              >
                <div className="flex min-w-0 items-center gap-2">
                  <FileText className="size-4 shrink-0 text-muted-foreground" />
                  <span className="truncate text-sm">{fileName(receipt.fileReference)}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {new Date(receipt.uploadedAt).toLocaleDateString("ru-RU")}
                  </span>
                </div>
                {canUpload ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={remove.isPending}
                    onClick={() => onRemove(receipt.id)}
                  >
                    <Trash2 className="size-4" />
                    Удалить
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {canUpload ? (
          <div>
            <Button
              variant="outline"
              size="sm"
              loading={upload.isPending}
              onClick={() => inputRef.current?.click()}
            >
              {receipts.length > 0 ? "Добавить квитанцию" : "Загрузить квитанцию"}
            </Button>
            <input
              ref={inputRef}
              type="file"
              accept={RECEIPT_ACCEPT}
              className="hidden"
              aria-label="Квитанция об оплате"
              onChange={onFileChosen}
            />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
