import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, Search, UserPen } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";

import { fetchTeacher, teacherDirectoryKeys, useTeachers } from "@/entities/teacher";
import { toApiError } from "@/shared/api";
import { recordOwnConsent } from "@/shared/api/generated/identity/identity";
import type { AddTeacherRequest } from "@/shared/api/generated/model-teachers";
import {
  teachersCreate,
  teachersUpdate,
} from "@/shared/api/generated/teacher-directory/teacher-directory";
import { ROUTES } from "@/shared/config";
import { ConsentCheckbox, TEACHER_CONSENT } from "@/shared/consents";
import { formatPersonName } from "@/shared/lib";
import {
  Button,
  Card,
  CardContent,
  EmptyState,
  Input,
  LoadingState,
  PageActions,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  toast,
} from "@/shared/ui";

interface TeacherFormValues {
  firstName: string;
  lastName: string;
  middleName: string;
  role: string;
  email: string;
  phone: string;
}

const EMPTY_FORM: TeacherFormValues = {
  firstName: "",
  lastName: "",
  middleName: "",
  role: "",
  email: "",
  phone: "",
};

/**
 * The fields a teacher record cannot do without.
 *
 * The full name is what gets printed on a diploma or a thank-you letter, and the
 * role is what a diploma credits the teacher in. Email and phone are how the
 * organizer reaches the person — a record that names a teacher nobody can contact
 * is not usable either, so they are required alongside the printed fields.
 */
const REQUIRED_FIELDS = [
  "lastName",
  "firstName",
  "middleName",
  "role",
  "email",
  "phone",
] as const satisfies readonly (keyof TeacherFormValues)[];

function toRequest(
  values: TeacherFormValues,
): Omit<AddTeacherRequest, "consentId" | "consentVersion"> {
  return {
    firstName: values.firstName.trim(),
    lastName: values.lastName.trim(),
    middleName: values.middleName.trim() || null,
    role: values.role.trim(),
    email: values.email.trim() || null,
    phone: values.phone.trim() || null,
  };
}

