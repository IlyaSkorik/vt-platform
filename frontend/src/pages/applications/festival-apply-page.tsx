import { RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import {
  generatePath,
  Link,
  Navigate,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router";

import {
  applicationTotalLabel,
  REGULATION_PRICE_NOTE,
  useApplication,
  useCreateApplication,
  useMyApplications,
  useRegistration,
  useSubmitApplication,
} from "@/entities/application";
import { BenefitDocumentsCard } from "@/features/application-benefit-documents";
import { ReceiptCard } from "@/features/application-receipt";
import { ConsentsCard, PerformanceBuilder, ServicesCard } from "@/features/registration-wizard";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { ROUTES } from "@/shared/config";
import {
  Alert,
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

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Произошла ошибка. Попробуйте ещё раз.";
}

/**
 * The applicant-facing Registration Wizard — a thin rendering layer over the
 * single Registration projection (`GET /public/competitions/{id}/registration`).
 * The projection supplies every choice (services, required consents, taxonomy);
 * the wizard resumes/creates a DRAFT and drives the order lifecycle. The backend
 * validates everything and computes the price.
 */
export function FestivalApplyPage(): React.JSX.Element {
  const { festivalId = "" } = useParams<{ festivalId: string }>();
  const [searchParams] = useSearchParams();
  const { data: applications, isLoading: listLoading } = useMyApplications();
  // The address bar carries whatever the link used — a readable slug or a uuid — and
  // the public projection resolves either. Applications, though, are keyed strictly
  // by the competition's uuid, so the projection is the only trustworthy source of
  // the id to create against and to match existing applications on.
  const { data: registration, isLoading: registrationLoading } = useRegistration(festivalId);
  const competitionId = registration?.competition.id ?? null;
  const createApplication = useCreateApplication();
  const [createdId, setCreatedId] = useState<string | null>(null);
  const targetApplicationId = searchParams.get("applicationId");

  const selectedApplication = useMemo(() => {
    if (!applications || competitionId === null) return null;
    // An explicit ?applicationId= opens that exact application whatever its status.
    // A submitted one is not filled in here — `WizardBody` sends it on to the edit
    // screen — but it has to be resolved first for the redirect to know where to go.
    if (targetApplicationId) {
      const exact = applications.find(
        (application) =>
          application.id === targetApplicationId && application.competitionId === competitionId,
      );
      if (exact) return exact;
    }
    // Otherwise ("Подать заявку" again) only an in-progress DRAFT is resumed; if the
    // applicant already submitted, a fresh application is started from scratch.
    return (
      applications.find(
        (application) =>
          application.competitionId === competitionId && application.status === "DRAFT",
      ) ?? null
    );
  }, [applications, competitionId, targetApplicationId]);
  const applicationId = createdId ?? selectedApplication?.id ?? null;

  if (listLoading || registrationLoading) {
    return (
      <PageContainer>
        <PageContent>
          <LoadingState label="Готовим заявку…" />
        </PageContent>
      </PageContainer>
    );
  }

  if (competitionId === null) {
    return (
      <PageContainer>
        <PageHeader>
          <PageTitle>Фестиваль не найден</PageTitle>
          <PageDescription>
            Приём заявок на этот фестиваль закрыт, либо ссылка устарела.
          </PageDescription>
        </PageHeader>
      </PageContainer>
    );
  }

  if (!applicationId) {
    return (
      <PageContainer>
        <PageHeader>
          <PageTitle>Подача заявки</PageTitle>
          <PageDescription>Создайте заявку, чтобы начать заполнение.</PageDescription>
        </PageHeader>
        <PageContent>
          {createApplication.isError ? (
            <Alert variant="danger" className="mb-4">
              {errorMessage(createApplication.error)}
            </Alert>
          ) : null}
          <Button
            loading={createApplication.isPending}
            onClick={() =>
              createApplication.mutate(competitionId, {
                onSuccess: (application) => setCreatedId(application.id),
              })
            }
          >
            Начать заявку
          </Button>
        </PageContent>
      </PageContainer>
    );
  }

  return <WizardBody applicationId={applicationId} festivalRef={festivalId} />;
}

function WizardBody({
  applicationId,
  festivalRef,
}: {
  applicationId: string;
  /** The identifier from the address bar — slug or uuid; the projection takes either. */
  festivalRef: string;
}): React.JSX.Element {
  const {
    data: application,
    isLoading: applicationLoading,
    refetch: refetchApplication,
    isFetching: isFetchingApplication,
  } = useApplication(applicationId);
  const {
    data: registration,
    isLoading: registrationLoading,
    refetch: refetchRegistration,
    isFetching: isFetchingRegistration,
  } = useRegistration(festivalRef);
  const [refreshNotice, setRefreshNotice] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  if (applicationLoading || registrationLoading || !application || !registration) {
    return (
      <PageContainer>
        <PageContent>
          <LoadingState label="Загружаем заявку…" />
        </PageContent>
      </PageContainer>
    );
  }

  // Мастер — только для черновика. Поданную заявку правят на экране редактирования:
  // здесь всё написано так, будто её ещё предстоит подать, и «Подать заявку» внизу
  // делает непонятным, дополняют существующую заявку или заводят вторую. Прежние
  // ссылки вида ?applicationId=<поданная> продолжают работать — через этот редирект.
  if (application.status !== "DRAFT") {
    return <Navigate to={generatePath(ROUTES.cabinetApplicationEdit, { applicationId })} replace />;
  }

  // Заполнение доступно пока открыта регистрация, а также после её закрытия —
  // если организатор запросил исправления/недостающие файлы.
  const canEdit = registration.registrationOpen || application.hasCorrections;
  if (!canEdit) {
    return <Navigate to={generatePath(ROUTES.cabinetApplication, { applicationId })} replace />;
  }

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>{registration.competition.title}</PageTitle>
        <PageDescription>
          Заполните заявку последовательно на одной странице.
          {registration.registrationOpen ? "" : " Регистрация закрыта."}
        </PageDescription>
      </PageHeader>
      <PageContent className="flex flex-col gap-6">
        {application.hasCorrections ? (
          <Alert variant="warning">
            <p className="font-medium">Требуется исправление</p>
            <p className="mt-1 text-sm">
              Комментарий организатора: {application.correctionComment?.trim() || "не указан"}
            </p>
          </Alert>
        ) : null}
        <PerformancesStep
          applicationId={applicationId}
          application={application}
          registration={registration}
        />
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
        <ReviewStep
          applicationId={applicationId}
          application={application}
          registration={registration}
        />
        <div className="flex flex-wrap justify-between gap-2">
          <p className="text-sm">
            <Link to={generatePath(ROUTES.cabinetApplication, { applicationId })}>
              Открыть карточку заявки
            </Link>
          </p>
          <Button
            size="sm"
            variant="primary"
            loading={isFetchingApplication || isFetchingRegistration}
            onClick={async () => {
              try {
                const [applicationResult, registrationResult] = await Promise.all([
                  refetchApplication(),
                  refetchRegistration(),
                ]);
                if (applicationResult.error || registrationResult.error) {
                  setRefreshNotice({ type: "error", text: "Не удалось обновить данные заявки" });
                  return;
                }
                setRefreshNotice({ type: "success", text: "Данные заявки обновлены" });
              } catch {
                setRefreshNotice({ type: "error", text: "Не удалось обновить данные заявки" });
              }
            }}
          >
            <RefreshCw className="size-4" />
            Обновить
          </Button>
        </div>
        {refreshNotice ? (
          <p
            className={`text-sm ${refreshNotice.type === "success" ? "text-green-600" : "text-danger"}`}
          >
            {refreshNotice.text}
          </p>
        ) : null}
      </PageContent>
    </PageContainer>
  );
}

function PerformancesStep({
  applicationId,
  application,
  registration,
}: {
  applicationId: string;
  application: ApplicationResource;
  registration: Registration;
}): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Выступления</CardTitle>
        <CardDescription>
          Каждое выступление настраивается по конфигурации фестиваля. Если у выступления есть
          стоимость, она показана в его заголовке.
        </CardDescription>
      </CardHeader>
      {/* Tighter side padding on a phone: the performance cards are cards inside this
          card, and two lots of `p-6` took a third of a 360 px screen before any content
          got a say. */}
      <CardContent className="px-3 sm:px-6">
        <PerformanceBuilder
          applicationId={applicationId}
          application={application}
          registration={registration}
        />
      </CardContent>
    </Card>
  );
}

