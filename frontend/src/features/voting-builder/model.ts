/**
 * The organizer's side of a ballot, as rules rather than as markup.
 *
 * Pure functions over the payload, so what the editor allows — and what it warns
 * about — is testable without rendering anything.
 */
import type { Ballot, BallotStatus, Nominee, RevealPolicy } from "./api";

/** A vote needs something to choose between. */
export const MINIMUM_NOMINEES = 2;

export const STATUS_LABELS: Record<BallotStatus, string> = {
  DRAFT: "Черновик",
  OPEN: "Идёт голосование",
  CLOSED: "Завершено",
};

export const REVEAL_LABELS: Record<RevealPolicy, string> = {
  ALWAYS: "Показывать сразу",
  AFTER_CLOSE: "Показать после завершения",
  NEVER: "Только организатору",
};

export const REVEAL_OPTIONS = (Object.keys(REVEAL_LABELS) as RevealPolicy[]).map((value) => ({
  value,
  label: REVEAL_LABELS[value],
}));

/** How each status is coloured in a list. */
export function statusVariant(status: BallotStatus): "neutral" | "success" | "info" {
  if (status === "OPEN") return "success";
  return status === "CLOSED" ? "neutral" : "info";
}

/** The nominees a vote may actually be cast for. */
export function votable(ballot: Ballot | undefined): Nominee[] {
  return (ballot?.nominees ?? []).filter((nominee) => !nominee.withdrawn);
}

/** Whether the ballot can be opened right now, and why not when it cannot. */
export function openBlockedReason(ballot: Ballot | undefined): string | null {
  if (!ballot) {
    return "Голосование не загружено";
  }
  if (ballot.status === "CLOSED") {
    return "Голосование завершено — его нельзя открыть заново";
  }
  if (ballot.status === "OPEN") {
    return null;
  }
  if (votable(ballot).length < MINIMUM_NOMINEES) {
    return "Добавьте хотя бы двух номинантов";
  }
  return null;
}

/**
 * The public address of a ballot, for the QR and for reading aloud.
 *
 * Absolute because it is copied onto a poster and into a chat, where a relative
 * path means nothing.
 */
export function publicUrl(slug: string, origin?: string): string {
  const base = origin ?? (typeof window === "undefined" ? "" : window.location.origin);
  return `${base}/vote/${slug}`;
}

/**
 * What an organizer should be told before they promise the hall anything.
 *
 * The honest version rather than the flattering one: this tier of protection stops
 * somebody holding F5 and a script from one machine. It does not stop a determined
 * person with a VPN and a private window, and an organizer who does not know that
 * will promise more than the platform can deliver.
 */
export const ANTI_FRAUD_NOTE =
  "Один голос с устройства. Это останавливает случайные повторы и накрутку с одной машины, " +
  "но не человека с VPN в режиме инкогнито — учитывайте это, если у голосования есть приз.";

/**
 * Whether showing the running count is a risk worth naming.
 *
 * A live scoreboard tells a would-be stuffer exactly how many votes they still
 * need, which is why it is not the default and why choosing it earns a warning.
 */
export function revealWarning(reveal: RevealPolicy): string | null {
  return reveal === "ALWAYS"
    ? "Живой счёт виден всем — он же подсказывает накрутчику, сколько голосов не хватает."
    : null;
}
