import type { _Regulation, AddRegulation } from "@/shared/api/generated/model-competitions";
import type { RegulationDraftValues } from "../model/schemas";

const DRAFT_STORAGE_PREFIX = "competition-regulation-draft:";
const CHANGE_NOTES_STORAGE_PREFIX = "competition-regulation-notes:";

export function sortRegulationsNewestFirst(regulations: _Regulation[]): _Regulation[] {
  return [...regulations].sort((left, right) => {
    const byDate = right.publicationDate.localeCompare(left.publicationDate);
    if (byDate !== 0) {
      return byDate;
    }
    return right.version.localeCompare(left.version, undefined, { numeric: true });
  });
}

export function findCurrentRegulation(
  regulations: _Regulation[],
  currentRegulationId: string | null | undefined,
): _Regulation | null {
  if (currentRegulationId) {
    const byId = regulations.find((item) => item.id === currentRegulationId);
    if (byId) {
      return byId;
    }
  }
  return regulations.find((item) => item.isCurrent) ?? null;
}

/** Suggest the next semver-like label from the newest published version. */
export function suggestNextRegulationVersion(regulations: _Regulation[]): string {
  const newest = sortRegulationsNewestFirst(regulations)[0];
  if (!newest) {
    return "1.0";
  }
  const match = /^(\d+)(?:\.(\d+))?/.exec(newest.version.trim());
  if (!match) {
    return `${newest.version}-next`;
  }
  const major = Number(match[1]);
  const minor = Number(match[2] ?? "0");
  if (Number.isNaN(major) || Number.isNaN(minor)) {
    return `${newest.version}-next`;
  }
  return `${major}.${minor + 1}`;
}

export function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function createEmptyRegulationDraft(
  regulations: _Regulation[],
  base?: _Regulation | null,
): RegulationDraftValues {
  return {
    title: base?.title ?? "Положение конкурса",
    version: suggestNextRegulationVersion(regulations),
    publicationDate: todayIsoDate(),
    fileReference: "",
    changeNote: "",
  };
}

export function draftToAddRegulationPayload(values: RegulationDraftValues): AddRegulation {
  return {
    title: values.title.trim(),
    version: values.version.trim(),
    publicationDate: values.publicationDate,
    fileReference: values.fileReference.trim(),
  };
}

export function loadRegulationDraft(competitionId: string): RegulationDraftValues | null {
  try {
    const raw = sessionStorage.getItem(`${DRAFT_STORAGE_PREFIX}${competitionId}`);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<RegulationDraftValues>;
    if (typeof parsed.title !== "string" || typeof parsed.version !== "string") {
      return null;
    }
    return {
      title: parsed.title,
      version: parsed.version,
      publicationDate:
        typeof parsed.publicationDate === "string" && parsed.publicationDate.length > 0
          ? parsed.publicationDate
          : todayIsoDate(),
      fileReference: typeof parsed.fileReference === "string" ? parsed.fileReference : "",
      changeNote: typeof parsed.changeNote === "string" ? parsed.changeNote : "",
    };
  } catch {
    return null;
  }
}

export function saveRegulationDraft(competitionId: string, values: RegulationDraftValues): void {
  sessionStorage.setItem(`${DRAFT_STORAGE_PREFIX}${competitionId}`, JSON.stringify(values));
}

export function clearRegulationDraft(competitionId: string): void {
  sessionStorage.removeItem(`${DRAFT_STORAGE_PREFIX}${competitionId}`);
}

export function rememberRegulationChangeNote(
  competitionId: string,
  version: string,
  note: string,
): void {
  const trimmed = note.trim();
  if (!trimmed) {
    return;
  }
  try {
    const key = `${CHANGE_NOTES_STORAGE_PREFIX}${competitionId}`;
    const current = JSON.parse(sessionStorage.getItem(key) ?? "{}") as Record<string, string>;
    current[version] = trimmed;
    sessionStorage.setItem(key, JSON.stringify(current));
  } catch {
    // Ignore storage failures; changelog still works without notes.
  }
}

export function loadRegulationChangeNotes(competitionId: string): Record<string, string> {
  try {
    const raw = sessionStorage.getItem(`${CHANGE_NOTES_STORAGE_PREFIX}${competitionId}`);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as Record<string, string>;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export interface RegulationChangeLogEntry {
  id: string;
  version: string;
  title: string;
  publicationDate: string;
  isCurrent: boolean;
  changeNote?: string;
  summary: string;
}

export function buildRegulationChangeLog(
  regulations: _Regulation[],
  changeNotes: Record<string, string> = {},
): RegulationChangeLogEntry[] {
  return sortRegulationsNewestFirst(regulations).map((regulation) => {
    const note = changeNotes[regulation.version]?.trim();
    const summary = regulation.isCurrent
      ? `Опубликована версия ${regulation.version} и назначена текущей.`
      : `Опубликована версия ${regulation.version}.`;
    return {
      id: regulation.id,
      version: regulation.version,
      title: regulation.title,
      publicationDate: regulation.publicationDate,
      isCurrent: regulation.isCurrent,
      ...(note ? { changeNote: note } : {}),
      summary,
    };
  });
}
