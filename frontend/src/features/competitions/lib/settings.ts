import type {
  _FormatRequirements,
  _FormatRequirementsInput,
  _ParticipationFormat,
  _Settings,
  PaymentMethodsEnum,
  PaymentTimingEnum,
  UpdateCompetitionSettings,
} from "@/shared/api/generated/model-competitions";

export type SettingsPaymentTiming = PaymentTimingEnum;
export type SettingsPaymentMethod = PaymentMethodsEnum;

export const PAYMENT_TIMING_OPTIONS: { value: SettingsPaymentTiming; label: string }[] = [
  { value: "BEFORE_REVIEW", label: "До рассмотрения заявки" },
  { value: "BEFORE_APPROVAL", label: "До подтверждения заявки" },
  { value: "BEFORE_COMPETITION", label: "До начала фестиваля" },
];

export const PAYMENT_METHOD_OPTIONS: { value: SettingsPaymentMethod; label: string }[] = [
  { value: "ONLINE", label: "Онлайн-оплата" },
  { value: "BANK_TRANSFER", label: "Банковский перевод" },
  { value: "CASH", label: "Наличные" },
];

export type VideoMode = "NOT_REQUIRED" | "URL_ONLY" | "FILE_ONLY" | "URL_OR_FILE";
export type VideoProvider = "YOUTUBE" | "VK_VIDEO" | "RUTUBE" | "VIMEO";

/**
 * Video modes the platform can actually hold an applicant to.
 *
 * ``URL_ONLY`` and ``URL_OR_FILE`` are deliberately absent: a submission has no
 * field for a video *link*, only uploaded files, so either would behave exactly
 * like "не требуется". They remain in {@link VideoMode} and in the stored settings
 * — a competition configured with one keeps its value — but are not offered until
 * a video link is something an applicant can actually supply.
 */
export const VIDEO_MODE_OPTIONS: { value: VideoMode; label: string }[] = [
  { value: "NOT_REQUIRED", label: "Не требуется" },
  { value: "FILE_ONLY", label: "Требовать файл" },
];

export const VIDEO_FORMAT_OPTIONS: { value: string; label: string }[] = [
  { value: "mp4", label: "MP4" },
  { value: "mov", label: "MOV" },
  { value: "m4v", label: "M4V" },
  { value: "webm", label: "WebM" },
  { value: "mkv", label: "MKV" },
  { value: "avi", label: "AVI" },
];

export const VIDEO_PROVIDER_OPTIONS: { value: VideoProvider; label: string }[] = [
  { value: "YOUTUBE", label: "YouTube" },
  { value: "VK_VIDEO", label: "VK Видео" },
  { value: "RUTUBE", label: "RuTube" },
  { value: "VIMEO", label: "Vimeo" },
];

export const AUDIO_FORMAT_OPTIONS: { value: string; label: string }[] = [
  { value: "mp3", label: "MP3" },
  { value: "wav", label: "WAV" },
  { value: "m4a", label: "M4A" },
  { value: "aac", label: "AAC" },
  { value: "flac", label: "FLAC" },
  { value: "ogg", label: "OGG" },
];

export function defaultFormatRequirements(participationFormatId: string): _FormatRequirements {
  return {
    participationFormatId,
    music: {
      requireUpload: false,
      allowReplacement: true,
      allowedFormats: ["mp3", "wav", "m4a", "aac"],
      maxUploadSizeMb: 25,
    },
    video: {
      mode: "NOT_REQUIRED",
      allowedProviders: ["YOUTUBE", "VK_VIDEO", "RUTUBE", "VIMEO"],
      allowReplacement: true,
      requireUpload: false,
      allowedFormats: ["mp4", "mov", "m4v", "webm"],
      // Generous next to music's 25 MB: a minute of phone video is tens of megabytes,
      // and a limit that refuses an ordinary entry is a limit nobody can meet.
      maxUploadSizeMb: 200,
    },
    paymentReceipt: {
      requireReceipt: false,
      allowUploadLater: true,
      allowReplacement: true,
    },
  };
}

