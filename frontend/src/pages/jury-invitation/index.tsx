import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { Navigate, useLocation, useNavigate, useParams } from "react-router";

import { useAuth } from "@/app/providers";
import { useAcceptJuryInvitation } from "@/features/judging";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import { authPathWithNext, clearPostAuthRedirect } from "@/shared/lib";
import { useSeo } from "@/shared/seo";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  PageContainer,
} from "@/shared/ui";

/**
 * `/jury/invite/:token` — the link an invitation e-mail carries.
 *
 * Accepting requires being signed in, and that is the point rather than a hurdle: the
 * link identifies the *seat*, the account identifies the *person*, and a seat with no
 * account behind it cannot score. A judge who follows the link logged out is sent to
 * sign-in and comes straight back here — including through registration and a
 * confirmation e-mail, which is the long way round and the one that used to drop the
 * invitation on the floor. See `post-auth-redirect`.
 *
 * The token is single-use. It is burned at acceptance so a forwarded e-mail cannot seat
 * a second person on a jury.
 */
export function JuryInvitationPage(): React.JSX.Element {
  const { token } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const accept = useAcceptJuryInvitation();
  const [error, setError] = useState<string | null>(null);

  useSeo({ title: "Приглашение в жюри", robots: "noindex" });

  if (token == null) {
    return <Navigate to={ROUTES.home} replace />;
  }

  if (!isAuthenticated) {
    // Come back here after signing in: the link is what says which seat this is.
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={authPathWithNext(ROUTES.login, next)} replace />;
  }

  const handleAccept = async (): Promise<void> => {
    setError(null);
    try {
      await accept.mutateAsync(token);
      clearPostAuthRedirect();
      void navigate(ROUTES.jury, { replace: true });
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Не удалось принять приглашение. Попробуйте ещё раз.",
      );
    }
  };

  return (
    <PageContainer size="narrow" className="py-10">
      <Card>
        <CardHeader>
          <CardTitle>Приглашение в жюри</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-muted-foreground text-sm">
            Приняв приглашение, вы войдёте в состав жюри фестиваля и сможете выставлять оценки
            выступлениям со своего устройства — телефона, планшета или ноутбука.
          </p>
          <p className="text-muted-foreground text-sm">
            Ссылка одноразовая: после принятия она перестанет работать.
          </p>
          {error != null ? (
            <Alert variant="danger" title="Приглашение не принято">
              {error}
            </Alert>
          ) : null}
        </CardContent>
        <CardFooter>
          <Button type="button" loading={accept.isPending} onClick={() => void handleAccept()}>
            Принять приглашение
            <ArrowRight className="size-4" aria-hidden="true" />
          </Button>
        </CardFooter>
      </Card>
    </PageContainer>
  );
}
