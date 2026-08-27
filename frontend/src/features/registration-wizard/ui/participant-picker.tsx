import { UserPlus, Users } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import {
  isCollective,
  type Participant,
  participantDisplayName,
  useParticipants,
} from "@/entities/participant";
import { ROUTES } from "@/shared/config";
import {
  Avatar,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  EmptyState,
  Input,
  LoadingState,
} from "@/shared/ui";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("") || "?";
}

/**
 * A searchable picker over the user's Participant Registry, used by the wizard to
 * attach an existing solo participant or collective to a performance. It never
 * asks for participant details — those belong to the registry. Creating a new
 * registry entry reuses the existing participant page and returns to the wizard.
 */
export function ParticipantPicker({
  open,
  onOpenChange,
  onSelect,
  submissionId,
  returnTo,
  isAttaching,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (participant: Participant) => void;
  submissionId: string;
  returnTo: string;
  isAttaching?: boolean;
}): React.JSX.Element {
  const [search, setSearch] = useState("");
  const { data: participants, isLoading } = useParticipants(search);
  const navigate = useNavigate();

  const goCreate = (kind: "solo" | "collective") => {
    const params = new URLSearchParams({ returnTo, submissionId, kind });
    navigate(`${ROUTES.cabinetParticipantNew}?${params.toString()}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle>Выберите участника</DialogTitle>
          <DialogDescription>
            Участники берутся из вашего реестра — данные вводить повторно не нужно.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <Input
            leadingIcon={<Users className="size-4" />}
            placeholder="Поиск участников"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />

          <div className="flex max-h-80 flex-col gap-2 overflow-y-auto">
            {isLoading ? (
              <LoadingState label="Загружаем реестр…" size="sm" />
            ) : !participants || participants.length === 0 ? (
              <EmptyState
                title={search ? "Ничего не найдено" : "В реестре пока нет участников"}
                description={
                  search
                    ? "Измените запрос или создайте нового участника."
                    : "Создайте первого участника — он останется в реестре для будущих заявок."
                }
              />
            ) : (
              participants.map((participant) => (
                <ParticipantRow
                  key={participant.id}
                  participant={participant}
                  disabled={isAttaching ?? false}
                  onSelect={() => onSelect(participant)}
                />
              ))
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              leftIcon={<UserPlus className="size-4" />}
              onClick={() => goCreate("solo")}
            >
              Сохранить участника
            </Button>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Users className="size-4" />}
              onClick={() => goCreate("collective")}
            >
              Создать коллектив
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ParticipantRow({
  participant,
  onSelect,
  disabled,
}: {
  participant: Participant;
  onSelect: () => void;
  disabled?: boolean;
}): React.JSX.Element {
  const collective = isCollective(participant);
  const name = participantDisplayName(participant);
  const meta = collective ? "Коллектив" : `${participant.age} лет`;
  const organization = participant.primaryOrganization?.name;
  // Stacks on a phone: «Выбрать» cannot shrink, and on one row inside the dialog it
  // squeezed the name down to nothing — an avatar and a cut-off badge, nothing to pick by.
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
      <div className="flex min-w-0 items-center gap-3">
        <Avatar
          {...(participant.avatarUrl ? { src: participant.avatarUrl } : {})}
          alt={name}
          fallback={initials(name)}
        />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{name}</p>
          <p className="truncate text-xs text-muted-foreground">
            {meta}
            {organization ? ` · ${organization}` : ""}
          </p>
        </div>
      </div>
      {/* A collective is picked the same way as a solo participant: how many people it
          brings is asked once, in its own field on the entry, where the applicant can
          see the band the festival requires. */}
      <div className="flex shrink-0 items-center justify-end gap-2">
        <Button size="xs" disabled={disabled} onClick={onSelect}>
          Выбрать
        </Button>
      </div>
    </div>
  );
}
