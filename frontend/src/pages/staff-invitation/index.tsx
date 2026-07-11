import { useQueryClient } from "@tanstack/react-query";
import { ArrowRight, LogOut } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router";
import { useAuth } from "@/app/providers";
import { authKeys } from "@/features/auth";
import {
  type StaffInvitationRole,
  useAcceptStaffInvitation,
  useStaffInvitation,
} from "@/features/staff-invitations";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  PageContainer,
  Skeleton,
} from "@/shared/ui";

const ROLE_LABELS: Record<StaffInvitationRole, string> = {
  OWNER: "Владелец",
  DIRECTOR: "Директор",
  FINANCE: "Финансы",
  COMPETITION_MANAGER: "Менеджер фестивалей",
  CONTENT_MANAGER: "Контент-менеджер",
  MODERATOR: "Модератор",
  SUPPORT: "Поддержка",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function currentPath(location: ReturnType<typeof useLocation>): string {
  return `${location.pathname}${location.search}`;
}

function StateCard({
  title,
  description,
  actions,
  variant = "info",
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  variant?: "info" | "danger" | "warning";
}): React.JSX.Element {
  return (
    <PageContainer size="narrow" className="py-10">
      <Alert variant={variant} title={title}>
        {description}
      </Alert>
      {actions != null && <div className="flex flex-wrap gap-2">{actions}</div>}
    </PageContainer>
  );
}

function InvitationSkeleton(): React.JSX.Element {
  return (
    <PageContainer size="narrow" className="py-10">
      <Card>
        <CardHeader>
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-4 w-80 max-w-full" />
        </CardHeader>
        <CardContent className="grid gap-4">
          {[0, 1, 2, 3].map((item) => (
            <div key={item} className="space-y-2">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-5 w-56 max-w-full" />
            </div>
          ))}
        </CardContent>
        <CardFooter>
          <Skeleton className="h-10 w-44" />
        </CardFooter>
      </Card>
    </PageContainer>
  );
}

function DetailRow({ label, value }: { label: string; value: string }): React.JSX.Element {
  return (
    <div className="grid gap-1 rounded-md border bg-muted/30 p-3">
      <dt className="font-medium text-muted-foreground text-xs uppercase">{label}</dt>
      <dd className="font-medium text-foreground text-sm">{value}</dd>
    </div>
  );
}

export function StaffInvitationPage(): React.JSX.Element {
  const { token } = useParams<{ token: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { status, staffMembership, refresh, signOut } = useAuth();
  const invitation = useStaffInvitation(token);
  const accept = useAcceptStaffInvitation();

  if (!token) {
    return <StateCard variant="danger" title="Приглашение не найдено." />;
  }

  if (status === "unauthenticated") {
    const next = encodeURIComponent(currentPath(location));
    return <Navigate to={`${ROUTES.login}?next=${next}`} replace />;
  }

  const handleAccept = async (): Promise<void> => {
    try {
      await accept.mutateAsync(token);
      await queryClient.invalidateQueries({ queryKey: authKeys.currentUser });
      await refresh();
      navigate(ROUTES.cabinet, { replace: true });
    } catch {
      // The mutation state renders the expected Problem Details outcome.
    }
  };

  const handleSwitchAccount = async (): Promise<void> => {
    await signOut();
    const next = encodeURIComponent(currentPath(location));
    navigate(`${ROUTES.login}?next=${next}`, { replace: true });
  };

  if (status === "loading" || invitation.isLoading) {
    return <InvitationSkeleton />;
  }

  if (invitation.error instanceof ApiError) {
    if (invitation.error.status === 404) {
      return <StateCard variant="danger" title="Приглашение не найдено." />;
    }
    if (invitation.error.status === 410) {
      return <StateCard variant="warning" title="Срок действия приглашения истек." />;
    }
    if (invitation.error.status === 409) {
      return (
        <StateCard
          variant="warning"
          title="Приглашение уже использовано."
          actions={
            staffMembership != null ? (
              <Button asChild>
                <Link to={ROUTES.cabinet}>Перейти в кабинет</Link>
              </Button>
            ) : null
          }
        />
      );
    }
    return <StateCard variant="danger" title="Не удалось загрузить приглашение." />;
  }

  if (!invitation.data) {
    return <StateCard variant="danger" title="Приглашение не найдено." />;
  }

  const acceptError = accept.error instanceof ApiError ? accept.error : null;
  const isWrongAccount = acceptError?.status === 403;

  return (
    <PageContainer size="narrow" className="py-10">
      <Card>
        <CardHeader>
          <CardTitle>Приглашение в команду</CardTitle>
          <p className="text-muted-foreground text-sm">
            Проверьте данные приглашения и подтвердите присоединение.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {isWrongAccount ? (
            <Alert variant="danger" title="Вы вошли под другой учетной записью.">
              Выйдите или переключитесь на аккаунт с email {invitation.data.invitedEmail}.
            </Alert>
          ) : null}
          {acceptError != null && !isWrongAccount ? (
            <Alert variant="danger" title="Не удалось принять приглашение.">
              {acceptError.status === 409
                ? "Приглашение уже использовано."
                : "Попробуйте повторить действие позже."}
            </Alert>
          ) : null}
          <dl className="grid gap-3 sm:grid-cols-2">
            <DetailRow label="Организация" value={invitation.data.organizationName} />
            <DetailRow label="Роль" value={ROLE_LABELS[invitation.data.role]} />
            <DetailRow label="Email" value={invitation.data.invitedEmail} />
            <DetailRow label="Действует до" value={formatDate(invitation.data.expiresAt)} />
          </dl>
        </CardContent>
        <CardFooter className="flex flex-wrap gap-2">
          {isWrongAccount ? (
            <>
              <Button variant="outline" leftIcon={<LogOut />} onClick={() => void signOut()}>
                Logout
              </Button>
              <Button onClick={() => void handleSwitchAccount()}>Switch account</Button>
            </>
          ) : (
            <Button
              onClick={() => void handleAccept()}
              loading={accept.isPending}
              disabled={accept.isPending}
              rightIcon={<ArrowRight />}
            >
              Accept invitation
            </Button>
          )}
        </CardFooter>
      </Card>
    </PageContainer>
  );
}
