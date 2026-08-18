import type { MyDocument } from "./types";

/**
 * How the cabinet lays out one participant's documents.
 *
 * Most documents are a row each. The exception is the set of individual diplomas of
 * one entry: an ensemble that named twelve people holds twelve near-identical
 * documents, and twelve rows with twelve download buttons is a list nobody reads and
 * a download nobody finishes. Those collapse into one bundle the page offers as a
 * single archive, with the individual sheets still reachable underneath — a parent
 * wants exactly one of them.
 */
export type DocumentRow =
  | { kind: "document"; key: string; document: MyDocument }
  | { kind: "bundle"; key: string; submissionId: string; documents: MyDocument[] };

/** The kind that is issued per named member of a collective. */
const PER_MEMBER = "INDIVIDUAL_DIPLOMA";

/**
 * Group the flat list into display rows, preserving the server's order.
 *
 * Grouping is by **entry**, not by name or nomination: two ensembles can share a
 * nomination, and one applicant can enter the same ensemble in two festivals — either
 * would merge two unrelated sets into one archive.
 *
 * A lone individual diploma stays an ordinary row. An archive of one file is a worse
 * download than the file, and the bundle's whole justification is the count.
 */
export function documentRows(documents: MyDocument[]): DocumentRow[] {
  const perEntry = new Map<string, MyDocument[]>();
  for (const document of documents) {
    if (document.documentType !== PER_MEMBER) {
      continue;
    }
    const bundle = perEntry.get(document.submissionId);
    if (bundle) {
      bundle.push(document);
    } else {
      perEntry.set(document.submissionId, [document]);
    }
  }

  const rows: DocumentRow[] = [];
  const emitted = new Set<string>();
  for (const document of documents) {
    const bundle =
      document.documentType === PER_MEMBER ? perEntry.get(document.submissionId) : undefined;
    if (!bundle || bundle.length < 2) {
      rows.push({ kind: "document", key: document.id, document });
      continue;
    }
    // The bundle takes the position of its first member, so the group sits where the
    // list already put those documents rather than jumping to the end.
    if (emitted.has(document.submissionId)) {
      continue;
    }
    emitted.add(document.submissionId);
    rows.push({
      kind: "bundle",
      key: `bundle:${document.submissionId}`,
      submissionId: document.submissionId,
      documents: bundle,
    });
  }
  return rows;
}
