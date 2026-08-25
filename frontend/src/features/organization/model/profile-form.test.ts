import { describe, expect, it } from "vitest";
import type { OrganizationProfile } from "../api/profile";
import { formValuesToUpdate, organizationProfileSchema, profileToFormValues } from "./profile-form";

const baseProfile: OrganizationProfile = {
  id: "org-1",
  name: "Взлёт талантов",
  slug: "vzlyot-talantov",
  phone: "+375 29",
  email: "hello@vzlet.ru",
  website: "https://vzlet.ru",
  address: "Москва",
  logo: null,
  vk: null,
  instagram: null,
  telegram: null,
  legalInformation: "ООО «Взлёт»",
  supporter: null,
};

describe("profileToFormValues", () => {
  it("maps nulls to empty strings", () => {
    const values = profileToFormValues({ ...baseProfile, vk: null, phone: null });
    expect(values.vk).toBe("");
    expect(values.phone).toBe("");
    expect(values.email).toBe("hello@vzlet.ru");
  });
});

describe("formValuesToUpdate", () => {
  it("trims values and turns blanks into null", () => {
    const update = formValuesToUpdate({
      name: "  Взлёт  ",
      phone: "  +375 29  ",
      email: "",
      website: "   ",
      address: "Москва",
      vk: "",
      instagram: "",
      telegram: "",
      legalInformation: "",
      ...emptySupporter(),
    });
    expect(update.name).toBe("Взлёт");
    expect(update.phone).toBe("+375 29");
    expect(update.email).toBeNull();
    expect(update.website).toBeNull();
    expect(update.address).toBe("Москва");
  });
});

describe("organizationProfileSchema", () => {
  it("accepts empty optional fields when the name is set", () => {
    const result = organizationProfileSchema.safeParse(emptyForm());
    expect(result.success).toBe(true);
  });

  it("rejects a blank name", () => {
    const result = organizationProfileSchema.safeParse({ ...emptyForm(), name: "   " });
    expect(result.success).toBe(false);
  });

  it("rejects an invalid email", () => {
    const result = organizationProfileSchema.safeParse({ ...emptyForm(), email: "not-an-email" });
    expect(result.success).toBe(false);
  });

  it("rejects a non-http website", () => {
    const result = organizationProfileSchema.safeParse({ ...emptyForm(), website: "vzlet.ru" });
    expect(result.success).toBe(false);
  });

  it("rejects an overlong phone", () => {
    const result = organizationProfileSchema.safeParse({ ...emptyForm(), phone: "x".repeat(201) });
    expect(result.success).toBe(false);
  });

  it("accepts a form with no supporting entity at all", () => {
    // The ordinary organization runs its own festivals; the whole block stays blank.
    const result = organizationProfileSchema.safeParse(emptyForm());
    expect(result.success).toBe(true);
  });

  it("refuses supporting-entity details with no name to hang them on", () => {
    // The name is what makes the block exist, so the backend would drop the address
    // along with it. Losing what someone just typed without saying so is the bug.
    const result = organizationProfileSchema.safeParse({
      ...emptyForm(),
      supporterAddress: "г. Минск, ул. Ленина, 5",
    });
    expect(result.success).toBe(false);
    const issue = result.error?.issues.find((item) => item.path[0] === "supporterName");
    expect(issue?.message).toContain("не сохранятся");
  });

  it("validates the supporting entity's email like the organization's own", () => {
    const result = organizationProfileSchema.safeParse({
      ...emptyForm(),
      supporterName: "ГУ «Дворец культуры»",
      supporterEmail: "not-an-email",
    });
    expect(result.success).toBe(false);
  });
});

describe("the supporting entity round trip", () => {
  it("nests the flat form fields into the block the API takes", () => {
    const update = formValuesToUpdate({
      ...emptyForm(),
      supporterName: "  ГУ «Дворец культуры»  ",
      supporterPhone: "+375 17 222-22-22",
      supporterLegalInformation: "ГУ «Дворец культуры», УНП 100987654",
    });
    expect(update.supporter.name).toBe("ГУ «Дворец культуры»");
    expect(update.supporter.phone).toBe("+375 17 222-22-22");
    expect(update.supporter.legalInformation).toBe("ГУ «Дворец культуры», УНП 100987654");
    // The organization's own legal information stays its own — the two blocks are
    // different legal persons and must not bleed into each other.
    expect(update.legalInformation).toBeNull();
  });

  it("sends a blank name rather than omitting the block, so clearing it works", () => {
    const update = formValuesToUpdate(emptyForm());
    expect(update.supporter.name).toBe("");
  });

  it("seeds the form from a stored block and back without drift", () => {
    const values = profileToFormValues({
      ...baseProfile,
      supporter: {
        name: "ГУ «Дворец культуры»",
        phone: "+375 17",
        email: null,
        website: null,
        address: null,
        vk: null,
        instagram: null,
        telegram: null,
        legalInformation: "УНП 100987654",
      },
    });
    expect(values.supporterName).toBe("ГУ «Дворец культуры»");
    expect(values.supporterEmail).toBe("");
    expect(formValuesToUpdate(values).supporter).toEqual({
      name: "ГУ «Дворец культуры»",
      phone: "+375 17",
      email: null,
      website: null,
      address: null,
      vk: null,
      instagram: null,
      telegram: null,
      legalInformation: "УНП 100987654",
    });
  });
});

function emptyForm() {
  return {
    name: "Взлёт талантов",
    phone: "",
    email: "",
    website: "",
    address: "",
    vk: "",
    instagram: "",
    telegram: "",
    legalInformation: "",
    ...emptySupporter(),
  };
}

function emptySupporter() {
  return {
    supporterName: "",
    supporterPhone: "",
    supporterEmail: "",
    supporterWebsite: "",
    supporterAddress: "",
    supporterVk: "",
    supporterInstagram: "",
    supporterTelegram: "",
    supporterLegalInformation: "",
  };
}
