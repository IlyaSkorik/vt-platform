import { describe, expect, it } from "vitest";
import {
  buildContactsSummary,
  createTeamContactDraft,
  defaultContactsConfig,
  moveTeamContactBefore,
  sortTeamContacts,
} from "./contacts";

describe("contacts helpers", () => {
  it("defaults to organization contacts inheritance", () => {
    expect(defaultContactsConfig().useOrganizationContacts).toBe(true);
    expect(defaultContactsConfig().teamContacts).toEqual([]);
  });

  it("reorders team contacts by drag target", () => {
    const a = {
      ...createTeamContactDraft(0),
      id: "11111111-1111-7111-8111-111111111111",
      name: "A",
    };
    const b = {
      ...createTeamContactDraft(1),
      id: "22222222-2222-7222-8222-222222222222",
      name: "B",
    };
    const c = {
      ...createTeamContactDraft(2),
      id: "33333333-3333-7333-8333-333333333333",
      name: "C",
    };
    const next = moveTeamContactBefore([a, b, c], a.id, c.id);
    expect(sortTeamContacts(next).map((item) => item.name)).toEqual(["B", "A", "C"]);
  });

  it("builds summary flags from competition and config", () => {
    const config = defaultContactsConfig();
    config.teamContacts = [
      { ...createTeamContactDraft(0), id: "11111111-1111-7111-8111-111111111111", name: "Anna" },
    ];
    config.emergency.phone = "112";
    const summary = buildContactsSummary(config, "Взлёт талантов");
    expect(summary).toEqual({
      organizationProfile: true,
      competitionContacts: true,
      emergency: true,
    });
  });
});
