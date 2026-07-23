export {
  diplomaKeys,
  useCreateAssignmentMutation,
  useCreateTemplateMutation,
  useDeleteAssignmentMutation,
  useDiplomaAssignments,
  useDiplomaTemplates,
} from "./api";
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
