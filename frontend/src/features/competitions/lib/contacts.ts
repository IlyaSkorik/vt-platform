import type {
  _ContactProfileOverride,
  _ContactsConfig,
  _EmergencyContacts,
  _TeamContact,
  _VenueDetails,
  CompetitionDetail,
  UpdateContactsConfiguration,
} from "@/shared/api/generated/model-competitions";

export function defaultContactsConfig(): _ContactsConfig {
  return {
    useOrganizationContacts: true,
    override: emptyOverride(),
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
  venue: boolean;
  emergency: boolean;
}

export function buildContactsSummary(
  competition: CompetitionDetail,
  config: _ContactsConfig,
  organizationName: string | null | undefined,
): ContactsSummary {
  const venueName = competition.venue?.name?.trim();
  const hasVenueExtras =
    Boolean(config.venueDetails.city?.trim()) ||
    Boolean(config.venueDetails.country?.trim()) ||
    Boolean(config.venueDetails.googleMapsUrl?.trim()) ||
    Boolean(config.venueDetails.yandexMapsUrl?.trim()) ||
    Boolean(config.venueDetails.directions?.trim());

  return {
    organizationProfile: Boolean(organizationName?.trim()) || config.useOrganizationContacts,
    competitionContacts: config.teamContacts.length > 0,
    venue: Boolean(venueName) || hasVenueExtras,
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
