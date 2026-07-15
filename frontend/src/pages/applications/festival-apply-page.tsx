import { useEffect, useMemo, useRef, useState } from "react";
import { generatePath, Link, useParams } from "react-router";

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
  const { data: applications, isLoading: listLoading } = useMyApplications();
  const createApplication = useCreateApplication();
  const [createdId, setCreatedId] = useState<string | null>(null);

  const existingDraft = useMemo(
    () =>
      applications?.find(
        (application) => application.competitionId === festivalId && application.status === "DRAFT",
      ),
    [applications, festivalId],
  );
  const applicationId = createdId ?? existingDraft?.id ?? null;

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
  const { data: application, isLoading: applicationLoading } = useApplication(applicationId);
  const { data: registration, isLoading: registrationLoading } = useRegistration(competitionId);

  if (applicationLoading || registrationLoading || !application || !registration) {
    return (
      <PageContainer>
        <PageContent>
          <LoadingState label="Загружаем заявку…" />
        </PageContent>
      </PageContainer>
    );
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
        <PerformancesStep applicationId={applicationId} application={application} registration={registration} />
        <ServicesStep applicationId={applicationId} application={application} registration={registration} />
        <ConsentsStep applicationId={applicationId} application={application} registration={registration} />
        <ReviewStep applicationId={applicationId} application={application} registration={registration} />
        <p className="text-sm">
          <Link to={generatePath(ROUTES.cabinetApplication, { applicationId })}>
            Открыть карточку заявки
          </Link>
        </p>
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
            <div>
              <Button
                disabled={!canSubmit}
                loading={submit.isPending}
                onClick={() => submit.mutate()}
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
      <ReceiptCard application={application} />
    </div>
  );
}
