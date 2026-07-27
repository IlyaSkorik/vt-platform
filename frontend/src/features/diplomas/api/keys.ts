/** TanStack Query keys for diploma resources. */
export const diplomaKeys = {
  all: ["diplomas"] as const,
  templates: () => [...diplomaKeys.all, "templates"] as const,
  assignments: () => [...diplomaKeys.all, "assignments"] as const,
  layout: (templateId: string) => [...diplomaKeys.all, "layout", templateId] as const,
  previewApplications: (competitionId: string) =>
    [...diplomaKeys.all, "preview", "applications", competitionId] as const,
  // The kind is part of the key: the same application resolves differently for a
  // diploma and for a thank-you letter.
  previewBindings: (applicationId: string, documentType = "DIPLOMA") =>
    [...diplomaKeys.all, "preview", "bindings", applicationId, documentType] as const,
  registry: (competitionId: string) => [...diplomaKeys.all, "registry", competitionId] as const,
  printSummary: (competitionId: string) =>
    [...diplomaKeys.all, "print-summary", competitionId] as const,
  printJob: (jobId: string) => [...diplomaKeys.all, "print-job", jobId] as const,
  // Every scope of the history, for invalidating them all after a run.
  generationArchives: () => [...diplomaKeys.all, "generation-archive"] as const,
  // The whole history by default; a competition id narrows it to one competition.
  generationArchive: (competitionId = "") =>
    [...diplomaKeys.generationArchives(), competitionId] as const,
};
