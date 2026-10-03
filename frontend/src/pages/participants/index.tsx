import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArrowLeft, Building2, Medal, Plus, Search, Trash2, UserPen } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import {
  fetchOrganizations,
  fetchParticipant,
  fetchParticipants,
  type Gender,
  type Organization,
  type OrganizationType,
  type Participant,
  type ParticipantType,
  participantRegistryKeys,
  uploadParticipantAvatar,
} from "@/entities/participant";
import { type ApiError, apiClient, toApiError } from "@/shared/api";
import { recordOwnConsent } from "@/shared/api/generated/identity/identity";
import { ROUTES } from "@/shared/config";
import { ConsentCheckbox, participantConsent } from "@/shared/consents";
import { useAutosave, useMediaQuery } from "@/shared/hooks";
import { cn, formatPersonName } from "@/shared/lib";
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Checkbox,
  DatePicker,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  EmptyState,
  IconButton,
  Input,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Select,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
  toast,
} from "@/shared/ui";

interface ParticipantFormValues {
  participantType: ParticipantType;
  collectiveName: string;
  firstName: string;
  lastName: string;
  middleName: string;
  birthDate: string;
  gender: Gender;
  avatarUrl: string;
  notes: string;
  organizations: { organizationId: string; isPrimary: boolean }[];
}

interface OrganizationFormValues {
  name: string;
  type: OrganizationType;
  country: string;
  city: string;
  address: string;
  website: string;
}

/** Long enough that typing a name is one save, short enough to feel automatic. */
const AUTOSAVE_DELAY_MS = 800;

/** An untouched organization form — what «добавить» starts from and what a save returns to. */
const BLANK_ORGANIZATION: OrganizationFormValues = {
  name: "",
  type: "school",
  country: "",
  city: "",
  address: "",
  website: "",
};

/** The width at which the directory shows its list and its form side by side. */
const DIRECTORY_SIDE_BY_SIDE = "(min-width: 1024px)";

const genderOptions = [
  { value: "female", label: "Женский" },
  { value: "male", label: "Мужской" },
  { value: "other", label: "Другой" },
] as const;

const participantTypeOptions = [
  { value: "solo", label: "Сольный участник" },
  { value: "collective", label: "Коллектив" },
] as const;

const organizationTypeOptions: Array<{ value: OrganizationType; label: string }> = [
  { value: "school", label: "Школа" },
  { value: "music_school", label: "Музыкальная школа" },
  { value: "dance_studio", label: "Танцевальная студия" },
  { value: "art_school", label: "Художественная школа" },
  { value: "college", label: "Колледж" },
  { value: "university", label: "Университет" },
  { value: "cultural_center", label: "Культурный центр" },
  { value: "creative_center", label: "Творческий центр" },
  { value: "private_studio", label: "Частная студия" },
  { value: "other", label: "Другое" },
];

function initialsFromName(fullName: string): string {
  const parts = fullName
    .split(" ")
    .map((part) => part.trim())
    .filter(Boolean);
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("ru-RU", { day: "2-digit", month: "long", year: "numeric" });
}

