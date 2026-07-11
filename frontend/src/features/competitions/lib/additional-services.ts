import type {
  _AdditionalService,
  _ParticipationFormat,
  AddAdditionalService,
  CompetitionDetail,
  PatchedUpdateAdditionalService,
} from "@/shared/api/generated/model-competitions";
import { parseAmount } from "./pricing";

export type ServiceBillingModelValue = "PER_PARTICIPANT" | "PER_PERFORMANCE";

export const DEFAULT_SERVICE_CURRENCY = "BYN";
export const DEFAULT_SERVICE_BILLING_MODEL = "PER_PARTICIPANT" as const;

export const SERVICE_BILLING_MODEL_OPTIONS: Array<{
  value: ServiceBillingModelValue;
  label: string;
}> = [
  { value: "PER_PARTICIPANT", label: "За участника" },
  { value: "PER_PERFORMANCE", label: "За номер" },
];

export function billingModelLabel(value: string | null | undefined): string {
  if (value === "PER_PERFORMANCE") return "За номер";
  return "За участника";
}

export function normalizeBillingModel(value: string | null | undefined): ServiceBillingModelValue {
  return value === "PER_PERFORMANCE" ? "PER_PERFORMANCE" : "PER_PARTICIPANT";
}

export interface AdditionalServiceFormValues {
  name: string;
  description: string;
  amount: string;
  currency: string;
  billingModel: ServiceBillingModelValue;
  participationFormatIds: string[];
  required: boolean;
  enabled: boolean;
}

export interface AdditionalServicesStats {
  total: number;
  enabledCount: number;
  requiredCount: number;
  perParticipantCount: number;
  perPerformanceCount: number;
}

export interface AdditionalServiceWarning {
  id: string;
  kind: "no-formats" | "missing-format" | "disabled-format";
  message: string;
  sectionId?: "participation-formats" | "additional-services";
}

export function emptyAdditionalServiceForm(
  preferredFormatIds: string[] = [],
): AdditionalServiceFormValues {
  return {
    name: "",
    description: "",
    amount: "",
    currency: DEFAULT_SERVICE_CURRENCY,
    billingModel: DEFAULT_SERVICE_BILLING_MODEL,
    participationFormatIds: preferredFormatIds,
    required: false,
    enabled: true,
  };
}

export function serviceToFormValues(service: _AdditionalService): AdditionalServiceFormValues {
  return {
    name: service.name,
    description: service.description ?? "",
    amount: service.amount,
    currency: service.currency || DEFAULT_SERVICE_CURRENCY,
    billingModel: normalizeBillingModel(service.billingModel),
    participationFormatIds: [...service.participationFormatIds],
    required: service.required,
    enabled: service.enabled,
  };
}

export function sortAdditionalServices(items: _AdditionalService[]): _AdditionalService[] {
  return [...items].sort((left, right) => {
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }
    return left.name.localeCompare(right.name, "ru");
  });
}

export function filterAdditionalServices(
  items: _AdditionalService[],
  search: string,
  formats: _ParticipationFormat[],
): _AdditionalService[] {
  const query = search.trim().toLowerCase();
  const sorted = sortAdditionalServices(items);
  if (query.length === 0) return sorted;

  const formatNames = new Map(formats.map((item) => [item.id, item.name]));
  return sorted.filter((item) => {
    const formatLabels = item.participationFormatIds
      .map((id) => formatNames.get(id) ?? id)
      .join(" ");
    const haystack =
      `${item.name} ${item.description ?? ""} ${item.amount} ${billingModelLabel(item.billingModel)} ${formatLabels}`.toLowerCase();
    return haystack.includes(query);
  });
}

export function nextAdditionalServiceSortOrder(items: _AdditionalService[]): number {
  if (items.length === 0) return 0;
  return Math.max(...items.map((item) => item.sortOrder)) + 1;
}

export function duplicateAdditionalServiceDraft(
  service: _AdditionalService,
): AdditionalServiceFormValues {
  return {
    ...serviceToFormValues(service),
    name: `${service.name} (копия)`,
    enabled: service.enabled,
  };
}

export function validateAdditionalServiceForm(
  values: AdditionalServiceFormValues,
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!values.name.trim()) {
    errors.name = "Обязательное поле";
  }
  if (parseAmount(values.amount) == null) {
    errors.amount = "Введите цену больше нуля";
  }
  if (values.participationFormatIds.length === 0) {
    errors.participationFormatIds = "Выберите хотя бы один формат участия";
  }
  return errors;
}

