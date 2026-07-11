import type { _Document, AddDocument } from "@/shared/api/generated/model-competitions";
import { timestampFromUuidV7 } from "@/shared/lib";
import {
  DOCUMENT_FORM_CATEGORIES,
  type DocumentCategory,
  type DocumentFormCategory,
  type DocumentFormValues,
} from "../model/schemas";

export type DocumentListSort =
  | "manual"
  | "title-asc"
  | "title-desc"
  | "date-newest"
  | "date-oldest";

export const DOCUMENT_CATEGORY_LABELS: Record<DocumentCategory, string> = {
  REGULATION: "Положение",
  PROGRAM: "Программа",
  SCHEDULE: "Расписание",
  REQUISITES: "Реквизиты",
  MEMO: "Памятка",
  ACCOMMODATION: "Проживание",
  OTHER: "Другое",
};

export const DOCUMENT_VISIBILITY_LABELS: Record<DocumentFormValues["visibility"], string> = {
  ALL: "Всем",
  PUBLIC: "Публичная страница",
  PARTICIPANTS: "Участники",
  STAFF: "Только сотрудники",
};

export const DOCUMENT_LIST_SORT_OPTIONS: ReadonlyArray<{ value: DocumentListSort; label: string }> =
  [
    { value: "manual", label: "Ручной порядок" },
    { value: "title-asc", label: "Название А–Я" },
    { value: "title-desc", label: "Название Я–А" },
    { value: "date-newest", label: "Сначала новые" },
    { value: "date-oldest", label: "Сначала старые" },
  ];

export function documentUploadDate(document: _Document): Date | null {
  return timestampFromUuidV7(document.id);
}

export function createEmptyDocumentForm(sortOrder = 0): DocumentFormValues {
  return {
    title: "",
    description: "",
    category: "OTHER",
    visibility: "PUBLIC",
    fileReference: "",
    sortOrder,
    published: false,
  };
}

function toFormCategory(category: string): DocumentFormCategory {
  if ((DOCUMENT_FORM_CATEGORIES as readonly string[]).includes(category)) {
    return category as DocumentFormCategory;
  }
  return "OTHER";
}

export function documentToFormValues(document: _Document): DocumentFormValues {
  const visibility = (
    Object.keys(DOCUMENT_VISIBILITY_LABELS) as DocumentFormValues["visibility"][]
  ).includes(document.visibility as DocumentFormValues["visibility"])
    ? (document.visibility as DocumentFormValues["visibility"])
    : "PUBLIC";

  return {
    title: document.title,
    description: document.description ?? "",
    category: toFormCategory(document.category),
    visibility,
    fileReference: document.fileReference,
    sortOrder: document.sortOrder,
    published: document.published,
  };
}

export function documentFormToAddPayload(values: DocumentFormValues): AddDocument {
  return {
    title: values.title.trim(),
    category: values.category,
    visibility: values.visibility,
    fileReference: values.fileReference.trim(),
    description: values.description?.trim() ? values.description.trim() : null,
    sortOrder: values.sortOrder,
    published: values.published,
  };
}

export function documentFormToUpdatePayload(values: DocumentFormValues): {
  title: string;
  category: string;
  visibility: string;
  fileReference: string;
  description: string | null;
  sortOrder: number;
} {
  return {
    title: values.title.trim(),
    category: values.category,
    visibility: values.visibility,
    fileReference: values.fileReference.trim(),
    description: values.description?.trim() ? values.description.trim() : null,
    sortOrder: values.sortOrder,
  };
}

export function nextDocumentSortOrder(documents: _Document[]): number {
  if (documents.length === 0) {
    return 0;
  }
  return Math.max(...documents.map((document) => document.sortOrder)) + 1;
}

export function filterAndSortDocuments(
  documents: _Document[],
  search: string,
  sort: DocumentListSort,
): _Document[] {
  const query = search.trim().toLowerCase();
  const filtered =
    query.length === 0
      ? [...documents]
      : documents.filter((document) => {
          const haystack = `${document.title} ${document.description ?? ""}`.toLowerCase();
          return haystack.includes(query);
        });

  switch (sort) {
    case "title-asc":
      return filtered.sort((left, right) => left.title.localeCompare(right.title, "ru"));
    case "title-desc":
      return filtered.sort((left, right) => right.title.localeCompare(left.title, "ru"));
    case "date-newest":
      return filtered.sort((left, right) => {
        const leftMs = documentUploadDate(left)?.getTime() ?? 0;
        const rightMs = documentUploadDate(right)?.getTime() ?? 0;
        return rightMs - leftMs;
      });
    case "date-oldest":
      return filtered.sort((left, right) => {
        const leftMs = documentUploadDate(left)?.getTime() ?? 0;
        const rightMs = documentUploadDate(right)?.getTime() ?? 0;
        return leftMs - rightMs;
      });
    default:
      return filtered.sort((left, right) => {
        if (left.sortOrder !== right.sortOrder) {
          return left.sortOrder - right.sortOrder;
        }
        return left.title.localeCompare(right.title, "ru");
      });
  }
}

export function isPreviewableDocument(fileReference: string): "pdf" | "image" | null {
  const lower = fileReference.toLowerCase();
  if (lower.endsWith(".pdf") || lower.includes("application/pdf")) {
    return "pdf";
  }
  if (/\.(jpe?g|png|webp)(\?|$)/i.test(lower)) {
    return "image";
  }
  return null;
}

export function buildReorderedSortUpdates(
  orderedIds: string[],
  documents: _Document[],
): Array<{ documentId: string; values: ReturnType<typeof documentFormToUpdatePayload> }> {
  const byId = new Map(documents.map((document) => [document.id, document]));
  const updates: Array<{
    documentId: string;
    values: ReturnType<typeof documentFormToUpdatePayload>;
  }> = [];

  orderedIds.forEach((documentId, index) => {
    const document = byId.get(documentId);
    if (!document || document.sortOrder === index) {
      return;
    }
    updates.push({
      documentId,
      values: documentFormToUpdatePayload({
        ...documentToFormValues(document),
        sortOrder: index,
      }),
    });
  });

  return updates;
}
