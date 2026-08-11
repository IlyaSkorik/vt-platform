export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  forgotPassword: "/forgot-password",
  resetPassword: "/reset-password",
  verifyEmail: "/verify-email",
  emailVerified: "/email-verified",
  sessionExpired: "/session-expired",
  unauthorized: "/unauthorized",
  cabinet: "/cabinet",
  cabinetProfile: "/cabinet",
  cabinetParticipants: "/cabinet/participants",
  cabinetParticipantNew: "/cabinet/participants/new",
  cabinetParticipantProfile: "/cabinet/participants/:participantId",
  cabinetTeachers: "/cabinet/teachers",
  cabinetTeacherNew: "/cabinet/teachers/new",
  cabinetTeacherProfile: "/cabinet/teachers/:teacherId",
  cabinetApplications: "/cabinet/applications",
  cabinetApplication: "/cabinet/applications/:applicationId",
  /**
   * Amending an application the organizer has already received — a screen of its
   * own, not a second pass through the submission wizard.
   */
  cabinetApplicationEdit: "/cabinet/applications/:applicationId/edit",
  cabinetCompetitions: "/cabinet/competitions",
  cabinetFestival: "/cabinet/competitions/:festivalId",
  cabinetFestivalApply: "/cabinet/competitions/:festivalId/apply",
  cabinetDocuments: "/cabinet/documents",
  cabinetNotifications: "/cabinet/notifications",
  cabinetSettings: "/cabinet/settings",
  dashboard: "/dashboard",
  participants: "/participants",
  competitions: "/competitions",
  /** Public diploma authenticity page — the target printed inside a diploma's QR. */
  verifyDiploma: "/verify/:verificationToken",
  /** Public programme screen — one unguessable slug per published edition. */
  publicProgram: "/program/:slug",
  /**
   * Public results page — one slug per published protocol.
   *
   * Unlike a programme link this one is meant to be found: the competition's landing page
   * links it under "Результаты", and so does the letter sent to every participant.
   */
  publicProtocol: "/protocol/:slug",
  /** The contract accepted at registration — the basis the account's data rests on. */
  termsOfService: "/terms",
  privacyPolicy: "/privacy-policy",
  cookiesPolicy: "/cookies",
  applications: "/applications",
  performances: "/performances",
  judging: "/judging",
  results: "/results",
  finance: "/finance",
  analytics: "/analytics",
  settings: "/settings",
  staff: "/staff",
  staffCompetitions: "/staff/competitions",
  staffCompetitionsNew: "/staff/competitions/new",
  staffCompetitionDetail: "/staff/competitions/:competitionId",
  staffApplications: "/staff/applications",
  staffParticipants: "/staff/participants",
  staffJudges: "/staff/judges",
  staffProgram: "/staff/program",
  staffDiplomas: "/staff/diplomas",
  staffDiplomaTemplateConstructor: "/staff/diplomas/templates/:templateId/constructor",
  staffFinance: "/staff/finance",
  staffAnalytics: "/staff/analytics",
  staffOrganization: "/staff/organization",
  staffUsers: "/staff/users",
  staffInvitations: "/staff/invitations",
  staffSettings: "/staff/settings",
  staffInvitation: "/staff/invitations/:token",
  /** The platform operator's own console — above every connected organization. */
  platform: "/platform",
  platformOrganizations: "/platform/organizations",
  /** The operator's test bench — load-testing generation against the live stack. */
  platformTesting: "/platform/testing",
  profile: "/profile",
} as const;

export type RouteKey = keyof typeof ROUTES;
export type RoutePath = (typeof ROUTES)[RouteKey];
