// Vite resolves the installed pdfjs-dist worker to a served URL (`?url`); a bare
// specifier inside `new URL(..., import.meta.url)` is NOT resolved and 404s.
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { pdfjs } from "react-pdf";

/**
 * Point pdf.js at its worker, bundled by Vite from the installed `pdfjs-dist`.
 * Imported once for its side effect before any <Document> renders.
 */
pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;
