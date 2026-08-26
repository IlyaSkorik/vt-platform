import type {
  _ContactProfileOverride,
  _ContactsConfig,
  _EmergencyContacts,
  _SupportingOrganizationOverride,
  _TeamContact,
  _VenueDetails,
  CompetitionDetail,
  UpdateContactsConfig as UpdateContactsConfiguration,
} from "@/shared/api/generated/model-competitions";

export function defaultContactsConfig(): _ContactsConfig {
  return {
    useOrganizationContacts: true,
    override: emptyOverride(),
    useOrganizationSupporter: true,
    supporterOverride: emptySupporterOverride(),
    teamContacts: [],
    emergency: emptyEmergency(),
    venueDetails: emptyVenueDetails(),
  };
}

export function emptyOverride(): _ContactProfileOverride {
  return {
    organizationName: null,
    phone: null,
    email: null,
    website: null,
    address: null,
    vk: null,
    instagram: null,
    telegram: null,
  };
}

export function emptySupporterOverride(): _SupportingOrganizationOverride {
  return {
    name: null,
    phone: null,
    email: null,
    website: null,
    address: null,
    vk: null,
    instagram: null,
    telegram: null,
    legalInformation: null,
  };
}

export function emptyEmergency(): _EmergencyContacts {
  return { phone: null, email: null, notes: null };
}

export function emptyVenueDetails(): _VenueDetails {
  return {
    city: null,
    country: null,
    googleMapsUrl: null,
    yandexMapsUrl: null,
    directions: null,
  };
}

export function resolveContactsConfig(competition: CompetitionDetail): _ContactsConfig {
  return competition.contactsConfig ?? defaultContactsConfig();
}

export function contactsConfigToPayload(config: _ContactsConfig): UpdateContactsConfiguration {
  return {
    useOrganizationContacts: config.useOrganizationContacts,
    override: {
      organizationName: blankToNull(config.override.organizationName),
      phone: blankToNull(config.override.phone),
      email: blankToNull(config.override.email),
      website: blankToNull(config.override.website),
      address: blankToNull(config.override.address),
      vk: blankToNull(config.override.vk),
      instagram: blankToNull(config.override.instagram),
      telegram: blankToNull(config.override.telegram),
    },
    useOrganizationSupporter: config.useOrganizationSupporter,
    supporterOverride: {
      name: blankToNull(config.supporterOverride.name),
      phone: blankToNull(config.supporterOverride.phone),
      email: blankToNull(config.supporterOverride.email),
      website: blankToNull(config.supporterOverride.website),
      address: blankToNull(config.supporterOverride.address),
      vk: blankToNull(config.supporterOverride.vk),
      instagram: blankToNull(config.supporterOverride.instagram),
      telegram: blankToNull(config.supporterOverride.telegram),
      legalInformation: blankToNull(config.supporterOverride.legalInformation),
    },
    teamContacts: sortTeamContacts(config.teamContacts).map((item, index) => ({
      ...item,
      name: item.name.trim(),
      position: blankToNull(item.position),
      phone: blankToNull(item.phone),
      email: blankToNull(item.email),
      description: blankToNull(item.description),
      sortOrder: index,
    })),
    emergency: {
      phone: blankToNull(config.emergency.phone),
      email: blankToNull(config.emergency.email),
      notes: blankToNull(config.emergency.notes),
    },
    venueDetails: {
      city: blankToNull(config.venueDetails.city),
      country: blankToNull(config.venueDetails.country),
      googleMapsUrl: blankToNull(config.venueDetails.googleMapsUrl),
      yandexMapsUrl: blankToNull(config.venueDetails.yandexMapsUrl),
      directions: blankToNull(config.venueDetails.directions),
    },
  };
}

export function sortTeamContacts(contacts: _TeamContact[]): _TeamContact[] {
  return [...contacts].sort(
    (a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name, "ru"),
  );
}

export function createTeamContactDraft(sortOrder: number): _TeamContact {
  return {
    id: crypto.randomUUID(),
    name: "",
    position: null,
    phone: null,
    email: null,
    description: null,
    sortOrder,
  };
}

export function moveTeamContactBefore(
  contacts: _TeamContact[],
  draggedId: string,
  targetId: string,
): _TeamContact[] {
  if (draggedId === targetId) return contacts;
  const ordered = sortTeamContacts(contacts);
  const ids = ordered.map((item) => item.id);
  if (!ids.includes(draggedId) || !ids.includes(targetId)) return contacts;
  const withoutDragged = ids.filter((id) => id !== draggedId);
  const targetIndex = withoutDragged.indexOf(targetId);
  if (targetIndex === -1) return contacts;
  const nextIds = [...withoutDragged];
  nextIds.splice(targetIndex, 0, draggedId);
  const byId = new Map(ordered.map((item) => [item.id, item]));
  return nextIds.map((id, index) => {
    const item = byId.get(id);
    if (!item) throw new Error(`Missing team contact ${id}`);
    return { ...item, sortOrder: index };
  });
}

export interface ContactsSummary {
  organizationProfile: boolean;
  competitionContacts: boolean;
  emergency: boolean;
}

/** What the «Контакты» section itself covers — the venue is edited under «Общее». */
export function buildContactsSummary(
  config: _ContactsConfig,
  organizationName: string | null | undefined,
): ContactsSummary {
  return {
    organizationProfile: Boolean(organizationName?.trim()) || config.useOrganizationContacts,
    competitionContacts: config.teamContacts.length > 0,
    emergency:
      Boolean(config.emergency.phone?.trim()) ||
      Boolean(config.emergency.email?.trim()) ||
      Boolean(config.emergency.notes?.trim()),
  };
}

function blankToNull(value: string | null | undefined): string | null {
  if (value == null) return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}
