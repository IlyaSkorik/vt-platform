export {
  type DiplomaTemplateQuery,
  diplomaKeys,
  useCreateAssignmentMutation,
  useCreateTemplateMutation,
  useDeleteAssignmentMutation,
  useDiplomaAssignments,
  useDiplomaTemplate,
  useDiplomaTemplates,
  useSaveTemplateLayoutMutation,
  useTemplateLayout,
  useUploadTemplateDocumentMutation,
} from "./api";
export { resolveMediaUrl } from "./lib/media-url";
export {
  defaultBindingForType,
  KNOWN_BINDINGS,
  PARTICIPANT_DISPLAY_NAME,
  type TemplateFieldBinding,
} from "./model/binding";
export {
  DEFAULT_FIELD_STYLE,
  DEFAULT_FREE_TEXT,
  FIELD_TYPES,
  type TemplateDocument,
  type TemplateField,
  type TemplateFieldStyle,
  type TemplateFieldType,
  type TemplateFieldTypeId,
  type TemplateFontStyle,
  type TemplateFontWeight,
  type TemplatePage,
  type TemplateTextAlign,
  type TemplateVersion,
} from "./model/constructor";
export { type PreviewMode, resolvePreviewValue } from "./model/preview-data";
export {
  DEFAULT_DIPLOMA_SECTION,
  DIPLOMA_SECTIONS,
  type DiplomaSection,
  type DiplomaSectionId,
  findDiplomaSection,
} from "./model/sections";
export type {
  CreateAssignmentPayload,
  CreateTemplatePayload,
  DiplomaAssignment,
  DiplomaTemplate,
  TemplateLayout,
} from "./model/types";