export function defaultCompetitionSettings(): _Settings {
  return {
    allowMultipleApplications: false,
    allowApplicationEditing: true,
    allowWithdrawingApplications: true,
    requireTeacher: true,
    requireParentGuardian: false,
    participantCommentEnabled: true,
    requireDocumentUpload: false,
    allowAdditionalDocumentsLater: true,
    allowReplacingDocuments: true,
    paymentRequired: false,
    paymentTiming: "BEFORE_APPROVAL",
    paymentMethods: [],
    additionalPerformanceDiscountPercent: 0,
    requirePersonalDataConsent: true,
    requireMediaConsent: false,
    requireRegulationsAcceptance: true,
    manualApplicationApproval: true,
    automaticApprovalAfterPayment: false,
    allowReturningForCorrection: true,
    formatRequirements: [],
  };
}

/**
 * Settings the platform stores but does not act on, and so does not show.
 *
 * An audit found most of this section was decoration: the switch saved and the
 * platform carried on regardless. The behaviour each one describes is currently
 * fixed for every festival — applications stay editable, approval stays manual,
 * payment is always on — and that base is what organizers actually want, so the
 * controls are simply absent rather than shown as pending. The fields stay in the
 * API and the stored bag: when enforcement lands, the setting is rendered again
 * and drops out of this list. Nothing here is read by the UI.
 */
export const UNENFORCED_SETTINGS = new Set<keyof _Settings>([
  "allowMultipleApplications",
  "allowApplicationEditing",
  "allowWithdrawingApplications",
  "allowAdditionalDocumentsLater",
  "allowReplacingDocuments",
  "paymentRequired",
  "paymentTiming",
  "paymentMethods",
  "manualApplicationApproval",
  "automaticApprovalAfterPayment",
  "allowReturningForCorrection",
]);

export function isSettingEnforced(key: keyof _Settings): boolean {
  return !UNENFORCED_SETTINGS.has(key);
}

/**
 * Ensures every active participation format has a requirements card.
 * Formats in settings but not in participationFormats are dropped.
 */
export function mergeSettingsWithFormats(
  settings: _Settings,
  participationFormats: _ParticipationFormat[],
): _Settings {
  const byId = new Map(settings.formatRequirements.map((r) => [r.participationFormatId, r]));
  const formatRequirements: _FormatRequirements[] = participationFormats.map(
    (fmt) => byId.get(fmt.id) ?? defaultFormatRequirements(fmt.id),
  );
  return { ...settings, formatRequirements };
}

export function settingsToUpdatePayload(settings: _Settings): UpdateCompetitionSettings {
  return {
    allowMultipleApplications: settings.allowMultipleApplications,
    allowApplicationEditing: settings.allowApplicationEditing,
    allowWithdrawingApplications: settings.allowWithdrawingApplications,
    requireTeacher: settings.requireTeacher,
    requireParentGuardian: settings.requireParentGuardian,
    participantCommentEnabled: settings.participantCommentEnabled,
    requireDocumentUpload: settings.requireDocumentUpload,
    allowAdditionalDocumentsLater: settings.allowAdditionalDocumentsLater,
    allowReplacingDocuments: settings.allowReplacingDocuments,
    paymentRequired: settings.paymentRequired,
    // `_Settings` (response) types these loosely (string / string[]); the request
    // payload uses the enum unions. Same wire values — narrow at the boundary.
    paymentTiming: settings.paymentTiming as PaymentTimingEnum,
    paymentMethods: settings.paymentMethods as PaymentMethodsEnum[],
    additionalPerformanceDiscountPercent: Math.max(
      0,
      Math.min(100, Math.round(settings.additionalPerformanceDiscountPercent ?? 0)),
    ),
    requirePersonalDataConsent: settings.requirePersonalDataConsent,
    requireMediaConsent: settings.requireMediaConsent,
    requireRegulationsAcceptance: settings.requireRegulationsAcceptance,
    manualApplicationApproval: settings.manualApplicationApproval,
    automaticApprovalAfterPayment: settings.automaticApprovalAfterPayment,
    allowReturningForCorrection: settings.allowReturningForCorrection,
    formatRequirements: settings.formatRequirements as _FormatRequirementsInput[],
  };
}
