/**
 * What the voting page decides for itself, kept out of the components.
 *
 * All pure functions over the payload, so the rules that matter — whether a tap
 * does anything, what the button says, how the board ranks — are testable without
 * rendering anything.
 */
import type { PublicBallot, PublicNominee } from "./api";

/** Whether this reader can still do anything on this page. */
export function canVote(ballot: PublicBallot | undefined): boolean {
  return Boolean(ballot?.open && ballot.votesLeft > 0);
}

/**
 * Whether tapping this card should do anything.
 *
 * A nominee already backed stays visibly chosen but inert: un-voting is not a
 * thing a ballot supports, and a card that looks tappable and is not is worse than
 * one that plainly is not.
 */
export function canPick(ballot: PublicBallot | undefined, nominee: PublicNominee): boolean {
  return canVote(ballot) && !nominee.chosen;
}

/**
 * What the page says about this reader's remaining votes.
 *
 * Silent on a one-vote ballot, which is nearly all of them: telling somebody they
 * have one vote left before they have used it is noise.
 */
export function votesLeftLabel(ballot: PublicBallot | undefined): string | null {
  if (!ballot?.open || ballot.votesPerVoter <= 1) {
    return null;
  }
  if (ballot.votesLeft <= 0) {
    return "Вы использовали все свои голоса";
  }
  return `Осталось голосов: ${ballot.votesLeft} из ${ballot.votesPerVoter}`;
}

/**
 * The line explaining why nothing can be done, or `null` while voting is open.
 *
 * Prefers the server's own wording: it knows whether the vote is over, has not
 * started, or was closed by hand, and the client would only be guessing.
 */
export function closedLabel(ballot: PublicBallot | undefined): string | null {
  if (!ballot || ballot.open) {
    return null;
  }
  if (ballot.closedReason) {
    return ballot.closedReason;
  }
  return ballot.status === "CLOSED" ? "Голосование завершено." : "Голосование сейчас закрыто.";
}

/** Whether this reader has spent anything at all in the current window. */
export function hasVoted(ballot: PublicBallot | undefined): boolean {
  return Boolean(ballot?.nominees.some((nominee) => nominee.chosen));
}

/**
 * The board's order: most votes first, then the ballot's own order.
 *
 * The second key matters more than it looks. Before anybody votes every count is
 * equal, and without a stable tiebreak the list would reshuffle itself on every
 * poll in front of a room full of people.
 */
export function ranked(nominees: PublicNominee[]): PublicNominee[] {
  return [...nominees].sort(
    (left, right) => (right.votes ?? 0) - (left.votes ?? 0) || left.position - right.position,
  );
}

/**
 * Each nominee's share of the vote, as a percentage of the leader.
 *
 * Relative to the leader rather than to the total, because the board draws bars
 * and a bar chart is read by comparing lengths: scaling to the total leaves every
 * bar short and indistinguishable when the field is wide.
 */
export function barWidth(nominee: PublicNominee, nominees: PublicNominee[]): number {
  const leader = Math.max(...nominees.map((row) => row.votes ?? 0), 0);
  if (leader <= 0) {
    return 0;
  }
  return Math.round(((nominee.votes ?? 0) / leader) * 100);
}
