export {
  type DiplomaTemplateQuery,
  diplomaKeys,
  useCreateAssignmentMutation,
  useCreateTemplateMutation,
  useDeleteAssignmentMutation,
  useDiplomaAssignments,
  useDiplomaTemplate,
  useDiplomaTemplates,
} from "./api";
export {
  FIELD_TYPES,
  type TemplateDocument,
  type TemplateField,
  type TemplateFieldStyle,
  type TemplateFieldType,
  type TemplateFieldTypeId,
  type TemplateTextAlign,
  type TemplateVersion,
} from "./model/constructor";
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
} from "./model/types";
