import { describe, expect, it } from "vitest";
import type { OrganizationProfile } from "../api/profile";
import { formValuesToUpdate, organizationProfileSchema, profileToFormValues } from "./profile-form";

const baseProfile: OrganizationProfile = {
  id: "org-1",
  name: "Взлёт талантов",
  slug: "vzlyot-talantov",
  phone: "+7 900",
  email: "hello@vzlet.ru",
  website: "https://vzlet.ru",
  address: "Москва",
  logo: null,
  vk: null,
  instagram: null,
  telegram: null,
  legalInformation: "ООО «Взлёт»",
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
      phone: "  +7 900  ",
      email: "",
      website: "   ",
      address: "Москва",
      vk: "",
      instagram: "",
      telegram: "",
      legalInformation: "",
    });
    expect(update.name).toBe("Взлёт");
    expect(update.phone).toBe("+7 900");
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
  };
}
