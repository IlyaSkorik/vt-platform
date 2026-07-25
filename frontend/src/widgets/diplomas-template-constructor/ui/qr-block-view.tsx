import { QrCode } from "lucide-react";
import { QR_VERIFICATION_TEXT, type TemplateFieldStyle } from "@/features/diplomas";
import { fieldTextStyle } from "../lib/field-text";

interface QrBlockViewProps {
  /** Resolved diploma number (or "—" when absent). */
  number: string;
  style: TemplateFieldStyle;
  scale: number;
}

/**
 * On-canvas view of the QR block: a placeholder QR square next to the fixed
 * authenticity text and the diploma number. The square stays a placeholder in the
 * editor by design — a template has no diploma, so there is no verification token
 * to encode; the backend draws the real code (pointing at
 * `<domain>/verify/<verificationToken>`) when it renders the diploma PDF.
 * Shared by the editable and read-only renderers so both match.
 */
export function QrBlockView({ number, style, scale }: QrBlockViewProps): React.JSX.Element {
  return (
    <div className="flex h-full w-full items-center gap-2 overflow-hidden">
      <div
        aria-hidden="true"
        className="flex aspect-square h-full max-h-full shrink-0 items-center justify-center rounded-sm border border-neutral-400/70 border-dashed text-muted-foreground"
      >
        <QrCode className="size-[70%]" />
      </div>
      <div
        className="flex min-w-0 flex-1 flex-col justify-center"
        style={{ ...fieldTextStyle(style, scale), fontSize: `${style.fontSize * scale}px` }}
      >
        <span className="whitespace-pre-wrap break-words">{QR_VERIFICATION_TEXT}</span>
        <span className="truncate">{number}</span>
      </div>
    </div>
  );
}
