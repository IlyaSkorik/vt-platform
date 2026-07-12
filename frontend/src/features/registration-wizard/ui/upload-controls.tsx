import { useRef } from "react";

import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import type { RegistrationUploadRequirement } from "@/shared/api/generated/model-public-catalog";
import { Badge, Button } from "@/shared/ui";

import { useRemoveAttachment, useUploadAttachment } from "../api/hooks";

type UploadKind = { attachmentType: "MUSIC" | "VIDEO" | "DOCUMENT"; label: string; hint: string };

/** Which upload controls to show for a format, per its upload requirement. */
function uploadKinds(requirement: RegistrationUploadRequirement | undefined): UploadKind[] {
  if (!requirement) {
    return [];
  }
  const kinds: UploadKind[] = [];
  if (requirement.musicRequired || requirement.musicAllowedFormats.length > 0) {
    kinds.push({
      attachmentType: "MUSIC",
      label: requirement.musicRequired ? "Фонограмма (обязательно)" : "Фонограмма",
      hint: `${requirement.musicAllowedFormats.join(", ")} · до ${requirement.musicMaxUploadSizeMb} МБ`,
    });
  }
  if (requirement.videoMode === "FILE_ONLY" || requirement.videoMode === "URL_OR_FILE") {
    kinds.push({ attachmentType: "VIDEO", label: "Видео", hint: "Видеофайл выступления" });
  }
  if (requirement.receiptRequired) {
    kinds.push({
      attachmentType: "DOCUMENT",
      label: "Квитанция об оплате",
      hint: "PDF или изображение",
    });
  }
  return kinds;
}

function UploadRow({
  submissionId,
  kind,
  submission,
}: {
  submissionId: string;
  kind: UploadKind;
  submission: SubmissionResource;
}): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadAttachment(submissionId);
  const remove = useRemoveAttachment(submissionId);
  const existing = submission.attachments.filter(
    (attachment) => attachment.type === kind.attachmentType,
  );

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium">{kind.label}</p>
          <p className="text-xs text-muted-foreground">{kind.hint}</p>
        </div>
      </div>
      {existing.map((attachment) => (
        <div key={attachment.id} className="flex items-center justify-between gap-2">
          <Badge variant="success">{attachment.caption || "Загружено"}</Badge>
          <Button
            variant="ghost"
            size="xs"
            loading={remove.isPending}
            onClick={() => remove.mutate(attachment.id)}
          >
            Удалить
          </Button>
        </div>
      ))}
      <div className="flex items-center gap-2">
        <input ref={inputRef} type="file" className="text-sm" aria-label={kind.label} />
        <Button
          variant="outline"
          size="sm"
          loading={upload.isPending}
          onClick={() => {
            const input = inputRef.current;
            const file = input?.files?.[0];
            if (file) {
              upload.mutate(
                { file, attachmentType: kind.attachmentType },
                {
                  onSuccess: () => {
                    input.value = "";
                  },
                },
              );
            }
          }}
        >
          Загрузить
        </Button>
      </div>
    </div>
  );
}

/** Render the upload controls required for the submission's selected format. */
export function UploadControls({
  submissionId,
  submission,
  requirement,
}: {
  submissionId: string;
  submission: SubmissionResource;
  requirement: RegistrationUploadRequirement | undefined;
}): React.JSX.Element {
  const kinds = uploadKinds(requirement);
  if (kinds.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Для выбранного формата загрузка файлов не требуется.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {kinds.map((kind) => (
        <UploadRow
          key={kind.attachmentType}
          submissionId={submissionId}
          kind={kind}
          submission={submission}
        />
      ))}
    </div>
  );
}
