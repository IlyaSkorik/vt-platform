import { FileText, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import {
  useRemoveSubmissionAttachment,
  useSubmissionDetail,
  useUploadSubmissionAttachment,
} from "@/entities/application";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  toast,
} from "@/shared/ui";

/**
 * Submission statuses whose content the domain still accepts edits to.
 *
 * Gated on the holder submission, not the order: an approved submission is
 * frozen even while its order is still awaiting payment, and the backend would
 * reject the upload.
 */
const EDITABLE_STATUSES = new Set(["DRAFT", "SUBMITTED", "REQUIRES_CORRECTION"]);
const BENEFIT_ACCEPT = ".pdf,image/*";

/** The last segment of a stored file reference, which is what a person recognises. */
function fileName(reference: string): string {
  return reference.split("/").pop() || reference;
}

/**
 * The order-level card for documents that justify a reduced fee — a benefit
 * certificate, a large-family card, a school's letter.
 *
 * The files ride on the order's first submission (the domain hangs attachments
 * off a submission, not the order), but they are presented as belonging to the
 * application as a whole: one certificate covers the заявка, not each number in
 * it. `BENEFIT` is its own attachment kind, distinct from the `DOCUMENT` a
 * competition may require of every applicant.
 *
 * Uploading one forfeits the additional-performance discount — the two do not
 * stack — so that consequence is stated before the file is chosen, not after.
 */
export function BenefitDocumentsCard({
  application,
}: {
  application: ApplicationResource;
}): React.JSX.Element | null {
  const holder = application.submissions[0];
  const holderId = holder?.submissionId;
  const { data: submission } = useSubmissionDetail(holderId);
  const upload = useUploadSubmissionAttachment(holderId ?? "");
  const remove = useRemoveSubmissionAttachment(holderId ?? "");
  const inputRef = useRef<HTMLInputElement>(null);
  const [caption, setCaption] = useState("");

  const documents = (submission?.attachments ?? []).filter((a) => a.type === "BENEFIT");
  const canEdit = holder != null && EDITABLE_STATUSES.has(holder.status);

  if (!holderId || (!canEdit && documents.length === 0)) {
    return null;
  }

  const onFileChosen = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    upload.mutate(
      { file, attachmentType: "BENEFIT", caption: caption.trim() || undefined },
      {
        onSuccess: () => {
          toast.success("Документ прикреплён");
          setCaption("");
        },
        onError: () => toast.error("Не удалось прикрепить документ"),
        onSettled: () => {
          if (inputRef.current) {
            inputRef.current.value = "";
          }
        },
      },
    );
  };

  const onRemove = (attachmentId: string) => {
    remove.mutate(attachmentId, {
      onSuccess: () => toast.success("Документ удалён"),
      onError: () => toast.error("Не удалось удалить документ"),
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>Документы о льготе</CardTitle>
          {documents.length > 0 ? (
            <Badge variant="success">Приложено: {documents.length}</Badge>
          ) : null}
        </div>
        <CardDescription>
          Сертификат, справка или иной документ, подтверждающий право на сниженный взнос или скидку.
          PDF или изображение, до 25 МБ. Один комплект на всю заявку.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {documents.length === 0 ? (
          <p className="text-sm text-muted-foreground">Документы не приложены.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {documents.map((document) => (
              <li
                key={document.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
              >
                <div className="flex min-w-0 items-center gap-2">
                  <FileText className="size-4 shrink-0 text-muted-foreground" />
                  <span className="truncate text-sm">
                    {document.caption?.trim() || fileName(document.fileReference)}
                  </span>
                </div>
                {canEdit ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={remove.isPending}
                    onClick={() => onRemove(document.id)}
                  >
                    <Trash2 className="size-4" />
                    Удалить
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {canEdit ? (
          <>
            <Alert variant="warning">
              Скидки не суммируются: пока к заявке приложен документ о льготе, скидка на второе и
              последующие выступления не применяется.
            </Alert>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <Input
                label="Что за документ (необязательно)"
                placeholder="Например: справка о многодетной семье"
                value={caption}
                onChange={(event) => setCaption(event.target.value)}
                className="sm:flex-1"
              />
              <Button
                variant="outline"
                loading={upload.isPending}
                onClick={() => inputRef.current?.click()}
              >
                Прикрепить документ
              </Button>
              <input
                ref={inputRef}
                type="file"
                accept={BENEFIT_ACCEPT}
                className="hidden"
                aria-label="Документ о льготе"
                onChange={onFileChosen}
              />
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
