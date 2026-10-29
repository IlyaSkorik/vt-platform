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
  /**
   * What the platform does for an organizer, with screens from a demo festival.
   * The link an organizer is sent after the first call, so it is public, indexed,
   * and lives here rather than on somebody else's hosting.
   */
  organizers: "/organizers",
  /** Public diploma authenticity page — the target printed inside a diploma's QR. */
  verifyDiploma: "/verify/:verificationToken",
  /** Public programme screen — one unguessable slug per published edition. */
  publicProgram: "/program/:slug",
  // The audience vote: the page people reach from a QR on a poster, and the
  // board beside the stage that shows the count.
  publicBallot: "/vote/:slug",
  publicBallotBoard: "/vote/:slug/board",
  /**
   * The review form, reached from a code on a banner. One slug per organizer and
   * permanent — the banner is printed on cloth and stands at next season's events.
   */
  publicReview: "/reviews/:slug",
  /**
   * Public results page — one slug per published protocol.
   *
   * Unlike a programme link this one is meant to be found: the competition's landing page
   * links it under "Результаты", and so does the letter sent to every participant.
   */
  publicProtocol: "/protocol/:slug",
  /**
   * The hall's judging board — one unguessable slug per festival, minted when the
   * organizer switches the board on. Like the vote board it is a screen nobody taps,
   * read from the back of a room; unlike it, what it may show is configurable, and the
   * filtering happens on the server.
   */
  publicJudgingBoard: "/board/:slug",
  /**
   * A judge's own screen: the acts they are seated for, and the sheet for each.
   *
   * Under `/jury` rather than `/staff` on purpose — a jury member is a guest of the
   * organization, not an employee of it, and the staff area would hand them the
   * applications, the money and the participants along with the marks.
   */
  jury: "/jury",
  juryScoring: "/jury/:competitionId",
  /** The one-time link an invitation e-mail carries. */
  juryInvitation: "/jury/invite/:token",
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
  staffVoting: "/staff/voting",
  staffReviews: "/staff/reviews",
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
  /** The platform's own books: what it spent, and the difference against income. */
  platformFinance: "/platform/finance",
  /** The other side of those books: commission organizations actually paid. */
  platformCommission: "/platform/commission",
  /** Every review left on the platform — where a complaint about one is settled. */
  platformReviews: "/platform/reviews",
  /** The eraser: removing a festival, an order or an account for good. */
  platformErase: "/platform/erase",
  profile: "/profile",
} as const;

export type RouteKey = keyof typeof ROUTES;
export type RoutePath = (typeof ROUTES)[RouteKey];
