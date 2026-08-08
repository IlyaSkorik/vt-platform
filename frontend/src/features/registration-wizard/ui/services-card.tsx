import { useRemoveService, useSelectService } from "@/entities/application";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui";

/**
 * The order's additional services, from the festival's own catalogue.
 *
 * Shared by the wizard and the post-submission edit screen: an applicant who forgot
 * to book a rehearsal slot changes it in exactly the same place afterwards, and the
 * backend applies the same rules either way (a required service cannot be dropped,
 * and the quantity is derived from the billing model, never sent from here).
 */
export function ServicesCard({
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
