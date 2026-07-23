/** TanStack Query keys for diploma resources. */
export const diplomaKeys = {
  all: ["diplomas"] as const,
  templates: () => [...diplomaKeys.all, "templates"] as const,
  assignments: () => [...diplomaKeys.all, "assignments"] as const,
  layout: (templateId: string) => [...diplomaKeys.all, "layout", templateId] as const,
  previewApplications: (competitionId: string) =>
    [...diplomaKeys.all, "preview", "applications", competitionId] as const,
  previewBindings: (applicationId: string) =>
    [...diplomaKeys.all, "preview", "bindings", applicationId] as const,
};
