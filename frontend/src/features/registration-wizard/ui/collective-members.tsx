import { useEffect, useState } from "react";

import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import { useServerDraft } from "@/shared/hooks";
import { Alert, Button, Switch, Textarea, toast } from "@/shared/ui";

import { useSetParticipantMembers } from "../api/hooks";

/** Mirrors the backend bounds on one roster (`_MAX_COLLECTIVE_MEMBERS` / name length). */
const MAX_MEMBERS = 200;
const MAX_NAME_LENGTH = 200;

type Participant = SubmissionResource["participants"][number];

/**
 * One ФИО per line — the roster as the applicant actually holds it.
 *
 * A textarea rather than a row of inputs per person: an ensemble roster arrives as a
 * list from a teacher, and pasting twenty lines in one go is the whole difference
 * between filling this in and not bothering. Blank lines are dropped on save, so the
 * applicant can format the list however they like.
 */
function parseRoster(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim().replace(/\s+/g, " "))
    .filter((line) => line.length > 0);
}

/**
 * Whether this participant is a collective — the only kind that can have a roster.
 *
 * A collective carries a headcount above one, or no structured person data at all
 * (the submission stores a solo's birth date and a collective's nothing). Either
 * signal is enough; a solo participant is already named on their own diploma, so
 * offering them an "individual diploma" would mean a second copy of the same sheet.
 */
export function isCollectiveEntry(participant: Participant): boolean {
  return participant.memberCount > 1 || participant.birthDate == null;
}

/**
 * The optional roster of a collective, and with it the request for individual diplomas.
 *
 * Naming the people **is** the request — there is no separate flag on the entry, so the
 * switch here only reveals the field. An applicant who wants nothing but the ensemble's
 * own diploma leaves it alone; one who fills it in gets a diploma per person in the
 * cabinet once the protocol is published, alongside the collective's.
 */
export function CollectiveMembers({
  submissionId,
  participant,
}: {
  submissionId: string;
  participant: Participant;
}): React.JSX.Element {
  const saved = participant.members ?? [];
  const [wanted, setWanted] = useState(saved.length > 0);
  const save = useSetParticipantMembers(submissionId);

  // Seeded from the stored roster and re-seeded when that roster changes, but never
  // over a list being typed. A refetch hands back a new array on every save made
  // anywhere on this submission, and adopting it used to replace the names being
  // entered — mid-paste, mid-line — with whatever the server still held.
  const [text, setText] = useServerDraft(saved.join("\n"), Object.is);
  useEffect(() => {
    // Names arriving from elsewhere reveal the field; the applicant's own switch is
    // never forced back on, so turning it off stays off.
    setWanted((on) => on || (participant.members ?? []).length > 0);
  }, [participant.members]);

  const roster = parseRoster(text);
  const tooLong = roster.find((name) => name.length > MAX_NAME_LENGTH);
  const dirty = roster.join("\n") !== saved.join("\n");

  const persist = (members: string[]) => {
    save.mutate(
      { participantId: participant.id, members },
      {
        onSuccess: () =>
          toast.success(
            members.length > 0
              ? `Состав сохранён: ${members.length} чел.`
              : "Индивидуальные дипломы отключены",
          ),
        onError: () => toast.error("Не удалось сохранить состав коллектива"),
      },
    );
  };

  const toggle = (on: boolean) => {
    setWanted(on);
    // Turning it off withdraws the request, which only means anything if names were
    // already saved — otherwise there is nothing to tell the server.
    if (!on && saved.length > 0) {
      setText("");
      persist([]);
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-muted/20 p-3">
      <Switch
        checked={wanted}
        onCheckedChange={toggle}
        disabled={save.isPending}
        label="Индивидуальные дипломы участникам"
        description="Кроме диплома на коллектив каждый названный участник получит свой диплом в личном кабинете — после публикации протокола."
      />

      {wanted ? (
        <>
          <Textarea
            rows={Math.min(12, Math.max(4, roster.length + 2))}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder={"Иванова Мария Петровна\nПетров Пётр Петрович"}
            label="ФИО участников коллектива"
            description="По одному ФИО в строке — список можно вставить целиком. Пустые строки не сохраняются."
            {...(tooLong
              ? { error: `Слишком длинное ФИО: не больше ${MAX_NAME_LENGTH} символов.` }
              : {})}
          />

          {roster.length > MAX_MEMBERS ? (
            <Alert variant="warning">
              Можно указать не больше {MAX_MEMBERS} участников; сейчас {roster.length}.
            </Alert>
          ) : roster.length > 0 && roster.length !== participant.memberCount ? (
            <Alert variant="info">
              Указано {roster.length} из {participant.memberCount} участников состава. Дипломы
              получат только названные.
            </Alert>
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button
              size="sm"
              loading={save.isPending}
              disabled={!dirty || tooLong != null || roster.length > MAX_MEMBERS}
              onClick={() => persist(roster)}
            >
              Сохранить состав
            </Button>
            <span className="text-muted-foreground text-xs">
              {dirty ? `Будет сохранено: ${roster.length} чел.` : `Сохранено: ${saved.length} чел.`}
            </span>
          </div>
        </>
      ) : null}
    </div>
  );
}