function ReviewStep({
  applicationId,
  application,
  registration,
}: {
  applicationId: string;
  application: ApplicationResource;
  registration: Registration;
}): React.JSX.Element {
  const submit = useSubmitApplication(applicationId);
  const navigate = useNavigate();

  // Proactively mirror the backend's submit invariants so the applicant sees what
  // the festival requires before the request is rejected.
  const recordedConsents = new Set(application.consents.map((consent) => consent.code));
  const selectedServices = new Set(application.services.map((service) => service.serviceId));
  const missingConsents = registration.requiredConsents
    .filter((consent) => consent.required && !recordedConsents.has(consent.code))
    .map((consent) => consent.label);
  const missingServices = registration.additionalServices
    .filter((service) => service.required && !selectedServices.has(service.id))
    .map((service) => service.name);
  const blockers: string[] = [];
  if (application.submissions.length === 0) {
    blockers.push("Добавьте хотя бы одно выступление");
  }
  for (const consent of missingConsents) {
    blockers.push(`Требуется согласие: ${consent}`);
  }
  for (const service of missingServices) {
    blockers.push(`Требуется услуга: ${service}`);
  }
  const canSubmit = blockers.length === 0;

  const totalPrice = applicationTotalLabel(application.totalPrice);

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Проверка и подача</CardTitle>
          <CardDescription>Проверьте, что всё заполнено, и подайте заявку.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <div className="flex justify-between">
            <span>Выступлений</span>
            <span>{application.submissions.length}</span>
          </div>
          {/* Строка про услуги — только у фестиваля, который их предлагает: там, где
              каталога нет, и карточки услуг на странице нет. */}
          {registration.additionalServices.length > 0 ? (
            <div className="flex justify-between">
              <span>Услуг выбрано</span>
              <span>{application.services.length}</span>
            </div>
          ) : null}
          <div className="flex justify-between">
            <span>Согласий записано</span>
            <span>{application.consents.length}</span>
          </div>
          {/* Сумма — там, где она есть; иначе сказано, чем стоимость определяется.
              «Итого —» заставляло искать, что не заполнено, хотя не заполнять было
              нечего. Цена каждого платного выступления видна бэйджем в его заголовке. */}
          <Divider />
          {totalPrice ? (
            <div className="flex justify-between font-semibold">
              <span>Итого</span>
              <span>{totalPrice}</span>
            </div>
          ) : (
            <p className="text-muted-foreground">{REGULATION_PRICE_NOTE}</p>
          )}
          {blockers.length > 0 ? (
            <Alert variant="warning">
              <ul className="list-disc pl-4">
                {blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </Alert>
          ) : null}
          {submit.isError ? <Alert variant="danger">{errorMessage(submit.error)}</Alert> : null}
          <div className="flex justify-end">
            <Button
              disabled={!canSubmit}
              loading={submit.isPending}
              onClick={() =>
                submit.mutate(undefined, {
                  onSuccess: () => {
                    void navigate(ROUTES.cabinetApplications);
                  },
                })
              }
            >
              Подать заявку
            </Button>
          </div>
        </CardContent>
      </Card>
      <BenefitDocumentsCard application={application} />
      <ReceiptCard application={application} />
    </div>
  );
}
