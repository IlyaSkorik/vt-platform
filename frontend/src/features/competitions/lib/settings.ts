import type {
  _FormatRequirements,
  _ParticipationFormat,
  _Settings,
  _SettingsPaymentMethodsItem,
  _SettingsPaymentTiming,
  UpdateCompetitionSettings,
} from "@/shared/api/generated/model-competitions";

export type SettingsPaymentTiming = _SettingsPaymentTiming;
export type SettingsPaymentMethod = _SettingsPaymentMethodsItem;

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

export const VIDEO_MODE_OPTIONS: { value: VideoMode; label: string }[] = [
  { value: "NOT_REQUIRED", label: "Не требуется" },
  { value: "URL_ONLY", label: "Только ссылка" },
  { value: "FILE_ONLY", label: "Только файл" },
  { value: "URL_OR_FILE", label: "Ссылка или файл" },
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
    allowCopyingPreviousApplications: false,
    requireTeacher: false,
    requireParentGuardian: false,
    participantCommentEnabled: false,
    requireDocumentUpload: false,
    allowAdditionalDocumentsLater: true,
    allowReplacingDocuments: true,
    paymentRequired: false,
    paymentTiming: "BEFORE_APPROVAL",
    paymentMethods: [],
    requirePersonalDataConsent: true,
    requireMediaConsent: false,
    requireRegulationsAcceptance: true,
    emailNotifications: true,
    cabinetNotifications: true,
    smsNotifications: false,
    pushNotifications: false,
    manualApplicationApproval: true,
    automaticApprovalAfterPayment: false,
    allowReturningForCorrection: true,
    formatRequirements: [],
  };
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
    allowCopyingPreviousApplications: settings.allowCopyingPreviousApplications,
    requireTeacher: settings.requireTeacher,
    requireParentGuardian: settings.requireParentGuardian,
    participantCommentEnabled: settings.participantCommentEnabled,
    requireDocumentUpload: settings.requireDocumentUpload,
    allowAdditionalDocumentsLater: settings.allowAdditionalDocumentsLater,
    allowReplacingDocuments: settings.allowReplacingDocuments,
    paymentRequired: settings.paymentRequired,
    paymentTiming: settings.paymentTiming,
    paymentMethods: settings.paymentMethods,
    requirePersonalDataConsent: settings.requirePersonalDataConsent,
    requireMediaConsent: settings.requireMediaConsent,
    requireRegulationsAcceptance: settings.requireRegulationsAcceptance,
    emailNotifications: settings.emailNotifications,
    cabinetNotifications: settings.cabinetNotifications,
    smsNotifications: settings.smsNotifications,
    pushNotifications: settings.pushNotifications,
    manualApplicationApproval: settings.manualApplicationApproval,
    automaticApprovalAfterPayment: settings.automaticApprovalAfterPayment,
    allowReturningForCorrection: settings.allowReturningForCorrection,
    formatRequirements: settings.formatRequirements,
  };
}
