import { Maximize2, Minus, Plus } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Document, Page } from "react-pdf";
import { Button, Spinner } from "@/shared/ui";
import "../lib/pdf-worker";
import { useConstructorFieldsContext } from "../model/fields-context";
import { usePreviewData } from "../model/preview-context";
import { CanvasOverlay } from "./canvas-overlay";

const MIN_SCALE = 0.25;
const MAX_SCALE = 3;
const SCALE_STEP = 0.1;
const SCROLL_PADDING = 48; // matches the p-6 scroll padding, both sides

function clampScale(value: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, Math.round(value * 100) / 100));
}

interface PdfViewerProps {
  url: string;
}

/**
 * View-only PDF viewer: renders every page top-to-bottom with vertical scroll,
 * a zoom control, and a transparent overlay per page for the future editor.
 * The PDF is the immutable background — no text/annotation layers, no editing.
 */
export function PdfViewer({ url }: PdfViewerProps): React.JSX.Element {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { deselect } = useConstructorFieldsContext();
  const { mode: previewMode, setMode: setPreviewMode } = usePreviewData();
  const [numPages, setNumPages] = useState(0);
  const [scale, setScale] = useState(1);
  // Native (scale-1) page sizes in PDF points — the coordinate system future
  // fields position against. Keyed by 1-based page number.
  const pageSizes = useRef<Map<number, { width: number; height: number }>>(new Map());
  // Fit the template to the viewport width once, when it first opens; after that
  // the zoom is the user's to control.
  const autoFitDone = useRef(false);

  const zoomOut = useCallback(() => setScale((s) => clampScale(s - SCALE_STEP)), []);
  const zoomIn = useCallback(() => setScale((s) => clampScale(s + SCALE_STEP)), []);

  const fitWidth = useCallback(() => {
    const container = scrollRef.current;
    const first = pageSizes.current.get(1);
    if (!container || !first) {
      return;
    }
    const available = container.clientWidth - SCROLL_PADDING;
    if (available > 0) {
      setScale(clampScale(available / first.width));
    }
  }, []);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-1 border-border border-b bg-card/80 px-3 py-1.5 backdrop-blur">
        <Button variant="ghost" size="sm" iconOnly onClick={zoomOut} aria-label="Уменьшить">
          <Minus className="size-4" aria-hidden="true" />
        </Button>
        <span className="w-12 text-center text-muted-foreground text-sm tabular-nums">
          {Math.round(scale * 100)}%
        </span>
        <Button variant="ghost" size="sm" iconOnly onClick={zoomIn} aria-label="Увеличить">
          <Plus className="size-4" aria-hidden="true" />
        </Button>
        <Button variant="ghost" size="sm" onClick={fitWidth}>
          <Maximize2 className="size-4" aria-hidden="true" />
          По ширине
        </Button>
        {/* Flip preview data to confirm one field renders both scenarios. */}
        <div className="ml-auto flex items-center gap-1">
          <span className="mr-1 text-muted-foreground text-xs">Превью:</span>
          <Button
            variant={previewMode === "individual" ? "primary" : "ghost"}
            size="sm"
            onClick={() => setPreviewMode("individual")}
          >
            Соло
          </Button>
          <Button
            variant={previewMode === "collective" ? "primary" : "ghost"}
            size="sm"
            onClick={() => setPreviewMode("collective")}
          >
            Коллектив
          </Button>
        </div>
      </div>
      {/* Pointerdown on empty space deselects; fields/handles stopPropagation. */}
      <div
        ref={scrollRef}
        className="scrollbar-custom min-h-0 flex-1 overflow-auto p-6"
        onPointerDown={() => deselect()}
      >
        <Document
          file={url}
          onLoadSuccess={({ numPages: count }) => setNumPages(count)}
          loading={
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          }
          error={<p className="py-12 text-center text-danger text-sm">Не удалось загрузить PDF.</p>}
          className="mx-auto flex w-fit flex-col items-center gap-6"
        >
          {Array.from({ length: numPages }, (_, index) => index + 1).map((pageNumber) => (
            <div key={pageNumber} className="relative shadow-elevation-1" data-page={pageNumber}>
              <Page
                pageNumber={pageNumber}
                scale={scale}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                onLoadSuccess={(page) => {
                  pageSizes.current.set(pageNumber, {
                    width: page.originalWidth,
                    height: page.originalHeight,
                  });
                  // Auto-fit to width once the first page's size is known.
                  if (pageNumber === 1 && !autoFitDone.current) {
                    autoFitDone.current = true;
                    fitWidth();
                  }
                }}
              />
              {/* Transparent editor layer hosting the fields. */}
              <CanvasOverlay pageNumber={pageNumber} scale={scale} />
            </div>
          ))}
        </Document>
      </div>
    </div>
  );
}
