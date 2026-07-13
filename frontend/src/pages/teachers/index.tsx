import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, Search, UserPen } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";

import { fetchTeacher, teacherDirectoryKeys, useTeachers } from "@/entities/teacher";
import { toApiError } from "@/shared/api";
import type { AddTeacherRequest } from "@/shared/api/generated/model-teachers";
import {
  teachersCreate,
  teachersUpdate,
} from "@/shared/api/generated/teacher-directory/teacher-directory";
import { ROUTES } from "@/shared/config";
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

function toRequest(values: TeacherFormValues): AddTeacherRequest {
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
                    variant="ghost"
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
      const response = await teachersCreate(toRequest(form));
      if (response.status !== 201) {
        throw new Error("Failed to create teacher");
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

  const canSave = values.firstName.trim() && values.lastName.trim() && values.role.trim();
  const pending = createMutation.isPending || updateMutation.isPending;
  const set = (field: keyof TeacherFormValues) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setValues((prev) => ({ ...prev, [field]: event.target.value }));

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>{isCreateMode ? "Новый педагог" : "Педагог"}</PageTitle>
        <PageActions>
          <Button
            variant="ghost"
            leftIcon={<ArrowLeft className="size-4" />}
            onClick={() => navigate(-1)}
          >
            Назад
          </Button>
        </PageActions>
      </PageHeader>
      <PageContent className="max-w-xl space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label="Фамилия" value={values.lastName} onChange={set("lastName")} />
          <Input label="Имя" value={values.firstName} onChange={set("firstName")} />
          <Input label="Отчество" value={values.middleName} onChange={set("middleName")} />
          <Input
            label="Роль"
            value={values.role}
            onChange={set("role")}
            placeholder="Педагог, Концертмейстер…"
          />
          <Input label="Email" type="email" value={values.email} onChange={set("email")} />
          <Input label="Телефон" value={values.phone} onChange={set("phone")} />
        </div>
        <div>
          <Button
            disabled={!canSave}
            loading={pending}
            onClick={() =>
              isCreateMode ? createMutation.mutate(values) : updateMutation.mutate(values)
            }
          >
            Сохранить
          </Button>
        </div>
      </PageContent>
    </PageContainer>
  );
}
