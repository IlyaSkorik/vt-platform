import { useEffect } from "react";

import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import { useAutosave, useServerDraft } from "@/shared/hooks";
import { Input, toast } from "@/shared/ui";

import { useSetParticipantMemberCount } from "../api/hooks";

type Participant = SubmissionResource["participants"][number];

/** Mirrors the backend bound on one entry's headcount (`_MAX_COLLECTIVE_MEMBERS`). */
const MAX_HEADCOUNT = 200;

/**
 * Whether this collective still owes a headcount.
 *
 * An entry attached from the registry carries the domain's floor of one, and one
 * person is not a collective — so the floor reads as "nobody has said yet". Rather
 * than seed the field with the group's minimum, which an applicant would accept
 * without reading, the number starts absent and has to be typed.
 */
export function headcountMissing(participant: Participant): boolean {
  return participant.memberCount <= 1;
}

/**
 * How many people this collective brings on stage.
 *
 * Its own field after the collective is chosen, not a box inside the picker: while
 * picking, the applicant is answering *who* performs, and a headcount asked in the
 * same breath got a default accepted without thought. Here it stands alone, empty,
 * next to the band the festival actually requires — which is what the number is
 * checked against, and what the price per participant is computed from.
 */
export function CollectiveHeadcount({
  submissionId,
  participant,
  bandLabel,
}: {
  submissionId: string;
  participant: Participant;
  /** The chosen group's count band ("6–12", "3+"), when a group is selected. */
  bandLabel?: string | null;
}): React.JSX.Element {
  const stated = headcountMissing(participant) ? null : participant.memberCount;
  const save = useSetParticipantMemberCount(submissionId);

  // Seeded from the entry and re-seeded when the stored number changes, but never
  // over a number being typed: every save on this submission echoes the whole thing
  // back, and adopting that echo mid-typing replaced what was in the field.
  const [text, setText] = useServerDraft(stated == null ? "" : String(stated), Object.is);

  const parsed = Number(text);
  const valid = Number.isInteger(parsed) && parsed >= 1 && parsed <= MAX_HEADCOUNT;
  const dirty = text.trim().length > 0 && valid && parsed !== stated;

  // Debounced, like every other field in the wizard: typing "12" passes through "1",
  // and saving that would quietly put a wrong number on the entry. Still pending when
  // the card is collapsed or the page left, it is sent rather than dropped.
  const { mutate } = save;
  const { schedule, cancel } = useAutosave<number>((memberCount) =>
    mutate(
      { participantId: participant.id, memberCount },
      { onError: () => toast.error("Не удалось сохранить численность коллектива") },
    ),
  );
  useEffect(() => {
    if (!dirty) {
      cancel();
      return;
    }
    schedule(parsed);
  }, [dirty, parsed, schedule, cancel]);

  const invalid = text.trim().length > 0 && !valid;
  const band = bandLabel ? ` Состав по правилам фестиваля — ${bandLabel} чел.` : "";
  // The field carries one message at a time (a description gives way to an error), so
  // the band travels with whichever one is showing — it is the number's whole point.
  const message = invalid
    ? `Укажите целое число от 1 до ${MAX_HEADCOUNT}.${band}`
    : stated == null
      ? `Укажите численность — без неё заявку не примут.${band}`
      : null;
  return (
    <Input
      type="number"
      min={1}
      max={MAX_HEADCOUNT}
      inputMode="numeric"
      className="max-w-40"
      required
      label="Сколько человек выступает"
      placeholder="Например, 12"
      description={`Численность коллектива: по ней проверяется состав и считается стоимость.${band}`}
      value={text}
      onChange={(event) => setText(event.target.value)}
      {...(message != null ? { error: message } : {})}
    />
  );
}
