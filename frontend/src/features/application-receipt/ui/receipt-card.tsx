import { CheckCircle2 } from "lucide-react";
import { useRef } from "react";

import { useUploadReceipt } from "@/entities/application";
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

/** Order statuses in which the applicant may still attach the payment receipt. */
const RECEIPT_STATUSES = new Set(["DRAFT", "SUBMITTED", "WAITING_PAYMENT"]);
const RECEIPT_ACCEPT = ".pdf,image/*";

/**
 * The order-level payment-receipt card, shared by the registration wizard (so a
 * receipt can be attached upfront while the order is still a draft) and the
 * application detail page. It renders nothing for a settled order with no receipt.
 */
export function ReceiptCard({
  application,
}: {
  application: ApplicationResource;
}): React.JSX.Element | null {
  const upload = useUploadReceipt(application.id);
  const inputRef = useRef<HTMLInputElement>(null);
  const receipt = application.paymentReceipt;
  const canUpload = RECEIPT_STATUSES.has(application.status);

  if (!canUpload && !receipt) {
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

  const badge = receipt
    ? ({ label: "Квитанция загружена", variant: "success" } as const)
    : canUpload
      ? ({ label: "Ожидает квитанцию", variant: "warning" } as const)
      : ({ label: "Квитанция не загружена", variant: "neutral" } as const);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>Квитанция об оплате</CardTitle>
          <Badge variant={badge.variant}>{badge.label}</Badge>
        </div>
        <CardDescription>
          Загрузите подтверждение оплаты организационного взноса (PDF или изображение). Можно
          прикрепить сразу при подаче заявки.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {receipt ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="size-4 text-success" />
            Квитанция загружена {new Date(receipt.uploadedAt).toLocaleDateString("ru-RU")}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Квитанция ещё не загружена.</p>
        )}
        {canUpload ? (
          <div>
            <Button
              variant="outline"
              size="sm"
              loading={upload.isPending}
              onClick={() => inputRef.current?.click()}
            >
              {receipt ? "Заменить квитанцию" : "Загрузить квитанцию"}
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
