import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  generatePath,
  Link,
  Navigate,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router";

import {
  useApplication,
  useCreateApplication,
  useMyApplications,
  useRecordConsents,
  useRegistration,
  useRemoveService,
  useSelectService,
  useSubmitApplication,
} from "@/entities/application";
import { BenefitDocumentsCard } from "@/features/application-benefit-documents";
import { ReceiptCard } from "@/features/application-receipt";
import { PerformanceBuilder } from "@/features/registration-wizard";
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
  Checkbox,
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
  const createApplication = useCreateApplication();
  const [createdId, setCreatedId] = useState<string | null>(null);
  const targetApplicationId = searchParams.get("applicationId");

  const selectedApplication = useMemo(() => {
    if (!applications) return null;
    // An explicit ?applicationId= (e.g. "edit" from an application card) opens that
    // exact application regardless of status, so an already-submitted one stays editable.
    if (targetApplicationId) {
      const exact = applications.find(
        (application) =>
          application.id === targetApplicationId && application.competitionId === festivalId,
      );
      if (exact) return exact;
    }
    // Otherwise ("Подать заявку" again) only an in-progress DRAFT is resumed; if the
    // applicant already submitted, a fresh application is started from scratch.
    return (
      applications.find(
        (application) => application.competitionId === festivalId && application.status === "DRAFT",
      ) ?? null
    );
  }, [applications, festivalId, targetApplicationId]);
  const applicationId = createdId ?? selectedApplication?.id ?? null;

  if (listLoading) {
    return (
      <PageContainer>
        <PageContent>
          <LoadingState label="Готовим заявку…" />
        </PageContent>
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
              createApplication.mutate(festivalId, {
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

  return <WizardBody applicationId={applicationId} competitionId={festivalId} />;
}

function WizardBody({
  applicationId,
  competitionId,
}: {
  applicationId: string;
  competitionId: string;
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
  } = useRegistration(competitionId);
  const [refreshNotice, setRefreshNotice] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const isEditableStatus = application?.status === "DRAFT" || application?.status === "SUBMITTED";

  if (applicationLoading || registrationLoading || !application || !registration) {
    return (
      <PageContainer>
        <PageContent>
          <LoadingState label="Загружаем заявку…" />
        </PageContent>
      </PageContainer>
    );
  }

  // Редактирование доступно пока открыта регистрация, а также после её
  // закрытия — если организатор запросил исправления/недостающие файлы.
  const canEdit = (registration.registrationOpen || application.hasCorrections) && isEditableStatus;
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
        <ServicesStep
          applicationId={applicationId}
          application={application}
          registration={registration}
        />
        <ConsentsStep
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
          Каждое выступление настраивается по конфигурации фестиваля; система рассчитывает его
          стоимость.
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
  );
}

function ServicesStep({
  applicationId,
  application,
  registration,
}: {
  applicationId: string;
  application: ApplicationResource;
  registration: Registration;
}): React.JSX.Element {
  const selectService = useSelectService(applicationId);
  const removeService = useRemoveService(applicationId);
  const selectedIds = new Set(application.services.map((service) => service.serviceId));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Дополнительные услуги</CardTitle>
        <CardDescription>
          Услуги фестиваля из каталога. Их стоимость учитывается в итоговой сумме.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {registration.additionalServices.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Фестиваль не предлагает дополнительных услуг.
          </p>
        ) : (
          registration.additionalServices.map((service) => {
            const selected = selectedIds.has(service.id);
            return (
              <div key={service.id} className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{service.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {service.amount} {service.currency}
                    {service.required ? " · обязательно" : ""}
                  </p>
                </div>
                {selected ? (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={service.required}
                    loading={removeService.isPending}
                    onClick={() => removeService.mutate(service.id)}
                  >
                    Убрать
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={selectService.isPending}
                    onClick={() => selectService.mutate({ serviceId: service.id, quantity: 1 })}
                  >
                    Добавить
                  </Button>
                )}
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}

function ConsentsStep({
  applicationId,
  application,
  registration,
}: {
  applicationId: string;
  application: ApplicationResource;
  registration: Registration;
}): React.JSX.Element {
  const recordConsents = useRecordConsents(applicationId);
  const required = registration.requiredConsents.filter((consent) => consent.required);
  const recordedCodes = new Set(application.consents.map((consent) => consent.code));
  const [accepted, setAccepted] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(required.map((consent) => [consent.code, recordedCodes.has(consent.code)])),
  );
  const autosavedSignature = useRef<string | null>(null);

  useEffect(() => {
    if (required.length === 0 || recordConsents.isPending) {
      return;
    }
    const signature = required
      .map((consent) => `${consent.code}:${accepted[consent.code] === true ? "1" : "0"}`)
      .sort()
      .join("|");
    if (autosavedSignature.current === signature) {
      return;
    }
    autosavedSignature.current = signature;
    const handle = setTimeout(() => {
      recordConsents.mutate({
        consents: required
          .filter((consent) => accepted[consent.code] === true)
          .map((consent) => ({ code: consent.code, version: "v1" })),
      });
    }, 250);
    return () => clearTimeout(handle);
  }, [accepted, recordConsents, required]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Согласия</CardTitle>
          <CardDescription>Обязательные согласия определяются фестивалем.</CardDescription>
        </div>
        <span className="min-h-5 text-xs text-muted-foreground">
          {recordConsents.isPending ? "Сохраняем…" : ""}
        </span>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {required.length === 0 ? (
          <p className="text-sm text-muted-foreground">Фестиваль не требует отдельных согласий.</p>
        ) : (
          required.map((consent) => (
            <Checkbox
              key={consent.code}
              checked={accepted[consent.code] === true}
              onCheckedChange={(checked) =>
                setAccepted((prev) => ({ ...prev, [consent.code]: checked === true }))
              }
              label={consent.label}
            />
          ))
        )}
        {recordConsents.isError ? (
          <Alert variant="danger">{errorMessage(recordConsents.error)}</Alert>
        ) : null}
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

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Проверка и подача</CardTitle>
          <CardDescription>Итоговую сумму рассчитывает система.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <div className="flex justify-between">
            <span>Выступлений</span>
            <span>{application.submissions.length}</span>
          </div>
          <div className="flex justify-between">
            <span>Услуг выбрано</span>
            <span>{application.services.length}</span>
          </div>
          <div className="flex justify-between">
            <span>Согласий записано</span>
            <span>{application.consents.length}</span>
          </div>
          <Divider />
          <div className="flex justify-between font-semibold">
            <span>Итого</span>
            <span>
              {application.totalPrice
                ? `${application.totalPrice.totalAmount} ${application.totalPrice.currency}`
                : "—"}
            </span>
          </div>
          {application.status === "DRAFT" && blockers.length > 0 ? (
            <Alert variant="warning">
              <ul className="list-disc pl-4">
                {blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </Alert>
          ) : null}
          {submit.isError ? <Alert variant="danger">{errorMessage(submit.error)}</Alert> : null}
          {application.status === "DRAFT" ? (
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
          ) : (
            <Alert variant="success">
              Заявка отправлена. <Link to={ROUTES.cabinetApplications}>Перейти к моим заявкам</Link>
              .
            </Alert>
          )}
        </CardContent>
      </Card>
      <BenefitDocumentsCard application={application} />
      <ReceiptCard application={application} />
    </div>
  );
}
