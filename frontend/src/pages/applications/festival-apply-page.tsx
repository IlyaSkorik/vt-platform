import { useMemo, useState } from "react";
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
import { PerformanceBuilder } from "@/features/registration-wizard";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
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
  Checkbox,
  Divider,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
} from "@/shared/ui";

const STEPS = ["Выступления", "Услуги", "Согласия", "Проверка"] as const;

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
  const [step, setStep] = useState(0);

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
          Шаг {step + 1} из {STEPS.length}: {STEPS[step]}
          {registration.registrationOpen ? "" : " · регистрация закрыта"}
        </PageDescription>
      </PageHeader>
      <PageContent>
        <div className="mb-6 flex flex-wrap gap-2">
          {STEPS.map((label, index) => (
            <Badge
              key={label}
              variant={index === step ? "primary" : index < step ? "success" : "neutral"}
            >
              {index + 1}. {label}
            </Badge>
          ))}
        </div>

        {step === 0 ? (
          <PerformancesStep
            applicationId={applicationId}
            application={application}
            registration={registration}
          />
        ) : null}
        {step === 1 ? (
          <ServicesStep
            applicationId={applicationId}
            application={application}
            registration={registration}
          />
        ) : null}
        {step === 2 ? (
          <ConsentsStep
            applicationId={applicationId}
            application={application}
            registration={registration}
          />
        ) : null}
        {step === 3 ? <ReviewStep applicationId={applicationId} application={application} /> : null}

        <div className="mt-6 flex justify-between">
          <Button
            variant="ghost"
            size="sm"
            disabled={step === 0}
            onClick={() => setStep((value) => Math.max(0, value - 1))}
          >
            Назад
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={step === STEPS.length - 1}
            onClick={() => setStep((value) => Math.min(STEPS.length - 1, value + 1))}
          >
            Далее
          </Button>
        </div>

        <p className="mt-6 text-sm">
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
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});

  const allChecked = required.every(
    (consent) => accepted[consent.code] || recordedCodes.has(consent.code),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Согласия</CardTitle>
        <CardDescription>Обязательные согласия определяются фестивалем.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {required.length === 0 ? (
          <p className="text-sm text-muted-foreground">Фестиваль не требует отдельных согласий.</p>
        ) : (
          required.map((consent) => (
            <Checkbox
              key={consent.code}
              checked={accepted[consent.code] || recordedCodes.has(consent.code)}
              onCheckedChange={(checked) =>
                setAccepted((prev) => ({ ...prev, [consent.code]: checked === true }))
              }
              label={consent.label}
            />
          ))
        )}
        {required.length > 0 ? (
          <div>
            <Button
              size="sm"
              disabled={!allChecked}
              loading={recordConsents.isPending}
              onClick={() =>
                recordConsents.mutate({
                  consents: required.map((consent) => ({ code: consent.code, version: "v1" })),
                })
              }
            >
              Сохранить согласия
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ReviewStep({
  applicationId,
  application,
}: {
  applicationId: string;
  application: ApplicationResource;
}): React.JSX.Element {
  const submit = useSubmitApplication(applicationId);
  return (
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
        {submit.isError ? <Alert variant="danger">{errorMessage(submit.error)}</Alert> : null}
        {application.status === "DRAFT" ? (
          <div>
            <Button loading={submit.isPending} onClick={() => submit.mutate()}>
              Подать заявку
            </Button>
          </div>
        ) : (
          <Alert variant="success">
            Заявка отправлена. <Link to={ROUTES.cabinetApplications}>Перейти к моим заявкам</Link>.
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
