import { ArrowLeft, Check } from "lucide-react";
import { generatePath, Link, Navigate, useParams } from "react-router";

import {
  applicationStatusPresentation,
  applicationTotalLabel,
  REGULATION_PRICE_NOTE,
  useApplication,
  useRegistration,
} from "@/entities/application";
import { BenefitDocumentsCard } from "@/features/application-benefit-documents";
import { PhonogramsCard } from "@/features/application-phonograms";
import { ReceiptCard } from "@/features/application-receipt";
import { ConsentsCard, PerformanceBuilder, ServicesCard } from "@/features/registration-wizard";
import { ROUTES } from "@/shared/config";
import {
  Alert,
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

/**
 * Editing an application the organizer has already received.
 *
 * A screen of its own rather than a second trip through the wizard. The wizard is
 * written for a form being filled in for the first time — it is titled "Подача
 * заявки", it walks the applicant to a "Подать заявку" button, and it says nothing
 * about who is now waiting on the entry. Reopening it to fix one teacher's name left
 * the applicant unsure whether they were amending their entry or starting a second one.
 *
 * Here the frame says what is happening: the order is already placed, every change is
 * saved as it is made, and the organizer will be told what changed. The editing
 * surfaces themselves are the wizard's own components, so a performance is composed
 * the same way in both places.
 */
export function ApplicationEditPage(): React.JSX.Element {
  const { applicationId = "" } = useParams<{ applicationId: string }>();
  const { data: application, isLoading: applicationLoading } = useApplication(applicationId);
  const { data: registration, isLoading: registrationLoading } = useRegistration(
    application?.competitionId,
  );

  if (applicationLoading || registrationLoading || !application || !registration) {
    return (
      <PageContainer>
        <PageContent>
          <LoadingState label="Загружаем заявку…" />
        </PageContent>
      </PageContainer>
    );
  }

  const detailTo = generatePath(ROUTES.cabinetApplication, { applicationId });

  // A draft belongs to the wizard: it has never been submitted, so there is nothing to
  // amend and no organizer to notify — the applicant is still filling it in.
  if (application.status === "DRAFT") {
    return (
      <Navigate
        to={`${generatePath(ROUTES.cabinetFestivalApply, { festivalId: application.competitionId })}?applicationId=${applicationId}`}
        replace
      />
    );
  }

  // Editing stays open while registration runs, and after it closes only for an order
  // the organizer sent back. Anything else is read-only, and the card is the place to
  // read it — the same rule the detail screen applies to its "Редактировать" button.
  const editable =
    (registration.registrationOpen || application.hasCorrections) &&
    application.status === "SUBMITTED";
  if (!editable) {
    return <Navigate to={detailTo} replace />;
  }

  const status = applicationStatusPresentation(application.status);
  const number = applicationId.slice(0, 8).toUpperCase();
  const totalPrice = applicationTotalLabel(application.totalPrice);

  return (
    <PageContainer>
      <PageHeader
        actions={
          <Button asChild size="sm">
            <Link to={detailTo}>
              <Check className="size-4" />
              Готово
            </Link>
          </Button>
        }
      >
        <Button asChild variant="ghost" size="sm">
          <Link to={detailTo}>
            <ArrowLeft className="size-4" />К карточке заявки
          </Link>
        </Button>
        <PageTitle>Редактирование заявки №{number}</PageTitle>
        <PageDescription className="flex flex-wrap items-center gap-2">
          <span>{registration.competition.title}</span>
          <Badge variant={status.variant}>{status.label}</Badge>
        </PageDescription>
      </PageHeader>
      <PageContent className="flex flex-col gap-6">
        <Alert variant="info">
          <p className="font-medium">Заявка уже подана</p>
          <p className="mt-1 text-sm">
            Каждое изменение сохраняется сразу — отдельной кнопки «Сохранить» здесь нет. Организатор
            получит письмо со списком внесённых правок.
            {registration.registrationOpen
              ? ""
              : " Регистрация закрыта — правки приняты по запросу организатора."}
          </p>
        </Alert>

        {application.hasCorrections ? (
          <Alert variant="warning">
            <p className="font-medium">Организатор просит исправить</p>
            <p className="mt-1 text-sm">
              Комментарий: {application.correctionComment?.trim() || "не указан"}
            </p>
          </Alert>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Выступления, участники и педагоги</CardTitle>
            <CardDescription>
              Разверните номер, чтобы изменить его данные, состав коллектива, педагогов и
              прикреплённые файлы.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PerformanceBuilder
              applicationId={applicationId}
              application={application}
              registration={registration}
            />
          </CardContent>
        </Card>

        <ServicesCard
          applicationId={applicationId}
          application={application}
          registration={registration}
        />

        <ConsentsCard
          applicationId={applicationId}
          application={application}
          registration={registration}
        />

        <PhonogramsCard application={application} />

        <BenefitDocumentsCard application={application} />

        <ReceiptCard application={application} />

        <Card>
          <CardHeader>
            <CardTitle>Стоимость после правок</CardTitle>
            <CardDescription>
              {totalPrice
                ? "Итоговую сумму пересчитывает система."
                : "Фестиваль не назначил цен на то, что входит в заявку."}
            </CardDescription>
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
            {totalPrice ? (
              <div className="flex justify-between font-semibold">
                <span>Итого</span>
                <span>{totalPrice}</span>
              </div>
            ) : (
              <p className="text-muted-foreground">{REGULATION_PRICE_NOTE}</p>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button asChild>
            <Link to={detailTo}>
              <Check className="size-4" />
              Готово
            </Link>
          </Button>
        </div>
      </PageContent>
    </PageContainer>
  );
}