export function createAdditionalServicePayload(
  values: AdditionalServiceFormValues,
  sortOrder: number,
): AddAdditionalService {
  const description = values.description.trim();
  const amount = parseAmount(values.amount);
  return {
    name: values.name.trim(),
    amount: amount != null ? amount.toFixed(2) : values.amount.trim(),
    currency: values.currency.trim() || DEFAULT_SERVICE_CURRENCY,
    description: description.length > 0 ? description : null,
    billingModel: values.billingModel,
    participationFormatIds: values.participationFormatIds,
    required: values.required,
    enabled: values.enabled,
    sortOrder,
  };
}

export function updateAdditionalServicePayload(
  values: AdditionalServiceFormValues,
  sortOrder: number,
): PatchedUpdateAdditionalService {
  const description = values.description.trim();
  const amount = parseAmount(values.amount);
  return {
    name: values.name.trim(),
    amount: amount != null ? amount.toFixed(2) : values.amount.trim(),
    currency: values.currency.trim() || DEFAULT_SERVICE_CURRENCY,
    description: description.length > 0 ? description : null,
    billingModel: values.billingModel,
    participationFormatIds: values.participationFormatIds,
    required: values.required,
    sortOrder,
  };
}

export function buildAdditionalServiceReorderUpdates(
  orderedIds: string[],
  items: _AdditionalService[],
): Array<{ serviceId: string; payload: PatchedUpdateAdditionalService }> {
  const byId = new Map(items.map((item) => [item.id, item]));
  const updates: Array<{ serviceId: string; payload: PatchedUpdateAdditionalService }> = [];

  orderedIds.forEach((serviceId, index) => {
    const item = byId.get(serviceId);
    if (!item || item.sortOrder === index) return;
    updates.push({
      serviceId,
      payload: updateAdditionalServicePayload(serviceToFormValues(item), index),
    });
  });

  return updates;
}

export function moveIdBefore(orderedIds: string[], draggedId: string, targetId: string): string[] {
  if (draggedId === targetId) return orderedIds;
  const withoutDragged = orderedIds.filter((id) => id !== draggedId);
  const targetIndex = withoutDragged.indexOf(targetId);
  if (targetIndex === -1) return orderedIds;
  const next = [...withoutDragged];
  next.splice(targetIndex, 0, draggedId);
  return next;
}

export function resolveServiceFormatLabels(
  service: _AdditionalService,
  formats: _ParticipationFormat[],
): string[] {
  const byId = new Map(formats.map((item) => [item.id, item.name]));
  return service.participationFormatIds.map((id) => byId.get(id) ?? "Неизвестный формат");
}

export function buildAdditionalServicesStats(
  services: _AdditionalService[],
): AdditionalServicesStats {
  return {
    total: services.length,
    enabledCount: services.filter((item) => item.enabled).length,
    requiredCount: services.filter((item) => item.required).length,
    perParticipantCount: services.filter(
      (item) => normalizeBillingModel(item.billingModel) === "PER_PARTICIPANT",
    ).length,
    perPerformanceCount: services.filter(
      (item) => normalizeBillingModel(item.billingModel) === "PER_PERFORMANCE",
    ).length,
  };
}

export function buildAdditionalServiceWarnings(
  competition: CompetitionDetail,
): AdditionalServiceWarning[] {
  const warnings: AdditionalServiceWarning[] = [];
  const formats = competition.participationFormats;
  const formatById = new Map(formats.map((item) => [item.id, item]));

  if (formats.length === 0 && competition.additionalServices.length > 0) {
    warnings.push({
      id: "no-formats",
      kind: "no-formats",
      message: "Нет форматов участия — услуги не к чему привязать.",
      sectionId: "participation-formats",
    });
  }

  for (const service of competition.additionalServices) {
    for (const formatId of service.participationFormatIds) {
      const format = formatById.get(formatId);
      if (!format) {
        warnings.push({
          id: `missing-${service.id}-${formatId}`,
          kind: "missing-format",
          message: `«${service.name}»: формат недоступен или удалён.`,
          sectionId: "additional-services",
        });
        continue;
      }
      if (!format.enabled) {
        warnings.push({
          id: `disabled-${service.id}-${formatId}`,
          kind: "disabled-format",
          message: `«${service.name}» привязана к выключенному формату «${format.name}».`,
          sectionId: "participation-formats",
        });
      }
    }
  }

  return warnings;
}

export function formatServicePrice(amount: string, currency: string): string {
  const parsed = Number(amount);
  if (!Number.isFinite(parsed)) return `${amount} ${currency}`;
  return `${parsed.toFixed(2)} ${currency}`;
}

export function exampleServiceTotal(
  amount: string,
  participantCount: number,
  billingModel: ServiceBillingModelValue,
): string {
  const parsed = parseAmount(amount);
  if (parsed == null) return "—";
  if (billingModel === "PER_PERFORMANCE") {
    return parsed.toFixed(2);
  }
  return (parsed * participantCount).toFixed(2);
}
