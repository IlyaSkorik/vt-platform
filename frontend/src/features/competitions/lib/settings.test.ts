import { describe, expect, it } from "vitest";
import type { _ParticipationFormat, _Settings } from "@/shared/api/generated/model-competitions";
import {
  defaultCompetitionSettings,
  defaultFormatRequirements,
  mergeSettingsWithFormats,
  settingsToUpdatePayload,
} from "./settings";

function makeFormat(id: string): _ParticipationFormat {
  return {
    id,
    name: id,
    description: null,
    enabled: true,
    sortOrder: 0,
  };
}

describe("defaultCompetitionSettings", () => {
  it("returns a valid settings object", () => {
    const s = defaultCompetitionSettings();
    expect(s.allowMultipleApplications).toBe(false);
    expect(s.requirePersonalDataConsent).toBe(true);
    expect(s.paymentTiming).toBe("BEFORE_APPROVAL");
    expect(s.formatRequirements).toEqual([]);
  });
});

describe("mergeSettingsWithFormats", () => {
  it("fills in defaults for formats not in settings", () => {
    const settings = defaultCompetitionSettings();
    const formats = [makeFormat("fmt-1"), makeFormat("fmt-2")];
    const merged = mergeSettingsWithFormats(settings, formats);
    expect(merged.formatRequirements).toHaveLength(2);
    expect(merged.formatRequirements[0]?.participationFormatId).toBe("fmt-1");
    expect(merged.formatRequirements[1]?.participationFormatId).toBe("fmt-2");
  });

  it("preserves existing format requirements", () => {
    const existing = defaultFormatRequirements("fmt-1");
    existing.music.requireUpload = true;
    const settings: _Settings = {
      ...defaultCompetitionSettings(),
      formatRequirements: [existing],
    };
    const formats = [makeFormat("fmt-1"), makeFormat("fmt-2")];
    const merged = mergeSettingsWithFormats(settings, formats);
    expect(merged.formatRequirements[0]?.music.requireUpload).toBe(true);
    expect(merged.formatRequirements[1]?.music.requireUpload).toBe(false);
  });

  it("drops format requirements for removed formats", () => {
    const settings: _Settings = {
      ...defaultCompetitionSettings(),
      formatRequirements: [
        defaultFormatRequirements("fmt-old"),
        defaultFormatRequirements("fmt-1"),
      ],
    };
    const formats = [makeFormat("fmt-1")];
    const merged = mergeSettingsWithFormats(settings, formats);
    expect(merged.formatRequirements).toHaveLength(1);
    expect(merged.formatRequirements[0]?.participationFormatId).toBe("fmt-1");
  });
});

describe("settingsToUpdatePayload", () => {
  it("produces an update payload matching the settings shape", () => {
    const settings = defaultCompetitionSettings();
    const payload = settingsToUpdatePayload(settings);
    expect(payload.allowMultipleApplications).toBe(settings.allowMultipleApplications);
    expect(payload.paymentTiming).toBe(settings.paymentTiming);
    expect(payload.formatRequirements).toEqual(settings.formatRequirements);
  });
});
