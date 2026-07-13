import { ArrowLeft, Pencil } from "lucide-react";
import { generatePath, Link, useParams } from "react-router";

import {
  applicationStatusPresentation,
  submissionStatusPresentation,
  useApplication,
  useCancelApplication,
} from "@/entities/application";
import { ROUTES } from "@/shared/config";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Divider,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
} from "@/shared/ui";

const CANCELLABLE = new Set(["DRAFT", "SUBMITTED", "WAITING_PAYMENT"]);

export function ApplicationDetailPage(): React.JSX.Element {
  const { applicationId } = useParams<{ applicationId: string }>();
  const { data: application, isLoading } = useApplication(applicationId);
  const cancel = useCancelApplication(applicationId ?? "");

  if (isLoading || !application) {
    return (
      <PageContainer>
        <PageContent>
          <LoadingState label="Загружаем заявку…" />
        </PageContent>
      </PageContainer>
    );
  }

  const status = applicationStatusPresentation(application.status);

  return (
    <PageContainer>
      <PageHeader
        actions={
          <div className="flex gap-2">
            {application.status === "DRAFT" ? (
              <Button asChild variant="secondary" size="sm">
                <Link
                  to={generatePath(ROUTES.cabinetFestivalApply, {
                    festivalId: application.competitionId,
                  })}
                >
                  <Pencil className="size-4" />
                  Продолжить заполнение
                </Link>
              </Button>
            ) : null}
            {CANCELLABLE.has(application.status) ? (
              <Button
                variant="danger"
                size="sm"
                loading={cancel.isPending}
                onClick={() => cancel.mutate()}
              >
                Отменить заявку
              </Button>
            ) : null}
          </div>
        }
      >
        <Button asChild variant="ghost" size="sm">
          <Link to={ROUTES.cabinetApplications}>
            <ArrowLeft className="size-4" />К списку заявок
          </Link>
        </Button>
        <PageTitle>Заявка</PageTitle>
        <PageDescription>
          <Badge variant={status.variant}>{status.label}</Badge>
        </PageDescription>
      </PageHeader>
      <PageContent>
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Выступления</CardTitle>
              <CardDescription>Номера, включённые в заявку.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {application.submissions.length === 0 ? (
                <p className="text-sm text-muted-foreground">Выступления ещё не добавлены.</p>
              ) : (
                application.submissions.map((ref) => {
                  const submissionStatus = submissionStatusPresentation(ref.status);
                  return (
                    <div key={ref.submissionId} className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">{ref.performanceTitle || "Без названия"}</p>
                        <p className="text-sm text-muted-foreground">
                          {ref.participantDisplayName || "Участник не указан"}
                          {ref.priceAmount ? ` · ${ref.priceAmount} ${ref.currency ?? ""}` : ""}
                        </p>
                      </div>
                      <Badge variant={submissionStatus.variant}>{submissionStatus.label}</Badge>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Стоимость</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              {application.services.map((service) => (
                <div key={service.serviceId} className="flex justify-between">
                  <span>
                    {service.name} × {service.quantity}
                  </span>
                  <span>
                    {service.lineAmount} {service.currency}
                  </span>
                </div>
              ))}
              <Divider />
              <div className="flex justify-between font-semibold">
                <span>Итого</span>
                <span>
                  {application.totalPrice
                    ? `${application.totalPrice.totalAmount} ${application.totalPrice.currency}`
                    : "—"}
                </span>
              </div>
            </CardContent>
          </Card>

          {application.organizationName ? (
            <Card>
              <CardHeader>
                <CardTitle>Образовательная организация</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{application.organizationName}</p>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </PageContent>
    </PageContainer>
  );
}
