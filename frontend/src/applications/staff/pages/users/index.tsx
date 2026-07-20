import { UserCog, UserMinus } from "lucide-react";
import { useAuth } from "@/app/providers";
import { ROLE_LABELS, ROLE_OPTIONS, type StaffInvitationRole } from "@/features/staff-invitations";
import {
  type StaffMember,
  type StaffMemberStatus,
  useChangeStaffRole,
  useRevokeStaffMember,
  useStaffMembers,
} from "@/features/staff-members";
import {
  Alert,
  Badge,
  type BadgeProps,
  Button,
  type ColumnDef,
  DataTable,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageSection,
  PageTitle,
  Select,
  toast,
} from "@/shared/ui";

const STATUS_META: Record<StaffMemberStatus, { label: string; variant: BadgeProps["variant"] }> = {
  ACTIVE: { label: "Активен", variant: "success" },
  PENDING: { label: "Ожидает", variant: "warning" },
  REVOKED: { label: "Отозван", variant: "neutral" },
};

export function StaffUsersPage(): React.JSX.Element {
  const { staffMembership } = useAuth();
  const canManage = staffMembership?.role === "OWNER" || staffMembership?.role === "DIRECTOR";
  const members = useStaffMembers();

  return (
    <PageContainer>
      <PageHeader>
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
            <UserCog className="size-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <PageTitle>Пользователи</PageTitle>
            <PageDescription>Доступы сотрудников.</PageDescription>
          </div>
        </div>
      </PageHeader>
      <PageContent>
        <PageSection
          title="Сотрудники организации"
          description="Роли и доступ сотрудников рабочего пространства."
        >
          {members.isError ? (
            <Alert variant="danger" title="Не удалось загрузить сотрудников">
              Обновите страницу и попробуйте снова.
            </Alert>
          ) : (
            <MembersTable
              data={members.data ?? []}
              loading={members.isLoading}
              canManage={canManage}
            />
          )}
        </PageSection>
      </PageContent>
    </PageContainer>
  );
}

interface MembersTableProps {
  data: StaffMember[];
  loading: boolean;
  canManage: boolean;
}

function MembersTable({ data, loading, canManage }: MembersTableProps): React.JSX.Element {
  const changeRole = useChangeStaffRole();
  const revoke = useRevokeStaffMember();

  const handleRoleChange = async (
    member: StaffMember,
    role: StaffInvitationRole,
  ): Promise<void> => {
    if (role === member.role) {
      return;
    }
    try {
      await changeRole.mutateAsync({ membershipId: member.id, role });
      toast.success("Роль обновлена");
    } catch {
      toast.error("Не удалось изменить роль");
    }
  };

  const handleRevoke = async (member: StaffMember): Promise<void> => {
    try {
      await revoke.mutateAsync(member.id);
      toast.success("Доступ отозван");
    } catch {
      toast.error("Не удалось отозвать доступ");
    }
  };

  const columns: ColumnDef<StaffMember, unknown>[] = [
    {
      accessorKey: "displayName",
      header: "Сотрудник",
      cell: ({ row }) => (
        <span className="font-medium">{row.original.displayName ?? "Без имени"}</span>
      ),
    },
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ row }) => row.original.email ?? "—",
    },
    {
      accessorKey: "role",
      header: "Роль",
      cell: ({ row }) => {
        const member = row.original;
        if (!canManage || member.status !== "ACTIVE") {
          return ROLE_LABELS[member.role];
        }
        return (
          <Select
            aria-label={`Роль сотрудника ${member.email ?? member.userId}`}
            options={ROLE_OPTIONS}
            value={member.role}
            size="sm"
            className="w-52"
            onValueChange={(role) => void handleRoleChange(member, role as StaffInvitationRole)}
          />
        );
      },
    },
    {
      accessorKey: "status",
      header: "Статус",
      cell: ({ row }) => {
        const meta = STATUS_META[row.original.status];
        return <Badge variant={meta.variant}>{meta.label}</Badge>;
      },
    },
    ...(canManage
      ? [
          {
            id: "actions",
            header: "",
            enableSorting: false,
            cell: ({ row }: { row: { original: StaffMember } }) =>
              row.original.status === "ACTIVE" ? (
                <div className="flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    leftIcon={<UserMinus aria-hidden="true" />}
                    onClick={() => void handleRevoke(row.original)}
                  >
                    Отозвать доступ
                  </Button>
                </div>
              ) : null,
          } as ColumnDef<StaffMember, unknown>,
        ]
      : []),
  ];

  return (
    <DataTable
      columns={columns}
      data={data}
      loading={loading}
      emptyContent="Пока нет сотрудников."
    />
  );
}
