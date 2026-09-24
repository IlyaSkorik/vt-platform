import { Copy, Mail, Plus, RotateCcw, Trash2, UserMinus } from "lucide-react";
import { useState } from "react";

import {
  JURY_STATUS_LABELS,
  type JuryMember,
  useInviteJuryMember,
  useJudgingSetup,
  useJury,
  useReinviteJuryMember,
  useRemoveJuryMember,
  useRevokeJuryMember,
  useUpdateJuryMember,
} from "@/features/judging";
import { ApiError } from "@/shared/api";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  IconButton,
  Input,
  LoadingState,
  toast,
} from "@/shared/ui";

import { useCompetitionPicker } from "./competition-picker";

/**
 * Состав жюри — who is on the panel and where they are in accepting.
 *
 * A jury member is *not* a user account: they are a named seat an organizer types into
 * the programme booklet weeks before anybody logs in, and an account gets attached when
 * the invitation is accepted. The screen shows both halves — the name as printed, and
 * whether there is somebody behind it yet — because an organizer needs to know on the
 * morning of the festival which of their five judges can actually open a tablet.
 *
 * Removing and revoking are two different things and both are offered. Revoking takes
 * the seat away but keeps the marks it gave, because those are what the jury decided;
 * removing is for the judge entered on the wrong festival.
 */

interface MemberFormState {
  fullName: string;
  email: string;
  title: string;
  isChair: boolean;
}

const EMPTY_FORM: MemberFormState = { fullName: "", email: "", title: "", isChair: false };

function statusVariant(member: JuryMember): "success" | "warning" | "secondary" {
  if (member.status === "ACTIVE") return "success";
  if (member.status === "INVITED") return "warning";
  return "secondary";
}

