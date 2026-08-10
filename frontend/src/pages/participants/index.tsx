import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArrowLeft, Medal, Plus, Search, Trash2, UserPen } from "lucide-react";
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
import { formatPersonName } from "@/shared/lib";
import {
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
              <Card key={participant.id} className="group">
                <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
                  <div className="flex items-center gap-3">
                    <Avatar
                      size="lg"
                      {...(participant.avatarUrl ? { src: participant.avatarUrl } : {})}
                      fallback={initialsFromName(participant.fullName)}
                    />
                    <div>
                      <CardTitle className="text-base">{participant.fullName}</CardTitle>
                      {participant.participantType === "collective" ? (
                        <CardDescription>Коллектив</CardDescription>
                      ) : (
                        <CardDescription>
                          {participant.age} лет · {formatDate(participant.birthDate)}
                        </CardDescription>
                      )}
                    </div>
                  </div>
                  <Badge variant={participant.archived ? "outline" : "primary"}>
                    {participant.participantType === "collective" ? "Коллектив" : "Соло"}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <p>
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
                  <div className="flex flex-wrap gap-2">
                    {participant.organizations.map((organization) => (
                      <Badge
                        key={organization.id}
                        variant={organization.isPrimary ? "primary" : "secondary"}
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
  const autosaveTimer = useRef<number | null>(null);
  const isCreateMode = participantId === "new" || participantId == null;
  // Which consent was ticked, rather than whether one was. The wording depends on the
  // participant's age, so editing the birth date across the eighteenth birthday changes
  // the question being asked — and storing the code makes the old answer stop counting
  // by itself, instead of carrying a tick from a text that is no longer on screen.
  const [acceptedConsentCode, setAcceptedConsentCode] = useState<string | null>(null);
  const [consentMissing, setConsentMissing] = useState(false);

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

  useEffect(() => {
    const participant = participantQuery.data;
    if (participant == null) {
      return;
    }
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
  }, [participantQuery.data, form.reset]);

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

  const values = form.watch();
  useEffect(() => {
    if (isCreateMode || !form.formState.isDirty || participantId == null) {
      return;
    }
    if (autosaveTimer.current != null) {
      window.clearTimeout(autosaveTimer.current);
    }
    autosaveTimer.current = window.setTimeout(() => {
      updateMutation.mutate(values);
    }, 800);
    return () => {
      if (autosaveTimer.current != null) {
        window.clearTimeout(autosaveTimer.current);
      }
    };
  }, [form.formState.isDirty, isCreateMode, participantId, updateMutation.mutate, values]);

  const participant = participantQuery.data;
  const selectedOrganizations = form.watch("organizations");
  // Derived from the live form values, so the checkbox below re-reads the birth date as
  // it is typed. `values` is already a `form.watch()` of everything, so this costs a
  // comparison on a render that was happening anyway.
  const activeConsent = participantConsent(values);
  const consentGiven = acceptedConsentCode === activeConsent.code;

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
            ? "Заполните форму создания."
            : "Изменения сохраняются автоматически. Профиль принадлежит вашему личному реестру."}
        </PageDescription>
      </PageHeader>

      <PageContent>
        {isCreateMode ? (
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
                      <Input
                        label="Имя"
                        required
                        error={form.formState.errors.firstName?.message}
                        {...registerName("firstName", { required: "Укажите имя" })}
                      />
                      <Input
                        label="Фамилия"
                        required
                        error={form.formState.errors.lastName?.message}
                        {...registerName("lastName", { required: "Укажите фамилию" })}
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
              </Card>
            </TabsContent>
            <TabsContent value="organizations">
              <Card>
                <CardHeader>
                  <CardTitle>Организации участника</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-end">
                    <Button variant="outline" onClick={() => setOrganizationDialogOpen(true)}>
                      Справочник организаций
                    </Button>
                  </div>
                  <OrganizationPicker
                    organizations={organizationsQuery.data ?? []}
                    selectedOrganizations={selectedOrganizations}
                    onChange={(next) => form.setValue("organizations", next, { shouldDirty: true })}
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
                  <div className="flex justify-end">
                    <Button
                      loading={createMutation.isPending}
                      onClick={() => {
                        if (!consentGiven) {
                          setConsentMissing(true);
                          return;
                        }
                        createMutation.mutate(form.getValues());
                      }}
                    >
                      Создать участника
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
                      <Input
                        label="Имя"
                        required
                        error={form.formState.errors.firstName?.message}
                        {...registerName("firstName", { required: "Укажите имя" })}
                      />
                      <Input
                        label="Фамилия"
                        required
                        error={form.formState.errors.lastName?.message}
                        {...registerName("lastName", { required: "Укажите фамилию" })}
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
                    Выберите одну или несколько организаций. Основная меняется одним кликом.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-end">
                    <Button variant="outline" onClick={() => setOrganizationDialogOpen(true)}>
                      Справочник организаций
                    </Button>
                  </div>
                  <OrganizationPicker
                    organizations={organizationsQuery.data ?? []}
                    selectedOrganizations={selectedOrganizations}
                    onChange={(next) => form.setValue("organizations", next, { shouldDirty: true })}
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
      />
    </PageContainer>
  );
}

function OrganizationPicker({
  organizations,
  selectedOrganizations,
  onChange,
}: {
  organizations: Organization[];
  selectedOrganizations: Array<{ organizationId: string; isPrimary: boolean }>;
  onChange: (next: Array<{ organizationId: string; isPrimary: boolean }>) => void;
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

  return (
    <div className="space-y-3">
      <Input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Поиск организации"
        leadingIcon={<Search aria-hidden="true" />}
      />
      <div className="grid gap-2 md:grid-cols-2">
        {filtered.map((organization) => {
          const selected = selectedOrganizations.find(
            (item) => item.organizationId === organization.id,
          );
          const typeLabel =
            organizationTypeOptions.find((item) => item.value === organization.type)?.label ?? "—";
          return (
            <Card key={organization.id}>
              <CardContent className="space-y-2 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium">{organization.name}</p>
                    <p className="text-muted-foreground text-xs">
                      {typeLabel}
                      {organization.city ? ` · ${organization.city}` : ""}
                    </p>
                  </div>
                  {selected?.isPrimary ? <Badge variant="primary">Основная</Badge> : null}
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox
                    label="Выбрать"
                    checked={selected != null}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        onChange([
                          ...selectedOrganizations,
                          {
                            organizationId: organization.id,
                            isPrimary: selectedOrganizations.length === 0,
                          },
                        ]);
                        return;
                      }
                      onChange(
                        selectedOrganizations.filter(
                          (item) => item.organizationId !== organization.id,
                        ),
                      );
                    }}
                  />
                  {selected != null ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        onChange(
                          selectedOrganizations.map((item) => ({
                            ...item,
                            isPrimary: item.organizationId === organization.id,
                          })),
                        )
                      }
                    >
                      Сделать основной
                    </Button>
                  ) : null}
                </div>
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
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"name" | "city">("name");
  const [editingOrganization, setEditingOrganization] = useState<Organization | null>(null);
  const form = useForm<OrganizationFormValues>({
    defaultValues: {
      name: "",
      type: "school",
      country: "",
      city: "",
      address: "",
      website: "",
    },
  });

  const organizationsQuery = useQuery<Organization[], ApiError>({
    queryKey: ["participant-registry", "organizations", "all"],
    queryFn: () => fetchOrganizations(true),
    enabled: open,
  });

  const createOrUpdate = useMutation({
    mutationFn: async (values: OrganizationFormValues) => {
      if (editingOrganization == null) {
        await apiClient.post("participants/organizations", { json: values });
      } else {
        await apiClient.patch(`participants/organizations/${editingOrganization.id}`, {
          json: values,
        });
      }
    },
    onSuccess: () => {
      setEditingOrganization(null);
      form.reset({
        name: "",
        type: "school",
        country: "",
        city: "",
        address: "",
        website: "",
      });
      queryClient.invalidateQueries({ queryKey: ["participant-registry"] });
      toast.success("Справочник обновлен");
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Личный справочник организаций</DialogTitle>
          <DialogDescription>
            Переиспользуйте организации во всех участниках. Поддерживаются создание, редактирование,
            архив и восстановление.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="space-y-3">
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
                    : "Добавьте первую образовательную организацию."
                }
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
                            {organization.archived ? <Badge variant="outline">Архив</Badge> : null}
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
                            onClick={() => {
                              setEditingOrganization(organization);
                              form.reset({
                                name: organization.name,
                                type: organization.type,
                                country: organization.country ?? "",
                                city: organization.city ?? "",
                                address: organization.address ?? "",
                                website: organization.website ?? "",
                              });
                            }}
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

          <Card>
            <CardHeader>
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
                  <Button type="submit" className="flex-1">
                    {editingOrganization == null ? "Создать" : "Сохранить"}
                  </Button>
                  {editingOrganization != null ? (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setEditingOrganization(null);
                        form.reset({
                          name: "",
                          type: "school",
                          country: "",
                          city: "",
                          address: "",
                          website: "",
                        });
                      }}
                    >
                      Отмена
                    </Button>
                  ) : null}
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
}
