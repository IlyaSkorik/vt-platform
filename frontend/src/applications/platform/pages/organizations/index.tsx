import { useState } from "react";

import {
  type PlatformOrganization,
  refusalMessage,
  useConnectOrganization,
  usePlatformOrganizations,
  useUpdateOrganization,
} from "@/applications/platform/api/platform-api";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  LoadingState,
  toast,
} from "@/shared/ui";

function ConnectForm(): React.JSX.Element {
  const connect = useConnectOrganization();
  const [name, setName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [commissionPercent, setCommissionPercent] = useState("0");
  const [slug, setSlug] = useState("");

  const submit = (event: React.FormEvent): void => {
    event.preventDefault();
    connect.mutate(
      {
        name: name.trim(),
        ownerEmail: ownerEmail.trim(),
        commissionPercent: commissionPercent.trim() || "0",
        ...(slug.trim() ? { slug: slug.trim() } : {}),
      },
      {
        onSuccess: (organization) => {
          toast.success(`«${organization.name}» подключена, приглашение владельцу отправлено`);
          setName("");
          setOwnerEmail("");
          setCommissionPercent("0");
          setSlug("");
        },
        onError: async (error) => {
          toast.error(await refusalMessage(error, "Не удалось подключить организацию"));
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Подключить организацию</CardTitle>
        <CardDescription>
          Владелец получит письмо со ссылкой-приглашением: приняв его, он становится OWNER своей
          организации и дальше управляет ею сам. Адрес в URL можно не заполнять — он будет построен
          из названия.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={submit}>
          <Input
            label="Название"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Например: Звёздный дождь"
          />
          <Input
            label="Почта владельца"
            type="email"
            required
            value={ownerEmail}
            onChange={(event) => setOwnerEmail(event.target.value)}
            placeholder="director@example.com"
          />
          <Input
            label="Комиссия платформы, %"
            inputMode="decimal"
            value={commissionPercent}
            onChange={(event) => setCommissionPercent(event.target.value)}
            description="Доля организационного взноса, которую организация должна платформе"
          />
          <Input
            label="Адрес в URL (необязательно)"
            value={slug}
            onChange={(event) => setSlug(event.target.value)}
            placeholder="zvezdnyy-dozhd"
          />
          <div className="sm:col-span-2">
            <Button type="submit" loading={connect.isPending}>
              Подключить и отправить приглашение
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function OrganizationCard({
  organization,
}: {
  organization: PlatformOrganization;
}): React.JSX.Element {
  const update = useUpdateOrganization();
  const [commission, setCommission] = useState(organization.commissionPercent);
  const suspended = organization.status === "SUSPENDED";

  const saveCommission = (): void => {
    update.mutate(
      { id: organization.id, commissionPercent: commission.trim() },
      {
        onSuccess: (saved) => {
          setCommission(saved.commissionPercent);
          toast.success("Ставка комиссии сохранена");
        },
        onError: async (error) => {
          toast.error(await refusalMessage(error, "Не удалось изменить ставку"));
        },
      },
    );
  };

  const toggleStatus = (): void => {
    update.mutate(
      { id: organization.id, status: suspended ? "ACTIVE" : "SUSPENDED" },
      {
        onSuccess: () =>
          toast.success(suspended ? "Организация возобновлена" : "Организация приостановлена"),
        onError: async (error) => {
          toast.error(await refusalMessage(error, "Не удалось изменить статус"));
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>{organization.name}</CardTitle>
          <Badge variant={suspended ? "warning" : "success"}>
            {suspended ? "Приостановлена" : "Активна"}
          </Badge>
        </div>
        <CardDescription>/{organization.slug}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <Input
          label="Комиссия, %"
          inputMode="decimal"
          className="sm:max-w-40"
          value={commission}
          onChange={(event) => setCommission(event.target.value)}
        />
        <Button
          variant="outline"
          loading={update.isPending}
          disabled={commission.trim() === organization.commissionPercent}
          onClick={saveCommission}
        >
          Сохранить ставку
        </Button>
        <Button variant="ghost" loading={update.isPending} onClick={toggleStatus}>
          {suspended ? "Возобновить" : "Приостановить"}
        </Button>
      </CardContent>
    </Card>
  );
}

/**
 * The connected organizations, and the terms each runs under.
 *
 * Connecting one and handing someone the keys to it are the same action here:
 * an organization nobody can administer is not connected in any useful sense.
 */
export function PlatformOrganizationsPage(): React.JSX.Element {
  const organizations = usePlatformOrganizations();

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-semibold text-2xl">Организации</h1>
        <p className="text-muted-foreground text-sm">
          Кто проводит фестивали на платформе и на каких условиях.
        </p>
      </header>

      <ConnectForm />

      {organizations.isLoading ? <LoadingState label="Загрузка организаций" /> : null}

      {organizations.isError ? (
        <EmptyState
          title="Не удалось загрузить организации"
          description="Проверьте доступ к консоли платформы и повторите попытку."
        />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {(organizations.data ?? []).map((organization) => (
          <OrganizationCard key={organization.id} organization={organization} />
        ))}
      </div>
    </div>
  );
}
