import { ArrowLeft, CheckCircle2, Pencil } from "lucide-react";
import { useRef } from "react";
import { generatePath, Link, useParams } from "react-router";

import {
  applicationStatusPresentation,
  submissionStatusPresentation,
  useApplication,
  useCancelApplication,
  useUploadReceipt,
} from "@/entities/application";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
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
  toast,
} from "@/shared/ui";

const CANCELLABLE = new Set(["DRAFT", "SUBMITTED", "WAITING_PAYMENT"]);
const RECEIPT_STATUSES = new Set(["SUBMITTED", "WAITING_PAYMENT"]);
const RECEIPT_ACCEPT = ".pdf,image/*";

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

          {RECEIPT_STATUSES.has(application.status) || application.paymentReceipt ? (
            <ReceiptCard application={application} />
          ) : null}

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

function ReceiptCard({ application }: { application: ApplicationResource }): React.JSX.Element {
  const upload = useUploadReceipt(application.id);
  const inputRef = useRef<HTMLInputElement>(null);
  const receipt = application.paymentReceipt;
  const canUpload = RECEIPT_STATUSES.has(application.status);

  const onFileChosen = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    upload.mutate(file, {
      onSuccess: () => toast.success("Квитанция загружена"),
      onError: () => toast.error("Не удалось загрузить квитанцию"),
      onSettled: () => {
        if (inputRef.current) {
          inputRef.current.value = "";
        }
      },
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Квитанция об оплате</CardTitle>
        <CardDescription>
          Загрузите подтверждение оплаты организационного взноса (PDF или изображение).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {receipt ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="size-4 text-success" />
            Квитанция загружена {new Date(receipt.uploadedAt).toLocaleDateString("ru-RU")}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Квитанция ещё не загружена.</p>
        )}
        {canUpload ? (
          <div>
            <Button
              variant="outline"
              size="sm"
              loading={upload.isPending}
              onClick={() => inputRef.current?.click()}
            >
              {receipt ? "Заменить квитанцию" : "Загрузить квитанцию"}
            </Button>
            <input
              ref={inputRef}
              type="file"
              accept={RECEIPT_ACCEPT}
              className="hidden"
              aria-label="Квитанция об оплате"
              onChange={onFileChosen}
            />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
