import { zodResolver } from "@hookform/resolvers/zod";
import { MailPlus, Send, Trash2 } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { useAuth } from "@/app/providers";
import { applyProblemToForm } from "@/features/auth";
import {
  ROLE_LABELS,
  ROLE_OPTIONS,
  type StaffInvitationStatus,
  type StaffInvitationSummary,
  useCreateStaffInvitation,
  useRevokeStaffInvitation,
  useStaffInvitations,
} from "@/features/staff-invitations";
import {
  Alert,
  Badge,
  type BadgeProps,
  Button,
  Card,
  CardContent,
  type ColumnDef,
  DataTable,
  Input,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageSection,
  PageTitle,
  Select,
  toast,
} from "@/shared/ui";

const STATUS_META: Record<
  StaffInvitationStatus,
  { label: string; variant: BadgeProps["variant"] }
> = {
  pending: { label: "Ожидает", variant: "warning" },
  accepted: { label: "Принято", variant: "success" },
  revoked: { label: "Отозвано", variant: "neutral" },
  expired: { label: "Истекло", variant: "danger" },
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

const inviteSchema = z.object({
  email: z.string().min(1, "Укажите email").email("Некорректный email"),
  role: z.enum([
    "OWNER",
    "DIRECTOR",
    "FINANCE",
    "COMPETITION_MANAGER",
    "CONTENT_MANAGER",
    "MODERATOR",
    "SUPPORT",
  ]),
});

type InviteFormValues = z.infer<typeof inviteSchema>;

export function StaffInvitationsPage(): React.JSX.Element {
  const { staffMembership } = useAuth();
  const canManage = staffMembership?.role === "OWNER" || staffMembership?.role === "DIRECTOR";
  const invitations = useStaffInvitations();

  return (
    <PageContainer>
      <PageHeader>
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
            <MailPlus className="size-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <PageTitle>Приглашения</PageTitle>
            <PageDescription>Приглашения в рабочее пространство.</PageDescription>
          </div>
        </div>
      </PageHeader>
      <PageContent className="space-y-8">
        {canManage ? <InviteForm /> : null}

        <PageSection
          title="Отправленные приглашения"
          description="Список приглашений со статусом и сроком действия."
        >
          {invitations.isError ? (
            <Alert variant="danger" title="Не удалось загрузить приглашения">
              Обновите страницу и попробуйте снова.
            </Alert>
          ) : (
            <InvitationsTable
              data={invitations.data ?? []}
              loading={invitations.isLoading}
              canManage={canManage}
            />
          )}
        </PageSection>
      </PageContent>
    </PageContainer>
  );
}

function InviteForm(): React.JSX.Element {
  const createInvitation = useCreateStaffInvitation();
  const {
    register,
    handleSubmit,
    control,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<InviteFormValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: "", role: "SUPPORT" },
    mode: "onBlur",
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await createInvitation.mutateAsync(values);
      toast.success("Приглашение отправлено");
      reset({ email: "", role: values.role });
    } catch (error) {
      const message = applyProblemToForm<InviteFormValues>(error, {
        setError,
        knownFields: ["email", "role"],
      });
      toast.error(message ?? "Не удалось отправить приглашение");
    }
  });

  return (
    <PageSection
      title="Пригласить сотрудника"
      description="Отправьте приглашение по email с выбранной ролью."
    >
      <Card className="shadow-none">
        <CardContent className="pt-6">
          <form onSubmit={onSubmit} noValidate className="grid gap-4 md:grid-cols-[1fr_240px_auto]">
            <Input
              label="Email"
              type="email"
              placeholder="colleague@example.com"
              required
              error={errors.email?.message}
              {...register("email")}
            />
            <Controller
              control={control}
              name="role"
              render={({ field }) => (
                <Select
                  label="Роль"
                  options={ROLE_OPTIONS}
                  value={field.value}
                  onValueChange={field.onChange}
                  error={errors.role?.message}
                />
              )}
            />
            <div className="flex items-end">
              <Button
                type="submit"
                loading={isSubmitting}
                leftIcon={<Send aria-hidden="true" />}
                className="w-full md:w-auto"
              >
                Пригласить
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </PageSection>
  );
}

interface InvitationsTableProps {
  data: StaffInvitationSummary[];
  loading: boolean;
  canManage: boolean;
}

function InvitationsTable({ data, loading, canManage }: InvitationsTableProps): React.JSX.Element {
  const revoke = useRevokeStaffInvitation();

  const handleRevoke = async (invitation: StaffInvitationSummary): Promise<void> => {
    try {
      await revoke.mutateAsync(invitation.id);
      toast.success("Приглашение отозвано");
    } catch {
      toast.error("Не удалось отозвать приглашение");
    }
  };

  const columns: ColumnDef<StaffInvitationSummary, unknown>[] = [
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ row }) => <span className="font-medium">{row.original.email}</span>,
    },
    {
      accessorKey: "role",
      header: "Роль",
      cell: ({ row }) => ROLE_LABELS[row.original.role],
    },
    {
      accessorKey: "status",
      header: "Статус",
      cell: ({ row }) => {
        const meta = STATUS_META[row.original.status];
        return <Badge variant={meta.variant}>{meta.label}</Badge>;
      },
    },
    {
      accessorKey: "expiresAt",
      header: "Действует до",
      cell: ({ row }) => formatDate(row.original.expiresAt),
    },
    ...(canManage
      ? [
          {
            id: "actions",
            header: "",
            enableSorting: false,
            cell: ({ row }: { row: { original: StaffInvitationSummary } }) =>
              row.original.status === "pending" ? (
                <div className="flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    leftIcon={<Trash2 aria-hidden="true" />}
                    onClick={() => void handleRevoke(row.original)}
                  >
                    Отозвать
                  </Button>
                </div>
              ) : null,
          } as ColumnDef<StaffInvitationSummary, unknown>,
        ]
      : []),
  ];

  return (
    <DataTable
      columns={columns}
      data={data}
      loading={loading}
      emptyContent="Пока нет отправленных приглашений."
    />
  );
}
