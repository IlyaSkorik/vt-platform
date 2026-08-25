import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, Check, Network } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { applyProblemToForm } from "@/features/auth";
import {
  formValuesToUpdate,
  ORGANIZATION_PROFILE_FIELDS,
  type OrganizationProfile,
  type OrganizationProfileFormValues,
  organizationProfileSchema,
  profileToFormValues,
  useOrganizationProfileQuery,
  useUpdateOrganizationProfileMutation,
} from "@/features/organization";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  Input,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageSection,
  PageTitle,
  Textarea,
  toast,
} from "@/shared/ui";

export function StaffOrganizationPage(): React.JSX.Element {
  const profileQuery = useOrganizationProfileQuery();

  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>Организация</PageTitle>
        <PageDescription>Профиль и структура организации.</PageDescription>
      </PageHeader>
      <PageContent className="space-y-8">
        {profileQuery.isLoading ? (
          <LoadingState label="Загружаем профиль организации…" />
        ) : profileQuery.isError || profileQuery.data == null ? (
          <Alert variant="danger" title="Не удалось загрузить профиль организации">
            Обновите страницу и попробуйте снова.
          </Alert>
        ) : (
          <OrganizationProfileForm profile={profileQuery.data} />
        )}

        <PageSection
          title="Структура организации"
          description="Подразделения и связи внутри организации."
        >
          <EmptyState
            icon={<Network aria-hidden="true" />}
            title="Скоро"
            description="Раздел со структурой организации появится в одном из ближайших обновлений."
          />
        </PageSection>
      </PageContent>
    </PageContainer>
  );
}

interface OrganizationProfileFormProps {
  profile: OrganizationProfile;
}

function OrganizationProfileForm({ profile }: OrganizationProfileFormProps): React.JSX.Element {
  const updateProfile = useUpdateOrganizationProfileMutation();
  const [formError, setFormError] = useState<string | null>(null);
  const [justSaved, setJustSaved] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<OrganizationProfileFormValues>({
    resolver: zodResolver(organizationProfileSchema),
    defaultValues: profileToFormValues(profile),
    mode: "onBlur",
  });

  // Re-seed the form whenever a fresh profile arrives (e.g. after a background refetch).
  useEffect(() => {
    reset(profileToFormValues(profile));
  }, [profile, reset]);

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const saved = await updateProfile.mutateAsync(formValuesToUpdate(values));
      reset(profileToFormValues(saved));
      setJustSaved(true);
      window.setTimeout(() => setJustSaved(false), 2000);
      toast.success("Профиль сохранён");
    } catch (error) {
      const message = applyProblemToForm<OrganizationProfileFormValues>(error, {
        setError,
        knownFields: [...ORGANIZATION_PROFILE_FIELDS],
      });
      if (message) {
        setFormError(message);
      }
      toast.error("Не удалось сохранить профиль");
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6">
      {formError ? (
        <Alert variant="danger" title="Не удалось сохранить изменения">
          {formError}
        </Alert>
      ) : null}

      <PageSection
        title="Профиль организации"
        description="Название и контактные данные организации."
      >
        <Card className="shadow-none">
          <CardContent className="space-y-6 pt-6">
            <div className="flex flex-wrap items-center gap-3">
              <span className="flex size-11 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <Building2 aria-hidden="true" className="size-5" />
              </span>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Идентификатор</p>
                <Badge variant="secondary">{profile.slug}</Badge>
              </div>
            </div>

            <Input
              label="Название организации"
              required
              error={errors.name?.message}
              {...register("name")}
            />

            <div className="grid gap-4 md:grid-cols-2">
              <Input label="Телефон" error={errors.phone?.message} {...register("phone")} />
              <Input
                label="Email"
                type="email"
                error={errors.email?.message}
                {...register("email")}
              />
              <Input
                label="Веб-сайт"
                placeholder="https://…"
                error={errors.website?.message}
                {...register("website")}
              />
              <Input label="Адрес" error={errors.address?.message} {...register("address")} />
            </div>
          </CardContent>
        </Card>
      </PageSection>

      <PageSection
        title="Социальные сети"
        description="Ссылки на официальные аккаунты организации."
      >
        <Card className="shadow-none">
          <CardContent className="grid gap-4 pt-6 md:grid-cols-3">
            <Input label="ВКонтакте" error={errors.vk?.message} {...register("vk")} />
            <Input label="Instagram" error={errors.instagram?.message} {...register("instagram")} />
            <Input label="Telegram" error={errors.telegram?.message} {...register("telegram")} />
          </CardContent>
        </Card>
      </PageSection>

      <PageSection
        title="Юридическая информация"
        description="Реквизиты и правовые сведения об организации."
      >
        <Card className="shadow-none">
          <CardContent className="pt-6">
            <Textarea
              label="Юридическая информация"
              rows={5}
              error={errors.legalInformation?.message}
              {...register("legalInformation")}
            />
          </CardContent>
        </Card>
      </PageSection>

      {/* The second entity, optional. Its own section rather than extra fields in
          the ones above: it is a different legal person, and mixing its phone in
          with the organizer's would be exactly the confusion naming it prevents. */}
      <PageSection
        title="При поддержке"
        description="Организация, при поддержке которой проходят фестивали, если по документам организатор — одно лицо, а проводит их другое. Блок необязательный: заполните название, и он появится на странице фестиваля."
      >
        <Card className="shadow-none">
          <CardContent className="space-y-6 pt-6">
            <Input
              label="Название организации"
              placeholder="Например, ГУ «Дворец культуры»"
              error={errors.supporterName?.message}
              {...register("supporterName")}
            />

            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="Телефон"
                error={errors.supporterPhone?.message}
                {...register("supporterPhone")}
              />
              <Input
                label="Email"
                type="email"
                error={errors.supporterEmail?.message}
                {...register("supporterEmail")}
              />
              <Input
                label="Веб-сайт"
                placeholder="https://…"
                error={errors.supporterWebsite?.message}
                {...register("supporterWebsite")}
              />
              <Input
                label="Адрес"
                error={errors.supporterAddress?.message}
                {...register("supporterAddress")}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <Input
                label="ВКонтакте"
                error={errors.supporterVk?.message}
                {...register("supporterVk")}
              />
              <Input
                label="Instagram"
                error={errors.supporterInstagram?.message}
                {...register("supporterInstagram")}
              />
              <Input
                label="Telegram"
                error={errors.supporterTelegram?.message}
                {...register("supporterTelegram")}
              />
            </div>

            <Textarea
              label="Юридическая информация"
              description="Реквизиты именно этой организации — они не совпадают с реквизитами организатора."
              rows={5}
              error={errors.supporterLegalInformation?.message}
              {...register("supporterLegalInformation")}
            />
          </CardContent>
        </Card>
      </PageSection>

      <div className="flex justify-end">
        <Button
          type="submit"
          loading={isSubmitting}
          disabled={!isDirty && !justSaved}
          variant={justSaved ? "success" : "primary"}
          leftIcon={justSaved ? <Check aria-hidden="true" /> : undefined}
        >
          {justSaved ? "Сохранено" : "Сохранить"}
        </Button>
      </div>
    </form>
  );
}