export function TeachersPage(): React.JSX.Element {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const { data: teachers, isLoading } = useTeachers();

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    const list = teachers ?? [];
    if (!query) {
      return list;
    }
    return list.filter((teacher) =>
      `${teacher.displayName} ${teacher.role}`.toLowerCase().includes(query),
    );
  }, [teachers, search]);

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Мои педагоги</PageTitle>
        <PageDescription>
          Личный справочник педагогов для повторного использования в заявках.
        </PageDescription>
        <PageActions>
          <Button
            leftIcon={<Plus className="size-4" />}
            onClick={() => navigate(ROUTES.cabinetTeacherNew)}
          >
            Добавить педагога
          </Button>
        </PageActions>
      </PageHeader>
      <PageContent className="space-y-4">
        <Input
          leadingIcon={<Search className="size-4" />}
          placeholder="Поиск педагогов"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        {isLoading ? (
          <LoadingState label="Загружаем справочник…" />
        ) : filtered.length === 0 ? (
          <EmptyState
            title={search ? "Ничего не найдено" : "В справочнике пока нет педагогов"}
            description="Добавьте педагога, чтобы переиспользовать его в заявках."
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {filtered.map((teacher) => (
              <Card key={teacher.id}>
                <CardContent className="flex items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{teacher.displayName}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {teacher.role}
                      {teacher.email ? ` · ${teacher.email}` : ""}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<UserPen className="size-4" />}
                    onClick={() => navigate(`${ROUTES.cabinetTeachers}/${teacher.id}`)}
                  >
                    Изменить
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </PageContent>
    </PageContainer>
  );
}

export function TeacherProfilePage(): React.JSX.Element {
  const { teacherId } = useParams<{ teacherId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const isCreateMode = teacherId === "new" || teacherId == null;

  // When the wizard sends the user here to create a teacher, it passes where to
  // return and which submission to credit the result to.
  const returnTo = searchParams.get("returnTo");
  const returnSubmissionId = searchParams.get("submissionId");

  const [values, setValues] = useState<TeacherFormValues>(EMPTY_FORM);
  // Set by a save attempt that could not go through, which is what turns the
  // required markers into per-field messages.
  const [submitted, setSubmitted] = useState(false);
  const [teacherConsent, setTeacherConsent] = useState(false);

  const teacherQuery = useQuery({
    enabled: !isCreateMode && teacherId != null,
    queryKey: teacherDirectoryKeys.teacher(teacherId ?? ""),
    queryFn: () => fetchTeacher(teacherId ?? ""),
  });

  useEffect(() => {
    const teacher = teacherQuery.data;
    if (teacher == null) {
      return;
    }
    setValues({
      firstName: teacher.firstName,
      lastName: teacher.lastName,
      middleName: teacher.middleName ?? "",
      role: teacher.role,
      email: teacher.email ?? "",
      phone: teacher.phone ?? "",
    });
  }, [teacherQuery.data]);

  const createMutation = useMutation({
    mutationFn: async (form: TeacherFormValues): Promise<string> => {
      // The journal entry first, and its id travels with the teacher: the row the
      // cabinet reads then carries the basis for holding this adult's details rather
      // than pointing at nothing (LEGAL-001 §5.4, §13.3). Creation is refused
      // server-side without it, so an interrupted flow leaves no teacher on file.
      const consent = await recordOwnConsent({
        consentType: TEACHER_CONSENT.code,
        version: TEACHER_CONSENT.version,
      });
      if (consent.status !== 201) {
        throw new Error("Не удалось записать согласие педагога.");
      }
      const consentId = consent.data.data[0]?.id;
      if (consentId == null) {
        throw new Error("Не удалось записать согласие педагога.");
      }
      const response = await teachersCreate({
        ...toRequest(form),
        consentId,
        consentVersion: TEACHER_CONSENT.version,
      });
      if (response.status !== 201) {
        throw new Error("Не удалось создать педагога. Попробуйте ещё раз.");
      }
      return response.data.data.id;
    },
    onSuccess: (createdId) => {
      queryClient.invalidateQueries({ queryKey: teacherDirectoryKeys.all });
      toast.success("Педагог создан");
      if (returnTo && returnSubmissionId) {
        const params = new URLSearchParams({
          pickedTeacherId: createdId,
          submissionId: returnSubmissionId,
        });
        navigate(`${returnTo}?${params.toString()}`);
        return;
      }
      navigate(ROUTES.cabinetTeachers);
    },
    onError: async (error) => {
      toast.error((await toApiError(error)).message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (form: TeacherFormValues) => {
      await teachersUpdate(teacherId ?? "", toRequest(form));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teacherDirectoryKeys.all });
      toast.success("Педагог обновлён");
      navigate(ROUTES.cabinetTeachers);
    },
    onError: async (error) => {
      toast.error((await toApiError(error)).message);
    },
  });

  const canSave = REQUIRED_FIELDS.every((field) => values[field].trim());
  const pending = createMutation.isPending || updateMutation.isPending;
  const set = (field: keyof TeacherFormValues) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setValues((prev) => ({ ...prev, [field]: event.target.value }));
  };

  /**
   * Tidies a ФИО field once the user leaves it.
   *
   * On blur rather than on every keystroke: rewriting the value mid-word would
   * fight the caret of anyone deliberately typing a lowercase particle.
   */
  const normalizeName = (field: keyof TeacherFormValues) => () => {
    setValues((prev) => ({ ...prev, [field]: formatPersonName(prev[field]) }));
  };

  /**
   * The message under a required field, once the form has been submitted.
   *
   * Shown only after a save attempt: flagging fields the moment the page opens
   * would scold the user for not having typed yet.
   */
  const errorFor = (field: (typeof REQUIRED_FIELDS)[number]): { error: string } | undefined =>
    submitted && !values[field].trim() ? { error: "Обязательное поле" } : undefined;

  function handleSave(): void {
    if (!canSave) {
      setSubmitted(true);
      return;
    }
    // Only on creation: once the consent is on file, editing a phone number has no
    // reason to ask for it again.
    if (isCreateMode && !teacherConsent) {
      setSubmitted(true);
      return;
    }
    if (isCreateMode) {
      createMutation.mutate(values);
    } else {
      updateMutation.mutate(values);
    }
  }

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>{isCreateMode ? "Новый педагог" : "Педагог"}</PageTitle>
        <PageActions>
          <Button
            variant="outline"
            leftIcon={<ArrowLeft className="size-4" />}
            onClick={() => navigate(-1)}
          >
            Назад
          </Button>
        </PageActions>
      </PageHeader>
      <PageContent className="max-w-xl space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Фамилия"
            required
            value={values.lastName}
            onChange={set("lastName")}
            onBlur={normalizeName("lastName")}
            {...errorFor("lastName")}
          />
          <Input
            label="Имя"
            required
            value={values.firstName}
            onChange={set("firstName")}
            onBlur={normalizeName("firstName")}
            {...errorFor("firstName")}
          />
          <Input
            label="Отчество"
            required
            value={values.middleName}
            onChange={set("middleName")}
            onBlur={normalizeName("middleName")}
            {...errorFor("middleName")}
          />
          <Input
            label="Роль"
            required
            value={values.role}
            onChange={set("role")}
            placeholder="Педагог, Концертмейстер…"
            {...errorFor("role")}
          />
          {/* Contacts: not part of what gets printed, but the only way to reach the
              teacher about the performance they are credited on. */}
          <Input
            label="Email"
            type="email"
            required
            value={values.email}
            onChange={set("email")}
            {...errorFor("email")}
          />
          <Input
            label="Телефон"
            required
            value={values.phone}
            onChange={set("phone")}
            {...errorFor("phone")}
          />
        </div>
        <div className="space-y-3">
          {isCreateMode ? (
            <ConsentCheckbox
              consent={TEACHER_CONSENT}
              checked={teacherConsent}
              error={
                submitted && !teacherConsent
                  ? "Без согласия педагога добавить его в справочник нельзя"
                  : undefined
              }
              onChange={setTeacherConsent}
            />
          ) : null}
          {/* Deliberately clickable while incomplete: a disabled button gives no
              reason, whereas this one names the fields that are still empty. */}
          <Button loading={pending} onClick={handleSave}>
            Сохранить
          </Button>
          {submitted && !canSave ? (
            <p className="text-danger text-sm">
              Заполните обязательные поля, отмеченные звёздочкой.
            </p>
          ) : null}
        </div>
      </PageContent>
    </PageContainer>
  );
}