function toRelativeTime(value: string): string {
  const date = new Date(value);
  const diffMs = Date.now() - date.getTime();
  if (Number.isNaN(diffMs)) {
    return "—";
  }
  const diffHours = Math.floor(diffMs / 3_600_000);
  if (diffHours < 1) {
    return "только что";
  }
  if (diffHours < 24) {
    return `${diffHours} ч назад`;
  }
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} д назад`;
}

/**
 * Pick an avatar, upload it, keep the reference the server hands back.
 *
 * The picture used to be read with `FileReader` and put into the form as a base64
 * `data:` URL, so it travelled inside the participant payload and was stored in a
 * database column. Here the file goes to its own endpoint and the form carries a
 * URL — which is what every other file on the platform does.
 *
 * The upload runs on selection rather than on submit: it is the slow part, and a
 * failure (too large, not really an image) should be reported while the person is
 * still looking at the field, not after they press save.
 */
function AvatarField({
  value,
  onChange,
}: {
  value: string;
  onChange: (url: string) => void;
}): React.JSX.Element {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pick = async (event: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
    const file = event.target.files?.[0];
    if (file == null) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      onChange(await uploadParticipantAvatar(file));
    } catch (caught) {
      // The server's own message names what to do about it ("не более 8 МБ",
      // "допустимы только JPEG…"), so it beats anything phrased here.
      setError((caught as ApiError)?.message ?? "Не удалось загрузить изображение");
      // Clear the input so picking the *same* file again still fires a change.
      event.target.value = "";
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="space-y-2">
      <Input
        label="Аватар (необязательно)"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        disabled={pending}
        onChange={pick}
        {...(error != null ? { error } : {})}
      />
      {pending ? <p className="text-muted-foreground text-xs">Загрузка…</p> : null}
      {!pending && error == null && value.length > 0 ? (
        <div className="flex items-center gap-2">
          <Avatar size="sm" src={value} alt="" />
          <span className="text-muted-foreground text-xs">Изображение загружено</span>
        </div>
      ) : null}
    </div>
  );
}

function buildFilterParams(filters: {
  q: string;
  organizationId: string;
  city: string;
  gender: string;
  archived: "all" | "true" | "false";
  ageMin: string;
  ageMax: string;
}): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q.trim().length > 0) {
    params.set("q", filters.q.trim());
  }
  if (filters.organizationId.length > 0) {
    params.set("organizationId", filters.organizationId);
  }
  if (filters.city.trim().length > 0) {
    params.set("city", filters.city.trim());
  }
  if (filters.gender.length > 0) {
    params.set("gender", filters.gender);
  }
  if (filters.archived !== "all") {
    params.set("archived", filters.archived);
  }
  if (filters.ageMin.length > 0) {
    params.set("ageMin", filters.ageMin);
  }
  if (filters.ageMax.length > 0) {
    params.set("ageMax", filters.ageMax);
  }
  return params;
}

function toPayload(values: ParticipantFormValues) {
  const isCollective = values.participantType === "collective";
  return {
    participantType: values.participantType,
    collectiveName: values.collectiveName.trim() || null,
    firstName: values.firstName.trim(),
    lastName: values.lastName.trim(),
    middleName: values.middleName.trim() || null,
    birthDate: isCollective ? null : values.birthDate,
    gender: isCollective ? null : values.gender,
    avatarUrl: values.avatarUrl.trim() || null,
    notes: values.notes.trim(),
    organizations: values.organizations,
  };
}

export function ParticipantsPage(): React.JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    q: "",
    organizationId: "",
    city: "",
    gender: "",
    archived: "all" as "all" | "true" | "false",
    ageMin: "",
    ageMax: "",
  });
  const [organizationDialogOpen, setOrganizationDialogOpen] = useState(false);
  const params = useMemo(() => buildFilterParams(filters), [filters]);

  const participantsQuery = useQuery<Participant[], ApiError>({
    queryKey: participantRegistryKeys.participants(params),
    queryFn: () => fetchParticipants(params),
  });

  const archiveParticipant = useMutation({
    mutationFn: async (participantId: string) =>
      apiClient.post(`participants/registry/${participantId}/archive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["participant-registry"] });
    },
  });

  const deleteParticipant = useMutation({
    mutationFn: async (participantId: string) =>
      apiClient.delete(`participants/registry/${participantId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["participant-registry"] });
      toast.success("Участник удален");
    },
  });

  const noFiltersActive = Object.values(filters).every(
    (value) => value.length === 0 || value === "all",
  );
  const participants = participantsQuery.data ?? [];

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Мои участники</PageTitle>
        <PageDescription>
          Личный реестр для повторного использования участников в неограниченном количестве заявок.
        </PageDescription>
      </PageHeader>
      <PageContent className="space-y-4">
        <Card>
          <CardContent className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
            <Input
              value={filters.q}
              onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))}
              placeholder="Поиск: имя, организация, город"
              className="w-full"
              leadingIcon={<Search aria-hidden="true" />}
            />
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center sm:justify-end">
              <Button
                className="w-full sm:w-auto"
                variant="outline"
                onClick={() => setOrganizationDialogOpen(true)}
              >
                Справочник организаций
              </Button>
              <Button
                className="w-full sm:w-auto"
                onClick={() => navigate(ROUTES.cabinetParticipantNew)}
              >
                <Plus aria-hidden="true" /> Добавить участника
              </Button>
            </div>
          </CardContent>
        </Card>

        {participantsQuery.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
            <Skeleton className="h-64" />
            <Skeleton className="h-64" />
            <Skeleton className="h-64" />
          </div>
        ) : participantsQuery.isError ? (
          <EmptyState
            title="Не удалось загрузить участников"
            description={participantsQuery.error.message}
            action={
              <Button variant="outline" onClick={() => participantsQuery.refetch()}>
                Повторить
              </Button>
            }
          />
        ) : participants.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
            {participants.map((participant) => (
              <Card key={participant.id} className="group min-w-0">
                <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
                  <div className="flex min-w-0 items-center gap-3">
                    <Avatar
                      size="lg"
                      {...(participant.avatarUrl ? { src: participant.avatarUrl } : {})}
                      fallback={initialsFromName(participant.fullName)}
                    />
                    <div className="min-w-0">
                      <CardTitle className="truncate text-base" title={participant.fullName}>
                        {participant.fullName}
                      </CardTitle>
                      {participant.participantType === "collective" ? (
                        <CardDescription>Коллектив</CardDescription>
                      ) : (
                        <CardDescription>
                          {participant.age} лет · {formatDate(participant.birthDate)}
                        </CardDescription>
                      )}
                    </div>
                  </div>
                  <Badge
                    className="shrink-0"
                    variant={participant.archived ? "outline" : "primary"}
                  >
                    {participant.participantType === "collective" ? "Коллектив" : "Соло"}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <p className="break-words">
                    <span className="text-muted-foreground">Основная организация:</span>{" "}
                    {participant.primaryOrganization?.name ?? "Не выбрана"}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Подано заявок:</span>{" "}
                    {participant.applicationsCount}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Статус:</span>{" "}
                    {participant.archived ? "В архиве" : "Активен"}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Обновлен:</span>{" "}
                    {toRelativeTime(participant.updatedAt)}
                  </p>
                  <div className="flex min-w-0 flex-wrap gap-2">
                    {participant.organizations.map((organization) => (
                      <Badge
                        key={organization.id}
                        variant={organization.isPrimary ? "primary" : "secondary"}
                        title={organization.name}
                      >
                        {organization.isPrimary ? "✓ " : ""}
                        {organization.name}
                      </Badge>
                    ))}
                  </div>
                  <div className="rounded-md border border-dashed p-3 text-muted-foreground text-xs">
                    <div className="mb-1 flex items-center gap-1 font-medium">
                      <Medal className="size-3.5" /> Достижения
                    </div>
                    Раздел подготовлен для будущих релизов.
                  </div>
                </CardContent>
                <CardFooter className="flex justify-end gap-2">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <IconButton
                          variant="outline"
                          size="sm"
                          aria-label="Редактировать"
                          onClick={() =>
                            navigate(`${ROUTES.cabinetParticipants}/${participant.id}`)
                          }
                          icon={<UserPen aria-hidden="true" />}
                        />
                      </TooltipTrigger>
                      <TooltipContent>Редактировать</TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <IconButton
                          variant="outline"
                          size="sm"
                          aria-label={participant.archived ? "Разархивировать" : "В архив"}
                          onClick={() => archiveParticipant.mutate(participant.id)}
                          icon={<Archive aria-hidden="true" />}
                        />
                      </TooltipTrigger>
                      <TooltipContent>
                        {participant.archived ? "Разархивировать" : "В архив"}
                      </TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <IconButton
                          variant="danger"
                          size="sm"
                          aria-label="Удалить"
                          onClick={() => deleteParticipant.mutate(participant.id)}
                          icon={<Trash2 aria-hidden="true" />}
                        />
                      </TooltipTrigger>
                      <TooltipContent>Удалить</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </CardFooter>
              </Card>
            ))}
          </div>
        ) : noFiltersActive ? (
          <EmptyState
            title="Пока нет участников"
            description="Создайте первого участника, чтобы больше не заполнять одинаковые данные заново."
            action={
              <Button onClick={() => navigate(ROUTES.cabinetParticipantNew)}>
                Создать первого участника
              </Button>
            }
          />
        ) : (
          <EmptyState
            title="Ничего не найдено"
            description="Измените условия поиска или очистите фильтры."
            action={
              <Button
                variant="outline"
                onClick={() =>
                  setFilters({
                    q: "",
                    organizationId: "",
                    city: "",
                    gender: "",
                    archived: "all",
                    ageMin: "",
                    ageMax: "",
                  })
                }
              >
                Сбросить фильтры
              </Button>
            }
          />
        )}
      </PageContent>

      <OrganizationDirectoryDialog
        open={organizationDialogOpen}
        onOpenChange={setOrganizationDialogOpen}
      />
    </PageContainer>
  );
}

export function ParticipantsProfilePage(): React.JSX.Element {
  const { participantId } = useParams<{ participantId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [organizationDialogOpen, setOrganizationDialogOpen] = useState(false);
  const isCreateMode = participantId === "new" || participantId == null;
  // Which consent was ticked, rather than whether one was. The wording depends on the
  // participant's age, so editing the birth date across the eighteenth birthday changes
  // the question being asked — and storing the code makes the old answer stop counting
  // by itself, instead of carrying a tick from a text that is no longer on screen.
  const [acceptedConsentCode, setAcceptedConsentCode] = useState<string | null>(null);
  const [consentMissing, setConsentMissing] = useState(false);
  // The last catch for the organization nobody ticked. Set on the first press of
  // «Создать участника», cleared by the fact rather than by hand: pick one and the
  // warning has nothing left to warn about.
  const [organizationWarningShown, setOrganizationWarningShown] = useState(false);
  // Creating a participant reads as a form with tabs, and the tab that finishes it is
  // not the one it opens on: people filled in the name, found no button under it and
  // stopped there. So creation is walked through — «Далее» carries them to the step
  // that holds the consent and the button that actually creates the participant.
  const [createStep, setCreateStep] = useState("general");

  // When the Registration Wizard sends the user here to create a participant, it
  // passes where to return and which submission to attach the result to.
  const returnTo = searchParams.get("returnTo");
  const returnSubmissionId = searchParams.get("submissionId");
  const createKind = searchParams.get("kind");

  const participantQuery = useQuery<Participant, ApiError>({
    enabled: !isCreateMode && participantId != null,
    queryKey: participantRegistryKeys.participant(participantId ?? ""),
    queryFn: () => fetchParticipant(participantId ?? ""),
  });
  const organizationsQuery = useQuery<Organization[], ApiError>({
    queryKey: participantRegistryKeys.organizations,
    queryFn: () => fetchOrganizations(false),
  });

  const form = useForm<ParticipantFormValues>({
    defaultValues: {
      participantType: createKind === "collective" ? "collective" : "solo",
      collectiveName: "",
      firstName: "",
      lastName: "",
      middleName: "",
      birthDate: "",
      gender: "female",
      avatarUrl: "",
      notes: "",
      organizations: [],
    },
  });

  /**
   * Registers one part of a person's ФИО, tidying its capitalisation on blur.
   *
   * On blur rather than on every keystroke, so the value never shifts under a
   * caret mid-word. Only the three person fields go through here — a
   * collective's name is registered plainly and keeps whatever case its author
   * chose.
   */
  const registerName = (
    field: "firstName" | "lastName" | "middleName",
    options?: { required: string },
  ) =>
    form.register(field, {
      ...options,
      onBlur: () => {
        const current = form.getValues(field);
        const formatted = formatPersonName(current);
        if (formatted !== current) {
          form.setValue(field, formatted, { shouldDirty: true, shouldValidate: true });
        }
      },
    });

  /**
   * Whose profile the form currently holds, and whether it holds unsaved typing.
   *
   * Autosaving invalidates the registry, which refetches this very participant and
   * hands back a new object — and resetting the form to it threw away everything
   * entered while the request was on the wire. So the record seeds the form and is
   * adopted again only into a form with nothing unsaved in it; switching to another
   * participant always reloads, dirty or not, since that is a different person.
   */
  const syncedParticipantId = useRef<string | null>(null);
  const isDirtyRef = useRef(false);
  isDirtyRef.current = form.formState.isDirty;
  // Written further down, once `updateMutation` exists; read only from the effect
  // below, which runs after the whole render.
  const isSavingRef = useRef(false);

  useEffect(() => {
    const participant = participantQuery.data;
    if (participant == null) {
      return;
    }
    const isSamePerson = syncedParticipantId.current === participant.id;
    if (isSamePerson && (isDirtyRef.current || isSavingRef.current)) {
      return;
    }
    syncedParticipantId.current = participant.id;
    form.reset({
      participantType: participant.participantType,
      collectiveName: participant.collectiveName ?? "",
      firstName: participant.firstName,
      lastName: participant.lastName,
      middleName: participant.middleName ?? "",
      birthDate: participant.birthDate,
      gender: participant.gender,
      avatarUrl: participant.avatarUrl ?? "",
      notes: participant.notes,
      organizations: participant.organizations.map((organization) => ({
        organizationId: organization.id,
        isPrimary: organization.isPrimary,
      })),
    });
  }, [participantQuery.data, form]);

  const createMutation = useMutation({
    mutationFn: async (values: ParticipantFormValues): Promise<string> => {
      // The journal entry comes first, and its id travels with the participant: the
      // record the platform reads and the evidence that permits it are then the same
      // fact, rather than two rows that happen to agree (LEGAL-001 §6.3, §13.3).
      // Creation is refused server-side without it, so an interrupted flow leaves
      // nobody on file. The basis is read from the values being submitted, not from
      // what the form last rendered — the server derives the same one from the same
      // birth date and rejects the mismatch.
      const definition = participantConsent(values);
      const consent = await recordOwnConsent({
        consentType: definition.code,
        version: definition.version,
      });
      if (consent.status !== 201) {
        throw new Error("Не удалось записать согласие на обработку данных участника.");
      }
      const consentId = consent.data.data[0]?.id;
      const response = await apiClient.post("participants/registry", {
        json: {
          ...toPayload(values),
          consentId,
          consentVersion: definition.version,
        },
      });
      const payload = (await response.json()) as { data: { id: string } };
      return payload.data.id;
    },
    onSuccess: (createdId) => {
      queryClient.invalidateQueries({ queryKey: ["participant-registry"] });
      toast.success("Участник создан");
      if (returnTo && returnSubmissionId) {
        // Return to the wizard, which auto-selects the freshly created participant.
        const params = new URLSearchParams({
          pickedParticipantId: createdId,
          submissionId: returnSubmissionId,
        });
        navigate(`${returnTo}?${params.toString()}`);
        return;
      }
      navigate(ROUTES.cabinetParticipants);
    },
    onError: async (error) => {
      toast.error((await toApiError(error)).message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (values: ParticipantFormValues) => {
      if (participantId == null) {
        return;
      }
      await apiClient.patch(`participants/registry/${participantId}`, { json: toPayload(values) });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["participant-registry"] });
      toast.success("Изменения сохранены");
    },
    onError: async (error) => {
      toast.error((await toApiError(error)).message);
    },
  });

  isSavingRef.current = updateMutation.isPending;

  // Debounced so typing is one save, and flushed when the page is left: the timer used
  // to be cleared on the way out, so the last thing typed before going back to the list
  // was never sent and the profile reopened without it.
  const { mutate: saveParticipant } = updateMutation;
  const { schedule: scheduleAutosave } = useAutosave<ParticipantFormValues>(
    (payload) => saveParticipant(payload),
    AUTOSAVE_DELAY_MS,
  );
  const values = form.watch();
  useEffect(() => {
    if (isCreateMode || !form.formState.isDirty || participantId == null) {
      return;
    }
    scheduleAutosave(values);
  }, [form.formState.isDirty, isCreateMode, participantId, scheduleAutosave, values]);

  const participant = participantQuery.data;
  const selectedOrganizations = form.watch("organizations");
  // Derived from the live form values, so the checkbox below re-reads the birth date as
  // it is typed. `values` is already a `form.watch()` of everything, so this costs a
  // comparison on a render that was happening anyway.
  const activeConsent = participantConsent(values);
  const consentGiven = acceptedConsentCode === activeConsent.code;
  // Only worth asking about when there was something to pick: an empty directory makes
  // «вы не выбрали организацию» a reproach for a step that does not exist yet.
  const organizationMissing =
    (organizationsQuery.data ?? []).length > 0 && selectedOrganizations.length === 0;

  /** What the first step is answering: who this is. A collective is named, a person is named and dated. */
  const identityFields = (): Array<"collectiveName" | "firstName" | "lastName" | "birthDate"> =>
    form.getValues("participantType") === "collective"
      ? ["collectiveName"]
      : ["firstName", "lastName", "birthDate"];

  const goToFinalStep = async (): Promise<void> => {
    // Checked here rather than at the end: a missing name is a mistake on the step the
    // applicant is looking at, and finding it out two tabs later is how a form loses people.
    if (!(await form.trigger(identityFields()))) {
      return;
    }
    setCreateStep("organizations");
  };

  return (
    <PageContainer size="wide">
      <PageHeader>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to={ROUTES.cabinetParticipants}>
              <ArrowLeft aria-hidden="true" /> К списку участников
            </Link>
          </Button>
        </div>
        <PageTitle>
          {isCreateMode ? "Новый участник" : (participant?.fullName ?? "Профиль участника")}
        </PageTitle>
        <PageDescription>
          {isCreateMode
            ? "Сначала — кто участвует, затем — организация (по желанию) и согласие на обработку данных."
            : "Изменения сохраняются автоматически. Профиль принадлежит вашему личному реестру."}
        </PageDescription>
      </PageHeader>

      <PageContent>
        {isCreateMode ? (
          <Tabs value={createStep} onValueChange={setCreateStep} className="space-y-4">
            <TabsList className="w-full justify-start overflow-x-auto">
              <TabsTrigger value="general">Кто участвует</TabsTrigger>
              {/* Named after what finishes creation rather than after the picker it
                  opens with: this is the step people could not find. */}
              <TabsTrigger value="organizations">Организация и согласие</TabsTrigger>
              <TabsTrigger value="history">История</TabsTrigger>
              <TabsTrigger value="notes">Заметки</TabsTrigger>
            </TabsList>
            <TabsContent value="general">
              <Card>
                <CardContent className="grid gap-3 p-4 md:grid-cols-2">
                  <div className="md:col-span-2">
                    <Select
                      label="Тип участника"
                      value={form.watch("participantType")}
                      onValueChange={(value) =>
                        form.setValue("participantType", value as ParticipantType)
                      }
                      options={participantTypeOptions.map((option) => ({
                        value: option.value,
                        label: option.label,
                      }))}
                    />
                  </div>
                  {form.watch("participantType") === "collective" ? (
                    <div className="grid gap-3 md:col-span-2 md:grid-cols-2">
                      <Input
                        label="Название коллектива"
                        required
                        error={form.formState.errors.collectiveName?.message}
                        {...form.register("collectiveName", {
                          required: "Укажите название коллектива",
                        })}
                      />
                      <AvatarField
                        value={form.watch("avatarUrl")}
                        onChange={(url) => form.setValue("avatarUrl", url, { shouldDirty: true })}
                      />
                    </div>
                  ) : (
                    <>
                      {/* Фамилия первой — как в реестре, в карточке организатора, в
                          форме педагога и на каждом печатаемом документе. Раньше
                          здесь было наоборот, и человек, заводивший участника и
                          следом педагога, видел в одной и той же клетке экрана то
                          «Имя», то «Фамилия» — и вписывал фамилию в имя. */}
                      <Input
                        label="Фамилия"
                        required
                        error={form.formState.errors.lastName?.message}
                        {...registerName("lastName", { required: "Укажите фамилию" })}
                      />
                      <Input
                        label="Имя"
                        required
                        error={form.formState.errors.firstName?.message}
                        {...registerName("firstName", { required: "Укажите имя" })}
                      />
                      <Input label="Отчество" {...registerName("middleName")} />
                      {/* `Controller`, not `setValue`: the picker is not an input the
                          form can register, and without this the "укажите дату
                          рождения" rule would quietly stop being enforced. */}
                      <Controller
                        control={form.control}
                        name="birthDate"
                        rules={{ required: "Укажите дату рождения" }}
                        render={({ field }) => (
                          <DatePicker
                            label="Дата рождения"
                            required
                            // The year dropdown is what makes this workable: a child's
                            // birth year is a decade back, and nobody should page
                            // through a hundred and thirty months to reach it.
                            toYear={new Date().getFullYear()}
                            value={field.value}
                            onChange={field.onChange}
                            {...(form.formState.errors.birthDate?.message != null
                              ? { error: form.formState.errors.birthDate.message }
                              : {})}
                          />
                        )}
                      />
                      <Select
                        label="Пол"
                        required
                        value={form.watch("gender")}
                        onValueChange={(value) => form.setValue("gender", value as Gender)}
                        options={genderOptions.map((option) => ({
                          value: option.value,
                          label: option.label,
                        }))}
                      />
                      <AvatarField
                        value={form.watch("avatarUrl")}
                        onChange={(url) => form.setValue("avatarUrl", url, { shouldDirty: true })}
                      />
                    </>
                  )}
                </CardContent>
                <CardFooter className="justify-end">
                  <Button onClick={() => void goToFinalStep()}>Далее</Button>
                </CardFooter>
              </Card>
            </TabsContent>
            <TabsContent value="organizations">
              <Card>
                <CardHeader>
                  <CardTitle>Организации участника</CardTitle>
                  <CardDescription>
                    По желанию: школа или студия, которую участник представляет — её название
                    попадёт в диплом. Если такой нет, переходите к согласию ниже.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-end">
                    <Button variant="outline" onClick={() => setOrganizationDialogOpen(true)}>
                      <Plus aria-hidden="true" /> Добавить организацию
                    </Button>
                  </div>
                  <OrganizationPicker
                    organizations={organizationsQuery.data ?? []}
                    selectedOrganizations={selectedOrganizations}
                    onChange={(next) => form.setValue("organizations", next, { shouldDirty: true })}
                    onAdd={() => setOrganizationDialogOpen(true)}
                  />
                </CardContent>
                <CardFooter className="flex-col items-stretch gap-3">
                  {/* The gate, not a formality: no participant's record may be created
                      without a basis for holding it, and the platform is what enforces
                      that (LEGAL-001 §6.3). Which basis it is follows the participant's
                      own age — their representative's consent under eighteen, their own
                      above it (§6.2) — so the wording here changes with the birth date
                      above, and a tick given to the previous wording does not carry. */}
                  <ConsentCheckbox
                    consent={activeConsent}
                    checked={consentGiven}
                    error={
                      consentMissing
                        ? "Без согласия на обработку данных участника создать его нельзя"
                        : undefined
                    }
                    onChange={(checked) => {
                      setAcceptedConsentCode(checked ? activeConsent.code : null);
                      if (checked) {
                        setConsentMissing(false);
                      }
                    }}
                  />
                  {/* Asked once, and only ever asked: the organization is optional, so
                      this stops the press rather than the save. The second press goes
                      through — and says in its own label what it is about to do. */}
                  {organizationWarningShown && organizationMissing ? (
                    <Alert variant="warning">
                      Организация не выбрана — в дипломе не будет её названия. Отметьте её в списке
                      выше или создайте участника без организации.
                    </Alert>
                  ) : null}
                  <div className="flex justify-between gap-2">
                    <Button variant="outline" onClick={() => setCreateStep("general")}>
                      Назад
                    </Button>
                    <Button
                      loading={createMutation.isPending}
                      onClick={async () => {
                        // The name is checked here too: this button can be reached by
                        // clicking the tab itself, and the backend's refusal would name
                        // a field two tabs away from where it is shown.
                        if (!(await form.trigger(identityFields()))) {
                          setCreateStep("general");
                          return;
                        }
                        // Both are raised in one press: fixing the consent only to be
                        // stopped again by the organization is two round-trips through a
                        // form the person is already looking at.
                        const needsOrganizationConfirmation =
                          organizationMissing && !organizationWarningShown;
                        if (!consentGiven) {
                          setConsentMissing(true);
                        }
                        if (needsOrganizationConfirmation) {
                          setOrganizationWarningShown(true);
                        }
                        if (!consentGiven || needsOrganizationConfirmation) {
                          return;
                        }
                        createMutation.mutate(form.getValues());
                      }}
                    >
                      {organizationWarningShown && organizationMissing
                        ? "Создать без организации"
                        : "Создать участника"}
                    </Button>
                  </div>
                </CardFooter>
              </Card>
            </TabsContent>
            <TabsContent value="history">
              <Card>
                <CardContent>
                  <EmptyState
                    title="Заявки (скоро)"
                    description="История заявок появится в этом разделе в следующих релизах."
                  />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="notes">
              <Card>
                <CardContent className="p-4">
                  <Textarea label="Заметки" rows={6} {...form.register("notes")} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        ) : participantQuery.isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-12" />
            <Skeleton className="h-64" />
          </div>
        ) : participantQuery.isError || participant == null ? (
          <EmptyState
            title="Не удалось открыть профиль"
            description={participantQuery.error?.message ?? "Участник не найден"}
            action={
              <Button variant="outline" onClick={() => participantQuery.refetch()}>
                Повторить
              </Button>
            }
          />
        ) : (
          <Tabs defaultValue="general" className="space-y-4">
            <TabsList className="w-full justify-start overflow-x-auto">
              <TabsTrigger value="general">Общее</TabsTrigger>
              <TabsTrigger value="organizations">Образовательные организации</TabsTrigger>
              <TabsTrigger value="history">История</TabsTrigger>
              <TabsTrigger value="notes">Заметки</TabsTrigger>
            </TabsList>

            <TabsContent value="general">
              <Card>
                <CardContent className="grid gap-3 p-4 md:grid-cols-2">
                  <div className="md:col-span-2">
                    <Select
                      label="Тип участника"
                      value={form.watch("participantType")}
                      onValueChange={(value) =>
                        form.setValue("participantType", value as ParticipantType)
                      }
                      options={participantTypeOptions.map((option) => ({
                        value: option.value,
                        label: option.label,
                      }))}
                    />
                  </div>
                  {form.watch("participantType") === "collective" ? (
                    <div className="grid gap-3 md:col-span-2 md:grid-cols-2">
                      <Input
                        label="Название коллектива"
                        required
                        error={form.formState.errors.collectiveName?.message}
                        {...form.register("collectiveName", {
                          required: "Укажите название коллектива",
                        })}
                      />
                      <AvatarField
                        value={form.watch("avatarUrl")}
                        onChange={(url) => form.setValue("avatarUrl", url, { shouldDirty: true })}
                      />
                    </div>
                  ) : (
                    <>
                      {/* Тот же порядок, что в форме создания выше. */}
                      <Input
                        label="Фамилия"
                        required
                        error={form.formState.errors.lastName?.message}
                        {...registerName("lastName", { required: "Укажите фамилию" })}
                      />
                      <Input
                        label="Имя"
                        required
                        error={form.formState.errors.firstName?.message}
                        {...registerName("firstName", { required: "Укажите имя" })}
                      />
                      <Input label="Отчество" {...registerName("middleName")} />
                    </>
                  )}
                  {form.watch("participantType") === "solo" ? (
                    <>
                      {/* `Controller`, not `setValue`: the picker is not an input the
                          form can register, and without this the "укажите дату
                          рождения" rule would quietly stop being enforced. */}
                      <Controller
                        control={form.control}
                        name="birthDate"
                        rules={{ required: "Укажите дату рождения" }}
                        render={({ field }) => (
                          <DatePicker
                            label="Дата рождения"
                            required
                            // The year dropdown is what makes this workable: a child's
                            // birth year is a decade back, and nobody should page
                            // through a hundred and thirty months to reach it.
                            toYear={new Date().getFullYear()}
                            value={field.value}
                            onChange={field.onChange}
                            {...(form.formState.errors.birthDate?.message != null
                              ? { error: form.formState.errors.birthDate.message }
                              : {})}
                          />
                        )}
                      />
                      <Select
                        label="Пол"
                        required
                        value={form.watch("gender")}
                        onValueChange={(value) => form.setValue("gender", value as Gender)}
                        options={genderOptions.map((option) => ({
                          value: option.value,
                          label: option.label,
                        }))}
                      />
                      <AvatarField
                        value={form.watch("avatarUrl")}
                        onChange={(url) => form.setValue("avatarUrl", url, { shouldDirty: true })}
                      />
                    </>
                  ) : null}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="organizations">
              <Card>
                <CardHeader>
                  <CardTitle>Организации участника</CardTitle>
                  <CardDescription>
                    По желанию: одна или несколько организаций, которые участник представляет.
                    Основная меняется одним кликом — её название попадёт в диплом.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-end">
                    <Button variant="outline" onClick={() => setOrganizationDialogOpen(true)}>
                      <Plus aria-hidden="true" /> Добавить организацию
                    </Button>
                  </div>
                  <OrganizationPicker
                    organizations={organizationsQuery.data ?? []}
                    selectedOrganizations={selectedOrganizations}
                    onChange={(next) => form.setValue("organizations", next, { shouldDirty: true })}
                    onAdd={() => setOrganizationDialogOpen(true)}
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history">
              <Card>
                <CardHeader>
                  <CardTitle>История</CardTitle>
                  <CardDescription>
                    Раздел подготовлен для отображения истории заявок.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <EmptyState
                    title="Заявки (скоро)"
                    description="История заявок появится в этом разделе в следующих релизах."
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="notes">
              <Card>
                <CardContent className="p-4">
                  <Textarea label="Заметки" rows={6} {...form.register("notes")} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </PageContent>

      <OrganizationDirectoryDialog
        open={organizationDialogOpen}
        onOpenChange={setOrganizationDialogOpen}
        intent="create"
        onCreated={(organizationId) => {
          // Added from the participant's own form: tick it here and step out of the
          // way. Leaving the directory open with the fields cleared read as «ничего не
          // произошло», and the organization still had to be found and ticked by hand.
          form.setValue(
            "organizations",
            [
              ...selectedOrganizations,
              { organizationId, isPrimary: selectedOrganizations.length === 0 },
            ],
            { shouldDirty: true },
          );
          setOrganizationDialogOpen(false);
        }}
      />
    </PageContainer>
  );
}

function OrganizationPicker({
  organizations,
  selectedOrganizations,
  onChange,
  onAdd,
}: {
  organizations: Organization[];
  selectedOrganizations: Array<{ organizationId: string; isPrimary: boolean }>;
  onChange: (next: Array<{ organizationId: string; isPrimary: boolean }>) => void;
  /** Open the personal directory to put an organization in it. */
  onAdd: () => void;
}): React.JSX.Element {
  const [search, setSearch] = useState("");
  const filtered = organizations.filter((organization) => {
    const query = search.trim().toLowerCase();
    if (query.length === 0) {
      return true;
    }
    return (
      organization.name.toLowerCase().includes(query) ||
      (organization.city ?? "").toLowerCase().includes(query)
    );
  });

  // An empty directory is how every account starts, and a search box over blank space
  // is not an answer to «что тут делать»: say there is nothing yet, say it is optional,
  // and put the way to add one right here.
  if (organizations.length === 0) {
    return (
      <EmptyState
        title="В справочнике пока нет организаций"
        description="Организацию указывать необязательно. Если участник кого-то представляет, добавьте её один раз — дальше она останется в справочнике, и её нужно будет только отметить."
        action={
          <Button onClick={onAdd}>
            <Plus aria-hidden="true" /> Добавить организацию
          </Button>
        }
      />
    );
  }

  const selectedNames = selectedOrganizations
    .map((item) => ({
      item,
      organization: organizations.find((candidate) => candidate.id === item.organizationId),
    }))
    .filter((entry) => entry.organization != null)
    .map((entry) => `${entry.organization?.name}${entry.item.isPrimary ? " (основная)" : ""}`);

  return (
    <div className="space-y-3">
      {/* Nothing-selected used to look exactly like something-selected: the same grid of
          cards, the difference a 16px tick somewhere inside one of them. People read the
          directory as «организация уже указана» and saved without one. This line is the
          single place the answer is stated outright. */}
      <div
        className={cn(
          "flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border px-3 py-2 text-sm",
          selectedNames.length === 0
            ? "border-input border-dashed text-muted-foreground"
            : "border-primary/40 bg-primary/5",
        )}
      >
        <Building2 className="size-4 shrink-0" aria-hidden="true" />
        {selectedNames.length === 0 ? (
          <span>Организация не выбрана — отметьте её в списке ниже</span>
        ) : (
          <>
            <span className="text-muted-foreground">Выбрано:</span>
            <span className="font-medium">{selectedNames.join(", ")}</span>
          </>
        )}
      </div>
      <Input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Поиск организации"
        leadingIcon={<Search aria-hidden="true" />}
      />
      {filtered.length === 0 ? (
        <EmptyState
          title="Ничего не найдено"
          description="Измените запрос — или добавьте эту организацию в справочник."
          action={
            <Button variant="outline" onClick={onAdd}>
              <Plus aria-hidden="true" /> Добавить организацию
            </Button>
          }
        />
      ) : null}
      <div className="grid gap-2 md:grid-cols-2">
        {filtered.map((organization) => {
          const selected = selectedOrganizations.find(
            (item) => item.organizationId === organization.id,
          );
          const typeLabel =
            organizationTypeOptions.find((item) => item.value === organization.type)?.label ?? "—";
          const toggle = (): void => {
            if (selected != null) {
              onChange(
                selectedOrganizations.filter((item) => item.organizationId !== organization.id),
              );
              return;
            }
            onChange([
              ...selectedOrganizations,
              { organizationId: organization.id, isPrimary: selectedOrganizations.length === 0 },
            ]);
          };
          return (
            // The whole card is the control, not the tick inside it. People clicked the
            // organization's name — the biggest, most obvious thing in the card — got no
            // response, and read that as «уже выбрана». The checkbox stays as the state
            // indicator it always was, but it no longer carries the click on its own.
            <Card
              key={organization.id}
              role="checkbox"
              aria-checked={selected != null}
              aria-label={organization.name}
              tabIndex={0}
              onClick={toggle}
              onKeyDown={(event) => {
                if (event.key === " " || event.key === "Enter") {
                  event.preventDefault();
                  toggle();
                }
              }}
              className={cn(
                "cursor-pointer outline-none transition-colors",
                "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
                selected != null
                  ? "border-primary bg-primary/5"
                  : "hover:border-input hover:bg-muted/40",
              )}
            >
              <CardContent className="space-y-2 p-3">
                <div className="flex items-start gap-2">
                  <Checkbox
                    className="pointer-events-none mt-0.5"
                    tabIndex={-1}
                    aria-hidden="true"
                    checked={selected != null}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{organization.name}</p>
                    <p className="text-muted-foreground text-xs">
                      {typeLabel}
                      {organization.city ? ` · ${organization.city}` : ""}
                    </p>
                  </div>
                  {selected?.isPrimary ? (
                    <Badge className="shrink-0" variant="primary">
                      Основная
                    </Badge>
                  ) : null}
                </div>
                {selected != null && !selected.isPrimary ? (
                  <Button
                    variant="outline"
                    size="sm"
                    // Inside a card that is itself the toggle: without this, making an
                    // organization primary would untick it in the same click.
                    onClick={(event) => {
                      event.stopPropagation();
                      onChange(
                        selectedOrganizations.map((item) => ({
                          ...item,
                          isPrimary: item.organizationId === organization.id,
                        })),
                      );
                    }}
                  >
                    Сделать основной
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function OrganizationDirectoryDialog({
  open,
  onOpenChange,
  intent = "browse",
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Why it was opened: to look through the directory, or to put something into it. */
  intent?: "browse" | "create";
  /** The new organization's id, for the picker that sent the applicant here to select it. */
  onCreated?: (organizationId: string) => void;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"name" | "city">("name");
  const [editingOrganization, setEditingOrganization] = useState<Organization | null>(null);
  /**
   * Whether the list and the form fit side by side.
   *
   * On a phone they never did: the form sat under the whole directory, so somebody who
   * opened this to add their school saw a list and a search box, never scrolled far
   * enough to reach the fields, and «Редактировать» looked like a button that does
   * nothing. On a narrow screen it is one or the other, and the buttons carry you over.
   */
  const sideBySide = useMediaQuery(DIRECTORY_SIDE_BY_SIDE);
  const [step, setStep] = useState<"list" | "form">("list");
  const showList = sideBySide || step === "list";
  const showForm = sideBySide || step === "form";

  const form = useForm<OrganizationFormValues>({ defaultValues: BLANK_ORGANIZATION });
  const { reset } = form;

  useEffect(() => {
    if (!open) {
      return;
    }
    // Opened to add something — start on the form rather than on a list of what is
    // already there. Reopening also starts clean: half an edit abandoned last time is
    // not what the next «Добавить» is about.
    setStep(intent === "create" ? "form" : "list");
    setEditingOrganization(null);
    setSearch("");
    reset(BLANK_ORGANIZATION);
  }, [open, intent, reset]);

  const startCreating = (): void => {
    setEditingOrganization(null);
    reset(BLANK_ORGANIZATION);
    setStep("form");
  };

  const startEditing = (organization: Organization): void => {
    setEditingOrganization(organization);
    reset({
      name: organization.name,
      type: organization.type,
      country: organization.country ?? "",
      city: organization.city ?? "",
      address: organization.address ?? "",
      website: organization.website ?? "",
    });
    setStep("form");
  };

  const backToList = (): void => {
    setEditingOrganization(null);
    reset(BLANK_ORGANIZATION);
    setStep("list");
  };

  const organizationsQuery = useQuery<Organization[], ApiError>({
    queryKey: ["participant-registry", "organizations", "all"],
    queryFn: () => fetchOrganizations(true),
    enabled: open,
  });

  const createOrUpdate = useMutation({
    mutationFn: async (values: OrganizationFormValues): Promise<string | null> => {
      if (editingOrganization == null) {
        const response = await apiClient.post("participants/organizations", { json: values });
        const payload = (await response.json()) as { data: { id: string } };
        return payload.data.id;
      }
      await apiClient.patch(`participants/organizations/${editingOrganization.id}`, {
        json: values,
      });
      return null;
    },
    onSuccess: (createdId) => {
      backToList();
      queryClient.invalidateQueries({ queryKey: ["participant-registry"] });
      toast.success(createdId == null ? "Организация сохранена" : "Организация добавлена");
      // Whoever sent the applicant here to add one gets it back selected, and the
      // directory closes behind them: the answer belongs on the participant's form,
      // not in a dialog they now have to work out how to leave.
      if (createdId != null && onCreated != null) {
        onCreated(createdId);
      }
    },
    onError: async (error) => toast.error((await toApiError(error)).message),
  });

  const archiveOrRestore = useMutation({
    mutationFn: async (organizationId: string) =>
      apiClient.post(`participants/organizations/${organizationId}/archive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["participant-registry"] });
    },
  });

  const rows = [...(organizationsQuery.data ?? [])]
    .filter((organization) => {
      const query = search.trim().toLowerCase();
      if (query.length === 0) {
        return true;
      }
      return (
        organization.name.toLowerCase().includes(query) ||
        (organization.city ?? "").toLowerCase().includes(query)
      );
    })
    .sort((a, b) =>
      sortBy === "name" ? a.name.localeCompare(b.name) : (a.city ?? "").localeCompare(b.city ?? ""),
    );

  const addButton = (
    <Button className="w-full" onClick={startCreating}>
      <Plus aria-hidden="true" /> Добавить организацию
    </Button>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Личный справочник организаций</DialogTitle>
          <DialogDescription>
            Ваш собственный список: добавленная один раз организация остаётся здесь — следующему
            участнику её достаточно отметить. Здесь её можно изменить или убрать в архив.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          {showList ? (
            <div className="space-y-3">
              {/* First on a phone, where the form is a step away rather than beside the
                  list: the reason people open this is to put something in it. */}
              {sideBySide ? null : addButton}
              <div className="grid gap-2 sm:grid-cols-2">
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Поиск в справочнике"
                  leadingIcon={<Search aria-hidden="true" />}
                />
                <Select
                  value={sortBy}
                  onValueChange={(value) => setSortBy(value as "name" | "city")}
                  options={[
                    { value: "name", label: "Сортировка: по названию" },
                    { value: "city", label: "Сортировка: по городу" },
                  ]}
                />
              </div>

              {organizationsQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-16" />
                  <Skeleton className="h-16" />
                  <Skeleton className="h-16" />
                </div>
              ) : organizationsQuery.isError ? (
                <EmptyState
                  title="Не удалось загрузить справочник"
                  description={organizationsQuery.error.message}
                  action={
                    <Button variant="outline" onClick={() => organizationsQuery.refetch()}>
                      Повторить
                    </Button>
                  }
                />
              ) : rows.length === 0 ? (
                <EmptyState
                  title={search.trim().length > 0 ? "Ничего не найдено" : "Справочник пуст"}
                  description={
                    search.trim().length > 0
                      ? "Измените поисковый запрос."
                      : "Добавьте первую образовательную организацию — дальше она останется в этом списке."
                  }
                  {...(search.trim().length === 0 && !sideBySide
                    ? { action: <Button onClick={startCreating}>Добавить организацию</Button> }
                    : {})}
                />
              ) : (
                <div className="space-y-2">
                  {rows.map((organization) => {
                    const typeLabel =
                      organizationTypeOptions.find((item) => item.value === organization.type)
                        ?.label ?? "—";
                    return (
                      <Card key={organization.id}>
                        <CardContent className="flex flex-wrap items-center justify-between gap-2 p-3">
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{organization.name}</p>
                              {organization.archived ? (
                                <Badge variant="outline">Архив</Badge>
                              ) : null}
                            </div>
                            <p className="text-muted-foreground text-xs">
                              {typeLabel}
                              {organization.city ? ` · ${organization.city}` : ""}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => startEditing(organization)}
                            >
                              Редактировать
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => archiveOrRestore.mutate(organization.id)}
                            >
                              {organization.archived ? "Восстановить" : "В архив"}
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </div>
          ) : null}

          {showForm ? (
            <Card>
              <CardHeader className="gap-2">
                {/* The way back, where the list is not on screen to click. */}
                {sideBySide ? null : (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="self-start px-0"
                    onClick={backToList}
                  >
                    <ArrowLeft aria-hidden="true" /> К списку
                  </Button>
                )}
                <CardTitle>
                  {editingOrganization == null ? "Новая организация" : "Редактирование"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form
                  className="space-y-3"
                  onSubmit={form.handleSubmit((values) => createOrUpdate.mutate(values))}
                >
                  <Input
                    label="Название"
                    required
                    error={form.formState.errors.name?.message}
                    {...form.register("name", { required: "Введите название организации" })}
                  />
                  <Select
                    label="Тип"
                    value={form.watch("type")}
                    onValueChange={(value) => form.setValue("type", value as OrganizationType)}
                    options={organizationTypeOptions}
                  />
                  <Input label="Страна" {...form.register("country")} />
                  <Input label="Город" {...form.register("city")} />
                  <Input label="Адрес" {...form.register("address")} />
                  <Input label="Сайт" {...form.register("website")} />
                  <div className="flex gap-2">
                    <Button type="submit" className="flex-1" loading={createOrUpdate.isPending}>
                      {editingOrganization == null ? "Создать" : "Сохранить"}
                    </Button>
                    {editingOrganization != null ? (
                      <Button type="button" variant="outline" onClick={backToList}>
                        Отмена
                      </Button>
                    ) : null}
                  </div>
                </form>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