export function JuryMembersSection(): React.JSX.Element {
  const { competitionId, picker } = useCompetitionPicker();
  const setupQuery = useJudgingSetup(competitionId || undefined);
  const juryQuery = useJury(competitionId || undefined);

  const invite = useInviteJuryMember(competitionId);
  const update = useUpdateJuryMember(competitionId);
  const reinvite = useReinviteJuryMember(competitionId);
  const revoke = useRevokeJuryMember(competitionId);
  const remove = useRemoveJuryMember(competitionId);

  const [form, setForm] = useState<MemberFormState>(EMPTY_FORM);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<JuryMember | null>(null);
  const [removeTarget, setRemoveTarget] = useState<JuryMember | null>(null);

  const members = juryQuery.data ?? [];

  const handleInvite = async (): Promise<void> => {
    try {
      await invite.mutateAsync({
        competitionId,
        fullName: form.fullName.trim(),
        email: form.email.trim(),
        title: form.title.trim() || null,
        isChair: form.isChair,
        categoryIds: [],
      });
      toast.success("Приглашение отправлено");
      setForm(EMPTY_FORM);
      setAdding(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось пригласить");
    }
  };

  const handleUpdate = async (): Promise<void> => {
    if (editing == null) return;
    try {
      await update.mutateAsync({
        memberId: editing.id,
        fullName: form.fullName.trim(),
        email: form.email.trim(),
        title: form.title.trim() || null,
        isChair: form.isChair,
      });
      toast.success("Сохранено");
      setEditing(null);
      setForm(EMPTY_FORM);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить");
    }
  };

  const copyInvitation = (member: JuryMember): void => {
    if (member.invitationPath == null) return;
    void navigator.clipboard.writeText(`${window.location.origin}${member.invitationPath}`);
    toast.success("Ссылка-приглашение скопирована");
  };

  if (competitionId === "") {
    return <div className="space-y-4">{picker}</div>;
  }

  const setup = setupQuery.data;

  return (
    <div className="space-y-4">
      {picker}

      {setup != null && !setup.onlineJudging ? (
        <Alert variant="info" title="Онлайн-судейство выключено">
          Состав жюри можно заполнить заранее — например, для программки. Но оценки на платформе
          появятся, только когда в настройках фестиваля выбран режим онлайн-судейства.
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">
          {members.length === 0 ? "Жюри ещё не собрано" : `Человек в жюри: ${members.length}`}
        </p>
        <Button
          type="button"
          onClick={() => {
            setForm(EMPTY_FORM);
            setAdding(true);
          }}
        >
          <Plus className="size-4" aria-hidden="true" />
          Пригласить в жюри
        </Button>
      </div>

      {juryQuery.isLoading ? (
        <LoadingState label="Загружаем состав жюри…" />
      ) : members.length === 0 ? (
        <EmptyState
          title="В жюри пока никого нет"
          description="Пригласите судей по почте: каждый получит одноразовую ссылку, зарегистрируется и сможет выставлять оценки со своего устройства."
        />
      ) : (
        <ul className="space-y-2" aria-label="Состав жюри">
          {members.map((member) => (
            <li key={member.id}>
              <Card className="shadow-none">
                <CardContent className="flex flex-wrap items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="flex flex-wrap items-center gap-2 font-medium text-sm">
                      {member.fullName}
                      {member.isChair ? <Badge variant="secondary">председатель</Badge> : null}
                      <Badge variant={statusVariant(member)}>
                        {JURY_STATUS_LABELS[member.status]}
                      </Badge>
                    </p>
                    <p className="truncate text-muted-foreground text-xs">
                      {member.email}
                      {member.title != null ? ` · ${member.title}` : ""}
                    </p>
                    <p className="text-muted-foreground text-xs">
                      {member.categoryNames.length === 0
                        ? "Судит все жанры"
                        : `Жанры: ${member.categoryNames.join(", ")}`}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-1">
                    {member.invitationPath != null ? (
                      <IconButton
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label="Скопировать ссылку-приглашение"
                        onClick={() => copyInvitation(member)}
                        icon={<Copy className="size-4" aria-hidden="true" />}
                      />
                    ) : null}
                    {member.status !== "ACTIVE" ? (
                      <IconButton
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label="Отправить приглашение заново"
                        disabled={reinvite.isPending}
                        onClick={() => {
                          void reinvite
                            .mutateAsync(member.id)
                            .then(() => toast.success("Приглашение отправлено заново"))
                            .catch((error: unknown) =>
                              toast.error(
                                error instanceof ApiError
                                  ? error.message
                                  : "Не удалось отправить приглашение",
                              ),
                            );
                        }}
                        icon={<RotateCcw className="size-4" aria-hidden="true" />}
                      />
                    ) : null}
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setEditing(member);
                        setForm({
                          fullName: member.fullName,
                          email: member.email,
                          title: member.title ?? "",
                          isChair: member.isChair,
                        });
                      }}
                    >
                      Изменить
                    </Button>
                    {member.status === "ACTIVE" ? (
                      <IconButton
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label="Отозвать из жюри"
                        disabled={revoke.isPending}
                        onClick={() => {
                          void revoke
                            .mutateAsync(member.id)
                            .then(() => toast.success("Член жюри отозван"))
                            .catch((error: unknown) =>
                              toast.error(
                                error instanceof ApiError ? error.message : "Не удалось отозвать",
                              ),
                            );
                        }}
                        icon={<UserMinus className="size-4" aria-hidden="true" />}
                      />
                    ) : null}
                    <IconButton
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label="Убрать из состава"
                      onClick={() => setRemoveTarget(member)}
                      icon={<Trash2 className="size-4 text-destructive" aria-hidden="true" />}
                    />
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <Dialog
        open={adding || editing != null}
        onOpenChange={(open) => {
          if (!open) {
            setAdding(false);
            setEditing(null);
            setForm(EMPTY_FORM);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing != null ? "Член жюри" : "Пригласить в жюри"}</DialogTitle>
            <DialogDescription>
              {editing != null
                ? "Изменение почты у ещё не принявшего приглашение судьи отправит ссылку заново."
                : "Судья получит письмо с одноразовой ссылкой. Открыв её, он войдёт или зарегистрируется — и попадёт в состав жюри."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <Input
              label="ФИО"
              placeholder="Иванова Анна Сергеевна"
              value={form.fullName}
              onChange={(event) => setForm({ ...form, fullName: event.target.value })}
            />
            <Input
              label="Почта"
              type="email"
              placeholder="jury@example.ru"
              leadingIcon={<Mail aria-hidden="true" />}
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
            <Input
              label="Регалии"
              description="Как написать в программке: «Заслуженный артист России»."
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
            <Checkbox
              label="Председатель жюри"
              checked={form.isChair}
              onCheckedChange={(next) => setForm({ ...form, isChair: Boolean(next) })}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setAdding(false);
                setEditing(null);
                setForm(EMPTY_FORM);
              }}
            >
              Отмена
            </Button>
            <Button
              type="button"
              loading={invite.isPending || update.isPending}
              onClick={() => void (editing != null ? handleUpdate() : handleInvite())}
            >
              {editing != null ? "Сохранить" : "Пригласить"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={removeTarget != null} onOpenChange={(open) => !open && setRemoveTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Убрать из состава жюри?</DialogTitle>
            <DialogDescription>
              {removeTarget != null
                ? `«${removeTarget.fullName}» пропадёт из состава. Уже выставленные им оценки останутся — они часть решения жюри.`
                : ""}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setRemoveTarget(null)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={remove.isPending}
              onClick={() => {
                if (removeTarget == null) return;
                void remove
                  .mutateAsync(removeTarget.id)
                  .then(() => {
                    toast.success("Убран из состава");
                    setRemoveTarget(null);
                  })
                  .catch((error: unknown) =>
                    toast.error(error instanceof ApiError ? error.message : "Не удалось убрать"),
                  );
              }}
            >
              Убрать
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
