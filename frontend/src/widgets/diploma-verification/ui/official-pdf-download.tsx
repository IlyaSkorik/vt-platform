import { Download } from "lucide-react";
import { resolveMediaUrl } from "@/shared/lib";
import { Button } from "@/shared/ui";

/**
 * The official document download.
 *
 * Rendered only once the PDF exists — before the ceremony there is no official
 * document to hand out, and a dead button would misrepresent that. The stored
 * `/media/…` reference is resolved against the API origin.
 *
 * The visible label already names the action, so `aria-label` adds only what sight
 * supplies: that the link opens the file in a new tab.
 */
export function OfficialPdfDownload({
  reference,
}: {
  reference: string;
}): React.JSX.Element | null {
  const href = resolveMediaUrl(reference);
  if (href == null) {
    return null;
  }
  return (
    <Button asChild size="xl" className="w-full sm:w-auto">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Скачать официальный диплом в формате PDF (откроется в новой вкладке)"
      >
        <Download aria-hidden="true" />
        Скачать официальный диплом
      </a>
    </Button>
  );
}
