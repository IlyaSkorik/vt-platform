import { ExternalLink, Link2 } from "lucide-react";
import { useId } from "react";
import { isGoogleDocsUrl } from "@/shared/lib";
import { Input } from "@/shared/ui";

interface RegulationLinkFieldProps {
  value: string;
  disabled?: boolean;
  error?: string;
  onChange: (value: string) => void;
}

/**
 * Link source for a regulation: the organizer pastes a stable document URL
 * (typically a shared Google Doc) instead of uploading a PDF. The URL never
 * changes while the document behind it can be edited freely.
 */
export function RegulationLinkField({
  value,
  disabled = false,
  error,
  onChange,
}: RegulationLinkFieldProps): React.JSX.Element {
  const inputId = useId();
  const trimmed = value.trim();
  const looksLikeGoogleDoc = isGoogleDocsUrl(trimmed);

  return (
    <div className="space-y-2">
      <Input
        id={inputId}
        type="url"
        inputMode="url"
        label="Ссылка на документ"
        placeholder="https://docs.google.com/document/d/…"
        description="Вставьте ссылку на Google Документ (доступ «для всех, у кого есть ссылка»). Ссылка остаётся неизменной — сам документ можно править когда угодно."
        leadingIcon={<Link2 aria-hidden="true" />}
        disabled={disabled}
        {...(error ? { error } : {})}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />

      {trimmed && !error ? (
        <div className="flex flex-wrap items-center gap-2 text-muted-foreground text-xs">
          {looksLikeGoogleDoc ? (
            <span className="text-success">Похоже на ссылку Google Документов.</span>
          ) : null}
          <a
            href={trimmed}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline"
          >
            <ExternalLink className="size-3.5" aria-hidden="true" />
            Открыть ссылку
          </a>
        </div>
      ) : null}
    </div>
  );
}
