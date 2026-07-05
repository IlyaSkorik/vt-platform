# DATA-003 — Domain Event Catalog v1.0

**Project:** «Взлёт талантов» — цифровая экосистема для организации детских творческих конкурсов
**Document type:** Domain Event Catalog (business language only)
**Status:** Draft for review (v1.0)
**Owner:** Enterprise Architecture Group
**Source of truth:** [ARCH-001](../architecture/ARCH-001-vt-platform-architecture.md) · [DATA-001 Business Data Model](DATA-001-business-data-model.md) · [DATA-002 Business Rules Catalog](DATA-002-business-rules-catalog.md)
**Last updated:** 2026-07-05

> This document catalogues **every significant business event** on the VT Platform, in **business language only**. It contains **no** SQL, no message-broker technology (no Kafka, no RabbitMQ), no implementation, and no code. Events are the integration currency between bounded contexts (ARCH-001 §4.8, §7.4). Each event references the business objects of [DATA-001](DATA-001-business-data-model.md) and the rules of [DATA-002](DATA-002-business-rules-catalog.md). Event **names** follow the naming standard in [DATA-001 §10.4](DATA-001-business-data-model.md#104-events): past-tense facts, PascalCase. This catalogue must not contradict its sources.

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [How to Read an Event](#2-how-to-read-an-event)
3. [Event Classification Model](#3-event-classification-model)
4. [Events by Domain](#4-events-by-domain)
   - [Identity (IDN)](#41-identity-idn) · [Participants (PRT)](#42-participants-prt) · [Institutions (INS)](#43-institutions-ins) · [Competitions (CMP)](#44-competitions-cmp) · [Applications (APP)](#45-applications-app) · [Performances (PRF)](#46-performances-prf) · [Judging (JDG)](#47-judging-jdg) · [Results (RES)](#48-results-res) · [Finance (FIN)](#49-finance-fin) · [Notifications (NTF)](#410-notifications-ntf) · [Analytics (ANL)](#411-analytics-anl) · [Audit (AUD)](#412-audit-aud)
5. [Event Dependency Graph](#5-event-dependency-graph)
6. [Cross-Domain Event Flow](#6-cross-domain-event-flow)
7. [End-to-End Competition Event Timeline](#7-end-to-end-competition-event-timeline)
8. [Event Ownership Matrix](#8-event-ownership-matrix)
9. [Event Versioning Policy](#9-event-versioning-policy)
10. [Summary Statistics](#10-summary-statistics)

---

## 1. Purpose & Scope

### 1.1 Purpose

To define the **published language** of the platform: the immutable facts that each domain emits when something business-significant happens, and which other domains react to. This catalogue lets teams reason about cause and effect across bounded contexts without coupling to each other's internals, and it operationalizes the event-driven principle (ARCH-001 §4.8) and the transactional-outbox integration model (ARCH-001 §7.4) in **business terms**.

### 1.2 Scope

- **In scope:** every significant business event across the twelve domains; each event's meaning, trigger, objects, producer/consumers, preconditions, referenced rules, business-level payload, side effects, priority, and classification; plus the dependency graph, cross-domain flow, end-to-end timeline, ownership matrix, and versioning policy.
- **Out of scope:** transport, brokers, serialization, delivery guarantees, retries — all technical concerns (ARCH-001 §7.4, §7.5). This document says *what* is published and *why*; not *how* it is carried.

### 1.3 Event Identifier Scheme

```
EVT-<DOMAIN>-<NNN>
```

Domain codes match [DATA-002 §1.3](DATA-002-business-rules-catalog.md#13-rule-identifier-scheme): `IDN PRT INS CMP APP PRF JDG RES FIN NTF ANL AUD`. Numbers are zero-padded, sequential, and **immutable** once assigned. Event **names** are past-tense PascalCase facts (e.g., `ApplicationSubmitted`).

### 1.4 Core Principles (from the sources)

- Events are **immutable facts** stated in the past tense; they are never commands (DATA-001 §10.4).
- Each event carries the **identity** of its affected aggregate root and the **business time** it occurred (DATA-001 §9, §10.4).
- Events cross domains **by identity**, never by exposing another domain's internals (ARCH-001 §9.2).
- **Audit is a universal consumer**: any fairness-, money-, access-, or privacy-significant event is recorded immutably ([RULE-AUD-001](DATA-002-business-rules-catalog.md#rule-aud-001)).

---

## 2. How to Read an Event

Every event is specified with the following fields:

- **Event ID** — stable identifier (§1.3).
- **Event Name** — past-tense PascalCase fact.
- **Classification** — one or more of the four event classes (§3).
- **Priority** — Critical / High / Medium / Low dispatch-and-reaction priority (§3.2).
- **Description** — what the event states, in business language.
- **Business Meaning** — why stakeholders care.
- **Trigger** — the action/decision that produces the event.
- **Business Objects** — DATA-001 objects the event concerns.
- **Producer** — the owning domain/aggregate that emits it.
- **Consumers** — domains that react to it.
- **Preconditions** — what must be true for the event to be emitted.
- **Business Rules References** — DATA-002 rules governing the event.
- **Payload (business attributes only)** — the business facts carried (identities + meaningful fields); no technical fields.
- **Side Effects** — the business consequences the event sets in motion.

---

## 3. Event Classification Model

### 3.1 Event Classes

An event may carry more than one class.

| Class | Definition | Typical audience |
|-------|------------|------------------|
| **Domain Event** | A fact meaningful **within** its originating bounded context; the primary record of a state change | The owning domain |
| **Integration Event** | A fact **published across** context boundaries for other domains to react to | Other domains |
| **Business Event** | A fact meaningful to **business stakeholders** (product, operations, organizers, finance) — surfaced in dashboards/reports | People & analytics |
| **Audit Event** | A fact that **must be recorded immutably** for fairness, privacy, security, or financial compliance | Audit domain, DPO |

> Most events are Domain Events. Those consumed by other contexts are also Integration Events. Fairness/money/privacy/access events are additionally Audit Events. Milestone events (e.g., competition published, results published) are also Business Events.

### 3.2 Priority

Priority expresses **how urgently** the event must be dispatched and reacted to (aligns with notification prioritization in [RULE-NTF-004](DATA-002-business-rules-catalog.md#rule-ntf-004) and severity in DATA-002 §3.1).

| Priority | Meaning |
|----------|---------|
| **Critical** | Safety, fairness, privacy, legal, or money integrity depends on prompt handling |
| **High** | Core workflow progression depends on it |
| **Medium** | Important but tolerant of short delay |
| **Low** | Informational / analytical |

---

## 4. Events by Domain

### 4.1 Identity (IDN)

---

#### EVT-IDN-001 · AccountRegistered
- **Classification:** Domain · Business
- **Priority:** Medium
- **Description:** A new adult User Account has been created.
- **Business Meaning:** A prospective guardian/teacher/jury/organizer has entered the platform (feeds registration funnel, BG-1).
- **Trigger:** Completion of account registration.
- **Business Objects:** User Account.
- **Producer:** Identity.
- **Consumers:** Notifications (send verification), Analytics (funnel), Audit.
- **Preconditions:** Unique, unused email; terms presented.
- **Business Rules References:** [IDN-003](DATA-002-business-rules-catalog.md#rule-idn-003), [IDN-010](DATA-002-business-rules-catalog.md#rule-idn-010).
- **Payload:** account identity, display name, email (contact), primary locale, registration time.
- **Side Effects:** Email verification requested; welcome/verification notification queued.

#### EVT-IDN-002 · EmailVerified
- **Classification:** Domain · Integration
- **Priority:** High
- **Description:** A User Account's email ownership has been proven.
- **Business Meaning:** The account may now perform sensitive actions.
- **Trigger:** Successful email verification.
- **Business Objects:** User Account, Email Verification.
- **Producer:** Identity.
- **Consumers:** Participants (guardian activation), Notifications, Audit.
- **Preconditions:** Valid, unexpired verification.
- **Business Rules References:** [IDN-001](DATA-002-business-rules-catalog.md#rule-idn-001).
- **Payload:** account identity, verified time.
- **Side Effects:** Sensitive-action gate lifted; dependent onboarding may proceed.

#### EVT-IDN-003 · ConsentGranted
- **Classification:** Domain · Integration · Audit · Business
- **Priority:** Critical
- **Description:** A guardian has granted consent for a minor's participation/data processing for a stated purpose.
- **Business Meaning:** Establishes the lawful basis without which no minor may participate.
- **Trigger:** Guardian completes a consent grant.
- **Business Objects:** Consent, Consent Type, Participant, Guardian.
- **Producer:** Identity.
- **Consumers:** Participants (activation), Applications (submission gate), Audit (consent record).
- **Preconditions:** Verified guardian; purpose and current consent-text version exist.
- **Business Rules References:** [IDN-005](DATA-002-business-rules-catalog.md#rule-idn-005), [PRT-001](DATA-002-business-rules-catalog.md#rule-prt-001), [APP-001](DATA-002-business-rules-catalog.md#rule-app-001).
- **Payload:** consent identity, subject participant identity, granting guardian identity, purpose, consent-text version, granted time, expiry.
- **Side Effects:** Participant may be activated; applications for the purpose become permissible; consent audit record written.

#### EVT-IDN-004 · ConsentWithdrawn
- **Classification:** Domain · Integration · Audit · Business
- **Priority:** Critical
- **Description:** A previously granted consent has been withdrawn.
- **Business Meaning:** Dependent processing must stop and enter the erasure/retention workflow.
- **Trigger:** Guardian withdraws consent.
- **Business Objects:** Consent, Participant, Retention Policy.
- **Producer:** Identity.
- **Consumers:** Participants, Applications, Performances, Audit.
- **Preconditions:** An active consent exists.
- **Business Rules References:** [IDN-006](DATA-002-business-rules-catalog.md#rule-idn-006), [PRT-007](DATA-002-business-rules-catalog.md#rule-prt-007), [AUD-005](DATA-002-business-rules-catalog.md#rule-aud-005).
- **Payload:** consent identity, subject participant identity, purpose, withdrawn time.
- **Side Effects:** Related processing halts; downstream data cascades to erasure/retention (subject to legal holds and financial retention).

#### EVT-IDN-005 · RoleAssigned
- **Classification:** Domain · Audit
- **Priority:** High
- **Description:** A role has been granted to a user within a scope.
- **Business Meaning:** Changes what the user may do (fairness/security relevant for privileged roles).
- **Trigger:** A role grant by an authorized granter.
- **Business Objects:** Role, Role Assignment, User Account.
- **Producer:** Identity.
- **Consumers:** all scoped domains (authorization), Audit.
- **Preconditions:** Granter authority sufficient; scope valid.
- **Business Rules References:** [IDN-008](DATA-002-business-rules-catalog.md#rule-idn-008), [IDN-002](DATA-002-business-rules-catalog.md#rule-idn-002).
- **Payload:** account identity, role, scope reference, granted-by, granted time, expiry.
- **Side Effects:** Access recomputed; MFA may be required before privileged use.

#### EVT-IDN-006 · MfaEnrolled
- **Classification:** Domain · Audit
- **Priority:** High
- **Description:** A user has enrolled a multi-factor method.
- **Business Meaning:** Privileged capabilities may now be exercised.
- **Trigger:** Successful MFA enrollment.
- **Business Objects:** User Account, Multi-Factor Enrollment.
- **Producer:** Identity.
- **Consumers:** Identity (privilege gate), Audit.
- **Preconditions:** Account holds a privileged role or opts in.
- **Business Rules References:** [IDN-002](DATA-002-business-rules-catalog.md#rule-idn-002).
- **Payload:** account identity, method descriptor, enrolled time.
- **Side Effects:** Privileged-role gate lifted.

#### EVT-IDN-007 · TermsAccepted
- **Classification:** Domain · Audit
- **Priority:** Medium
- **Description:** A user accepted the current platform terms version.
- **Business Meaning:** Contractual basis for platform use recorded.
- **Trigger:** User accepts terms.
- **Business Objects:** Terms Acceptance, User Account.
- **Producer:** Identity.
- **Consumers:** Audit.
- **Preconditions:** Current terms version differs from last accepted.
- **Business Rules References:** [IDN-010](DATA-002-business-rules-catalog.md#rule-idn-010).
- **Payload:** account identity, terms version, accepted time.
- **Side Effects:** Access gate lifted.

#### EVT-IDN-008 · AccountSuspended
- **Classification:** Domain · Integration · Audit · Business
- **Priority:** High
- **Description:** An account has been suspended (by policy or administration).
- **Business Meaning:** The user temporarily loses access; dependent activities pause.
- **Trigger:** Administrative or policy suspension.
- **Business Objects:** User Account, Role Assignment.
- **Producer:** Identity.
- **Consumers:** all domains (access), Notifications, Audit.
- **Preconditions:** Account active.
- **Business Rules References:** [IDN-009](DATA-002-business-rules-catalog.md#rule-idn-009).
- **Payload:** account identity, reason category, suspended time.
- **Side Effects:** Sessions revoked; user notified.

#### EVT-IDN-009 · AccountDeactivated
- **Classification:** Domain · Integration · Audit
- **Priority:** Medium
- **Description:** An account has been deactivated; audit history is preserved.
- **Business Meaning:** The identity is retired without losing accountability.
- **Trigger:** User/admin deactivation.
- **Business Objects:** User Account, Audit Log Entry.
- **Producer:** Identity.
- **Consumers:** all domains, Audit.
- **Preconditions:** Account active/suspended.
- **Business Rules References:** [IDN-007](DATA-002-business-rules-catalog.md#rule-idn-007).
- **Payload:** account identity, deactivated time.
- **Side Effects:** Access removed; audit retained; erasure handled separately via DSAR.

---

### 4.2 Participants (PRT)

---

#### EVT-PRT-001 · ParticipantCreated
- **Classification:** Domain
- **Priority:** Medium
- **Description:** A participant (child) record has been created under a guardian/teacher.
- **Business Meaning:** A child is being prepared for participation (not yet active).
- **Trigger:** Guardian/teacher creates a participant.
- **Business Objects:** Participant, Participant Profile.
- **Producer:** Participants.
- **Consumers:** Analytics, Audit.
- **Preconditions:** Creator is a verified guardian or authorized teacher.
- **Business Rules References:** [PRT-001](DATA-002-business-rules-catalog.md#rule-prt-001), [IDN-004](DATA-002-business-rules-catalog.md#rule-idn-004).
- **Payload:** participant identity, minimized profile facts, date of birth (for age derivation), creator identity, created time.
- **Side Effects:** Awaits verification and consent before activation.

#### EVT-PRT-002 · GuardianLinked
- **Classification:** Domain · Integration · Audit
- **Priority:** High
- **Description:** A verified guardian relationship to a participant has been established.
- **Business Meaning:** The responsible-adult link enabling consent and management exists.
- **Trigger:** Guardian link verified/accepted.
- **Business Objects:** Guardian Relationship, Guardian, Participant.
- **Producer:** Participants.
- **Consumers:** Identity (consent authority), Audit.
- **Preconditions:** Verified guardian; relationship proposed.
- **Business Rules References:** [PRT-001](DATA-002-business-rules-catalog.md#rule-prt-001), [PRT-003](DATA-002-business-rules-catalog.md#rule-prt-003), [PRT-008](DATA-002-business-rules-catalog.md#rule-prt-008).
- **Payload:** participant identity, guardian identity, relationship type, established time.
- **Side Effects:** Guardian may grant consent and manage the participant.

#### EVT-PRT-003 · ParticipantVerified
- **Classification:** Domain
- **Priority:** Medium
- **Description:** A participant's required details have been verified.
- **Business Meaning:** One prerequisite toward activation is met.
- **Trigger:** Verification of participant data.
- **Business Objects:** Participant.
- **Producer:** Participants.
- **Consumers:** Participants (activation), Audit.
- **Preconditions:** Required data present.
- **Business Rules References:** [PRT-001](DATA-002-business-rules-catalog.md#rule-prt-001), [PRT-002](DATA-002-business-rules-catalog.md#rule-prt-002).
- **Payload:** participant identity, verified time.
- **Side Effects:** Eligible for activation once consent + guardianship exist.

#### EVT-PRT-004 · ParticipantActivated
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** A participant has become Active and may enter competitions.
- **Business Meaning:** The child is ready to apply and perform.
- **Trigger:** All activation preconditions satisfied.
- **Business Objects:** Participant, Guardian Relationship, Consent.
- **Producer:** Participants.
- **Consumers:** Applications, Analytics, Audit.
- **Preconditions:** Verified guardianship/authority + active matching consent.
- **Business Rules References:** [PRT-001](DATA-002-business-rules-catalog.md#rule-prt-001), [IDN-003 (ConsentGranted)](DATA-002-business-rules-catalog.md#rule-idn-005).
- **Payload:** participant identity, activated time.
- **Side Effects:** Applications may now be created for the participant.

#### EVT-PRT-005 · ParticipantArchived
- **Classification:** Domain
- **Priority:** Low
- **Description:** A participant has been archived (inactive, history preserved).
- **Business Meaning:** The child is no longer actively participating.
- **Trigger:** Archival action or season end.
- **Business Objects:** Participant.
- **Producer:** Participants.
- **Consumers:** Analytics, Audit.
- **Preconditions:** No blocking active applications.
- **Business Rules References:** [PRT-007](DATA-002-business-rules-catalog.md#rule-prt-007) (distinct from erasure).
- **Payload:** participant identity, archived time.
- **Side Effects:** Excluded from active listings; retained per policy.

#### EVT-PRT-006 · ParticipantErasureRequested
- **Classification:** Domain · Integration · Audit · Business
- **Priority:** Critical
- **Description:** Erasure of a participant's personal data has been requested.
- **Business Meaning:** Triggers the privacy-critical erasure cascade.
- **Trigger:** DSAR or consent withdrawal leading to erasure.
- **Business Objects:** Participant, Data Subject Request, Retention Policy.
- **Producer:** Participants.
- **Consumers:** Performances, Finance, Audit.
- **Preconditions:** Verified request; no blocking legal hold.
- **Business Rules References:** [PRT-007](DATA-002-business-rules-catalog.md#rule-prt-007), [AUD-003](DATA-002-business-rules-catalog.md#rule-aud-003), [AUD-004](DATA-002-business-rules-catalog.md#rule-aud-004), [FIN-008](DATA-002-business-rules-catalog.md#rule-fin-008).
- **Payload:** participant identity, request reference, requested time.
- **Side Effects:** Cascade to media/derived data; financial/audit records retained under lawful basis; erasure record produced on completion.

---

### 4.3 Institutions (INS)

---

#### EVT-INS-001 · InstitutionRegistered
- **Classification:** Domain · Business
- **Priority:** Medium
- **Description:** An institution has been registered on the platform.
- **Business Meaning:** A potential scaled partner has joined (BG-5).
- **Trigger:** Institution registration submitted.
- **Business Objects:** Institution, Institution Profile.
- **Producer:** Institutions.
- **Consumers:** Notifications, Analytics, Audit.
- **Preconditions:** Registrant account verified.
- **Business Rules References:** [INS-005](DATA-002-business-rules-catalog.md#rule-ins-005).
- **Payload:** institution identity, name, type, region, locality, registered time.
- **Side Effects:** Verification workflow initiated.

#### EVT-INS-002 · InstitutionVerified
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** An institution's legitimacy has been verified.
- **Business Meaning:** Bulk workflows and institutional analytics unlock.
- **Trigger:** Successful verification review.
- **Business Objects:** Institution, Institution Verification.
- **Producer:** Institutions.
- **Consumers:** Participants, Analytics, Notifications, Audit.
- **Preconditions:** Evidence validated.
- **Business Rules References:** [INS-001](DATA-002-business-rules-catalog.md#rule-ins-001), [INS-005](DATA-002-business-rules-catalog.md#rule-ins-005).
- **Payload:** institution identity, verified time.
- **Side Effects:** Bulk features and analytics enabled.

#### EVT-INS-003 · TeacherAssigned
- **Classification:** Domain · Integration · Audit
- **Priority:** Medium
- **Description:** A teacher has been assigned to an institution/class.
- **Business Meaning:** Delegated management authority granted within tenancy.
- **Trigger:** Institution administrator assigns a teacher.
- **Business Objects:** Teacher Assignment, Teacher, Class Group, Institution.
- **Producer:** Institutions.
- **Consumers:** Participants, Audit.
- **Preconditions:** Assignment within the institution's scope.
- **Business Rules References:** [INS-002](DATA-002-business-rules-catalog.md#rule-ins-002), [INS-003](DATA-002-business-rules-catalog.md#rule-ins-003), [PRT-004](DATA-002-business-rules-catalog.md#rule-prt-004).
- **Payload:** teacher identity, institution identity, class group reference, assigned-by, assigned time.
- **Side Effects:** Teacher scope activated; delegation audited.

#### EVT-INS-004 · ClassGroupCreated
- **Classification:** Domain
- **Priority:** Low
- **Description:** A class/group has been created within an institution.
- **Business Meaning:** A teaching unit for organizing participants exists.
- **Trigger:** Class group creation.
- **Business Objects:** Class Group, Institution.
- **Producer:** Institutions.
- **Consumers:** Participants, Analytics, Audit.
- **Preconditions:** Institution active; single-institution ownership.
- **Business Rules References:** [INS-004](DATA-002-business-rules-catalog.md#rule-ins-004).
- **Payload:** class group identity, institution identity, name, responsible teacher, created time.
- **Side Effects:** Participants may be grouped.

#### EVT-INS-005 · ParticipantJoinedInstitution
- **Classification:** Domain · Integration
- **Priority:** Low
- **Description:** A participant became a member of an institution.
- **Business Meaning:** Institutional scoping and analytics now include the participant.
- **Trigger:** Membership approved.
- **Business Objects:** Participant Institution Membership, Participant, Institution.
- **Producer:** Institutions.
- **Consumers:** Analytics, Audit.
- **Preconditions:** Institution verified; membership requested/approved.
- **Business Rules References:** [INS-002](DATA-002-business-rules-catalog.md#rule-ins-002), [INS-004](DATA-002-business-rules-catalog.md#rule-ins-004).
- **Payload:** participant identity, institution identity, joined time.
- **Side Effects:** Participant appears under institutional scope.

---

### 4.4 Competitions (CMP)

---

#### EVT-CMP-001 · CompetitionCreated
- **Classification:** Domain
- **Priority:** Low
- **Description:** A competition has been created in Draft.
- **Business Meaning:** An organizer has begun configuring an event.
- **Trigger:** Organizer creates a competition.
- **Business Objects:** Competition, Organizer Assignment.
- **Producer:** Competitions.
- **Consumers:** Analytics, Audit.
- **Preconditions:** Creator has an organizer assignment.
- **Business Rules References:** [CMP-008](DATA-002-business-rules-catalog.md#rule-cmp-008).
- **Payload:** competition identity, title, organizer identity, created time.
- **Side Effects:** Configuration begins.

#### EVT-CMP-002 · CriteriaSetFrozen
- **Classification:** Domain · Integration
- **Priority:** High
- **Description:** A criteria set has been frozen for scoring.
- **Business Meaning:** The rubric is fixed; judges will score against exactly this.
- **Trigger:** A round enters scoring / organizer freezes criteria.
- **Business Objects:** Criteria Set, Judging Criterion, Round.
- **Producer:** Competitions.
- **Consumers:** Judging, Audit.
- **Preconditions:** Weights sum correctly; set published.
- **Business Rules References:** [CMP-004](DATA-002-business-rules-catalog.md#rule-cmp-004), [CMP-005](DATA-002-business-rules-catalog.md#rule-cmp-005), [JDG-004](DATA-002-business-rules-catalog.md#rule-jdg-004).
- **Payload:** criteria set identity, competition/round reference, version, frozen time.
- **Side Effects:** Scorecards structured from the frozen set; edits blocked.

#### EVT-CMP-003 · CompetitionPublished
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** A competition has been published and is visible.
- **Business Meaning:** The event is announced to the audience (marketing milestone, BG-2).
- **Trigger:** Organizer publishes a structurally complete competition.
- **Business Objects:** Competition, Nomination, Age Group, Criteria Set, Competition Announcement.
- **Producer:** Competitions.
- **Consumers:** Notifications, Analytics, Audit.
- **Preconditions:** Structural completeness; consistent schedule.
- **Business Rules References:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [CMP-002](DATA-002-business-rules-catalog.md#rule-cmp-002), [CMP-003](DATA-002-business-rules-catalog.md#rule-cmp-003).
- **Payload:** competition identity, title, nominations, age groups, key dates, published time.
- **Side Effects:** Announcement notifications; discoverable to prospective participants.

#### EVT-CMP-004 · CompetitionOpened
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** The application window has opened.
- **Business Meaning:** Participants may now apply.
- **Trigger:** Schedule reaches the open date.
- **Business Objects:** Competition, Competition Schedule.
- **Producer:** Competitions.
- **Consumers:** Applications, Notifications, Analytics, Audit.
- **Preconditions:** Competition published; open date reached.
- **Business Rules References:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [CMP-003](DATA-002-business-rules-catalog.md#rule-cmp-003).
- **Payload:** competition identity, opened time, close date.
- **Side Effects:** Application intake enabled; reminders scheduled.

#### EVT-CMP-005 · SubmissionWindowClosed
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** The submission window has closed.
- **Business Meaning:** No further entries/performances; judging can be prepared.
- **Trigger:** Schedule reaches the close date.
- **Business Objects:** Competition, Competition Schedule, Application, Performance.
- **Producer:** Competitions.
- **Consumers:** Applications, Performances, Judging, Notifications, Audit.
- **Preconditions:** Open window elapsed.
- **Business Rules References:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [APP-005](DATA-002-business-rules-catalog.md#rule-app-005).
- **Payload:** competition identity, closed time.
- **Side Effects:** Intake disabled; late withdrawals require approval; judging preparation begins.

#### EVT-CMP-006 · JudgingStarted
- **Classification:** Domain · Integration · Business
- **Priority:** Critical
- **Description:** The competition has entered the judging phase.
- **Business Meaning:** Scoring begins under frozen structure (fairness milestone).
- **Trigger:** Transition to Judging after submission close.
- **Business Objects:** Competition, Round, Criteria Set, Jury Panel.
- **Producer:** Competitions.
- **Consumers:** Judging, Notifications, Audit.
- **Preconditions:** Submission window closed; criteria frozen; panels formed.
- **Business Rules References:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [CMP-005](DATA-002-business-rules-catalog.md#rule-cmp-005), [JDG-003](DATA-002-business-rules-catalog.md#rule-jdg-003).
- **Payload:** competition identity, round reference, scoring window, started time.
- **Side Effects:** Judge assignments activated; structure locked.

#### EVT-CMP-007 · CompetitionResultsPhaseEntered
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** The competition has entered the results phase.
- **Business Meaning:** Judging finalized; results may be published.
- **Trigger:** Transition to Results after judging finalization.
- **Business Objects:** Competition, Result, Ranking.
- **Producer:** Competitions.
- **Consumers:** Results, Notifications, Audit.
- **Preconditions:** Aggregation finalized.
- **Business Rules References:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [RES-001](DATA-002-business-rules-catalog.md#rule-res-001).
- **Payload:** competition identity, entered time.
- **Side Effects:** Results publication permitted.

#### EVT-CMP-008 · CompetitionArchived
- **Classification:** Domain · Business
- **Priority:** Low
- **Description:** The competition has been archived.
- **Business Meaning:** The event is complete and read-only.
- **Trigger:** Archival after results.
- **Business Objects:** Competition, Result Snapshot.
- **Producer:** Competitions.
- **Consumers:** Analytics, Audit.
- **Preconditions:** Results published.
- **Business Rules References:** [CMP-006](DATA-002-business-rules-catalog.md#rule-cmp-006).
- **Payload:** competition identity, archived time.
- **Side Effects:** Structure immutable; retained per policy.

#### EVT-CMP-009 · CompetitionCancelled
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** The competition has been cancelled.
- **Business Meaning:** The event will not proceed; entries/fees must be unwound.
- **Trigger:** Organizer/admin cancellation.
- **Business Objects:** Competition, Application, Order.
- **Producer:** Competitions.
- **Consumers:** Applications, Finance (refunds), Notifications, Audit.
- **Preconditions:** Competition not archived.
- **Business Rules References:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [FIN-004](DATA-002-business-rules-catalog.md#rule-fin-004).
- **Payload:** competition identity, reason, cancelled time.
- **Side Effects:** Applications voided; refunds initiated; participants notified.

---

### 4.5 Applications (APP)

---

#### EVT-APP-001 · ApplicationSubmitted
- **Classification:** Domain · Integration · Business · Audit
- **Priority:** High
- **Description:** A participant's application to a nomination has been submitted.
- **Business Meaning:** An entry has entered the pipeline (core funnel, BG-1).
- **Trigger:** Guardian/teacher submits an application.
- **Business Objects:** Application, Participant, Competition, Nomination, Consent Snapshot.
- **Producer:** Applications.
- **Consumers:** Competitions, Finance (if paid), Performances, Notifications, Analytics, Audit.
- **Preconditions:** Participant active; active matching consent captured as snapshot; competition open.
- **Business Rules References:** [APP-001](DATA-002-business-rules-catalog.md#rule-app-001), [APP-006](DATA-002-business-rules-catalog.md#rule-app-006), [PRT-002](DATA-002-business-rules-catalog.md#rule-prt-002).
- **Payload:** application identity, participant identity, competition/nomination reference, derived age group, submitter identity, submitted time.
- **Side Effects:** Eligibility check triggered; fee assessed if paid; confirmation notification.

#### EVT-APP-002 · EligibilityChecked
- **Classification:** Domain
- **Priority:** High
- **Description:** An application has been evaluated against eligibility rules.
- **Business Meaning:** Determines whether the entry can be accepted.
- **Trigger:** Eligibility evaluation.
- **Business Objects:** Eligibility Check, Application, Eligibility Rule, Age Group.
- **Producer:** Applications.
- **Consumers:** Applications (acceptance), Notifications, Audit.
- **Preconditions:** Application submitted.
- **Business Rules References:** [APP-002](DATA-002-business-rules-catalog.md#rule-app-002), [APP-004](DATA-002-business-rules-catalog.md#rule-app-004).
- **Payload:** application identity, outcome, failure reasons (if any), evaluated time.
- **Side Effects:** Pass → acceptance path; fail → reasons surfaced.

#### EVT-APP-003 · ApplicationAccepted
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** An application has been accepted into the competition.
- **Business Meaning:** The participant is officially entered; performances expected.
- **Trigger:** Passing eligibility (+ payment if paid).
- **Business Objects:** Application, Competition, Nomination, Performance (expected).
- **Producer:** Applications.
- **Consumers:** Performances, Notifications, Analytics, Audit.
- **Preconditions:** Eligibility passed; order Paid if competition is paid.
- **Business Rules References:** [APP-002](DATA-002-business-rules-catalog.md#rule-app-002), [APP-003](DATA-002-business-rules-catalog.md#rule-app-003).
- **Payload:** application identity, participant identity, competition/nomination reference, accepted time.
- **Side Effects:** Performance submission enabled; acceptance notification.

#### EVT-APP-004 · ApplicationWaitlisted
- **Classification:** Domain · Business
- **Priority:** Medium
- **Description:** An application has been placed on a waitlist due to capacity.
- **Business Meaning:** The entry may be promoted if space frees.
- **Trigger:** Capacity reached at acceptance time.
- **Business Objects:** Waitlist Entry, Application, Competition.
- **Producer:** Applications.
- **Consumers:** Notifications, Analytics, Audit.
- **Preconditions:** Eligible but no capacity.
- **Business Rules References:** [APP-007](DATA-002-business-rules-catalog.md#rule-app-007).
- **Payload:** application identity, waitlist position, waitlisted time.
- **Side Effects:** Queued for promotion; applicant notified.

#### EVT-APP-005 · ApplicationRejected
- **Classification:** Domain · Business
- **Priority:** Medium
- **Description:** An application has been rejected.
- **Business Meaning:** The entry will not proceed.
- **Trigger:** Failed eligibility or organizer decision.
- **Business Objects:** Application, Eligibility Check.
- **Producer:** Applications.
- **Consumers:** Notifications, Analytics, Audit.
- **Preconditions:** Failing eligibility or documented decision.
- **Business Rules References:** [APP-002](DATA-002-business-rules-catalog.md#rule-app-002).
- **Payload:** application identity, reasons, rejected time.
- **Side Effects:** Applicant notified with reasons; any held fee refunded.

#### EVT-APP-006 · ApplicationWithdrawn
- **Classification:** Domain · Integration · Business · Audit
- **Priority:** Medium
- **Description:** An application has been withdrawn.
- **Business Meaning:** The participant exits the competition; downstream must unwind.
- **Trigger:** Withdrawal before cutoff (or approved after).
- **Business Objects:** Application, Application Withdrawal, Performance, Order.
- **Producer:** Applications.
- **Consumers:** Performances, Finance (refund), Notifications, Audit.
- **Preconditions:** Before cutoff and not yet judged (else approval).
- **Business Rules References:** [APP-005](DATA-002-business-rules-catalog.md#rule-app-005), [CMP-005](DATA-002-business-rules-catalog.md#rule-cmp-005).
- **Payload:** application identity, participant identity, withdrawn time, reason.
- **Side Effects:** Performances voided; refund per policy; audit recorded.

---

### 4.6 Performances (PRF)

---

#### EVT-PRF-001 · PerformanceUploaded
- **Classification:** Domain
- **Priority:** High
- **Description:** A performance (creative work) with its media has been uploaded.
- **Business Meaning:** The work is present but not yet safe/cleared for judging.
- **Trigger:** Submitter uploads a performance.
- **Business Objects:** Performance, Media Asset, Application.
- **Producer:** Performances.
- **Consumers:** Performances (scan/moderation), Analytics, Audit.
- **Preconditions:** Application accepted; media meets requirements.
- **Business Rules References:** [PRF-003](DATA-002-business-rules-catalog.md#rule-prf-003), [PRF-004](DATA-002-business-rules-catalog.md#rule-prf-004).
- **Payload:** performance identity, application reference, media references, title, uploaded time.
- **Side Effects:** Antivirus scan and moderation initiated.

#### EVT-PRF-002 · MediaScanCompleted
- **Classification:** Domain · Integration
- **Priority:** Critical
- **Description:** The safety (antivirus) scan of a performance's media has completed.
- **Business Meaning:** Determines whether media may ever be exposed or judged.
- **Trigger:** Scan result available.
- **Business Objects:** Media Asset, Antivirus Scan Result, Performance.
- **Producer:** Performances.
- **Consumers:** Performances (readiness), Notifications (if infected), Audit.
- **Preconditions:** Media uploaded.
- **Business Rules References:** [PRF-001](DATA-002-business-rules-catalog.md#rule-prf-001), [PRF-002](DATA-002-business-rules-catalog.md#rule-prf-002).
- **Payload:** performance identity, media reference, scan outcome (clean/infected), scanned time.
- **Side Effects:** Clean → moderation path; infected → quarantine + replace request.

#### EVT-PRF-003 · PerformanceModerationCleared
- **Classification:** Domain · Integration
- **Priority:** High
- **Description:** A performance has passed content moderation.
- **Business Meaning:** The work is appropriate for a children's platform.
- **Trigger:** Moderation clears the performance.
- **Business Objects:** Content Moderation Flag, Performance.
- **Producer:** Performances.
- **Consumers:** Performances (acceptance), Audit.
- **Preconditions:** Scan clean; moderation reviewed.
- **Business Rules References:** [PRF-001](DATA-002-business-rules-catalog.md#rule-prf-001), [PRF-006](DATA-002-business-rules-catalog.md#rule-prf-006).
- **Payload:** performance identity, cleared time.
- **Side Effects:** Eligible for acceptance and judging.

#### EVT-PRF-004 · PerformanceAccepted
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** A performance is accepted and ready for judging.
- **Business Meaning:** The work will be evaluated.
- **Trigger:** Scan clean + moderation cleared + requirements met.
- **Business Objects:** Performance, Application.
- **Producer:** Performances.
- **Consumers:** Judging, Notifications, Analytics, Audit.
- **Preconditions:** All safety/quality gates passed.
- **Business Rules References:** [PRF-001](DATA-002-business-rules-catalog.md#rule-prf-001), [PRF-005](DATA-002-business-rules-catalog.md#rule-prf-005).
- **Payload:** performance identity, application reference, pseudonymized participant alias, accepted time.
- **Side Effects:** Enters the judging pool (identity withheld from jury).

#### EVT-PRF-005 · PerformanceRejected
- **Classification:** Domain · Business
- **Priority:** High
- **Description:** A performance has been rejected (unsafe, non-conforming, or moderation-upheld).
- **Business Meaning:** The work will not be judged.
- **Trigger:** Failed scan/moderation/requirements, or upheld high-severity flag.
- **Business Objects:** Performance, Content Moderation Flag, Antivirus Scan Result.
- **Producer:** Performances.
- **Consumers:** Notifications, Analytics, Audit.
- **Preconditions:** A blocking condition confirmed.
- **Business Rules References:** [PRF-002](DATA-002-business-rules-catalog.md#rule-prf-002), [PRF-006](DATA-002-business-rules-catalog.md#rule-prf-006).
- **Payload:** performance identity, reason, rejected time.
- **Side Effects:** Excluded from judging; submitter notified to replace (if time permits).

#### EVT-PRF-006 · PerformanceVersionCreated
- **Classification:** Domain
- **Priority:** Medium
- **Description:** A new version of a performance has been created via re-submission.
- **Business Meaning:** The work was revised before the deadline.
- **Trigger:** Re-submission before deadline.
- **Business Objects:** Performance Version, Performance.
- **Producer:** Performances.
- **Consumers:** Performances (which version is judged), Audit.
- **Preconditions:** Before submission close; round not yet open.
- **Business Rules References:** [PRF-005](DATA-002-business-rules-catalog.md#rule-prf-005).
- **Payload:** performance identity, version reference, created time.
- **Side Effects:** Active version updated; frozen when round opens.

---

### 4.7 Judging (JDG)

---

#### EVT-JDG-001 · JuryPanelFormed
- **Classification:** Domain · Audit
- **Priority:** High
- **Description:** A jury panel has been formed for a competition/round scope.
- **Business Meaning:** The evaluators are organized to begin judging.
- **Trigger:** Panel composition finalized.
- **Business Objects:** Jury Panel, Panel Membership, Jury Member.
- **Producer:** Judging.
- **Consumers:** Judging (assignment), Audit.
- **Preconditions:** Jury members confirmed; MFA enrolled.
- **Business Rules References:** [IDN-002](DATA-002-business-rules-catalog.md#rule-idn-002), [JDG-007](DATA-002-business-rules-catalog.md#rule-jdg-007).
- **Payload:** panel identity, competition/round reference, member identities, formed time.
- **Side Effects:** Assignments may be created within panel scope.

#### EVT-JDG-002 · JudgeAssigned
- **Classification:** Domain · Integration · Audit
- **Priority:** High
- **Description:** A performance has been assigned to a jury member for a round.
- **Business Meaning:** Defines who scores what — the unit of judging work.
- **Trigger:** Assignment created (respecting conflicts).
- **Business Objects:** Judge Assignment, Jury Member, Performance, Round.
- **Producer:** Judging.
- **Consumers:** Judging (scoring), Notifications, Audit.
- **Preconditions:** No conflict of interest; performance accepted; round open.
- **Business Rules References:** [JDG-001](DATA-002-business-rules-catalog.md#rule-jdg-001), [JDG-002](DATA-002-business-rules-catalog.md#rule-jdg-002), [JDG-007](DATA-002-business-rules-catalog.md#rule-jdg-007).
- **Payload:** assignment identity, jury member identity, performance reference (pseudonymized), round reference, assigned time.
- **Side Effects:** Judge may open a scorecard; conflicts block assignment.

#### EVT-JDG-003 · ConflictDeclared
- **Classification:** Domain · Audit
- **Priority:** Critical
- **Description:** A jury member has declared a conflict of interest.
- **Business Meaning:** Protects fairness by disclosing potential bias.
- **Trigger:** Conflict declaration filed.
- **Business Objects:** Conflict of Interest Declaration, Jury Member.
- **Producer:** Judging.
- **Consumers:** Judging (assignment/recusal), Audit.
- **Preconditions:** Potential conflict exists.
- **Business Rules References:** [JDG-001](DATA-002-business-rules-catalog.md#rule-jdg-001), [JDG-007](DATA-002-business-rules-catalog.md#rule-jdg-007).
- **Payload:** declaration identity, jury member identity, subject reference, nature, declared time.
- **Side Effects:** Affected assignments blocked; may lead to recusal.

#### EVT-JDG-004 · JudgeRecused
- **Classification:** Domain · Integration · Audit
- **Priority:** Critical
- **Description:** A jury member has been recused from a performance.
- **Business Meaning:** Their evaluations for it are void; aggregation excludes them.
- **Trigger:** Recusal effective (accepted conflict).
- **Business Objects:** Recusal, Jury Member, Scorecard, Score Aggregation.
- **Producer:** Judging.
- **Consumers:** Judging (aggregation), Audit.
- **Preconditions:** Accepted conflict or governance decision.
- **Business Rules References:** [JDG-011](DATA-002-business-rules-catalog.md#rule-jdg-011), [JDG-009](DATA-002-business-rules-catalog.md#rule-jdg-009).
- **Payload:** recusal identity, jury member identity, performance reference, effective time.
- **Side Effects:** Affected scores voided; aggregation recomputed.

#### EVT-JDG-005 · ScorecardSubmitted
- **Classification:** Domain · Integration · Audit · Business
- **Priority:** Critical
- **Description:** A jury member has submitted a complete scorecard for a performance.
- **Business Meaning:** A binding, auditable evaluation has been cast.
- **Trigger:** Scorecard submission within the scoring window.
- **Business Objects:** Scorecard, Criterion Score, Judge Assignment, Performance.
- **Producer:** Judging.
- **Consumers:** Judging (aggregation), Audit, Analytics.
- **Preconditions:** Within open scoring window; full rubric scored; scores in range.
- **Business Rules References:** [JDG-003](DATA-002-business-rules-catalog.md#rule-jdg-003), [JDG-004](DATA-002-business-rules-catalog.md#rule-jdg-004), [JDG-005](DATA-002-business-rules-catalog.md#rule-jdg-005), [JDG-008](DATA-002-business-rules-catalog.md#rule-jdg-008).
- **Payload:** scorecard identity, assignment reference, performance reference (pseudonymized), per-criterion score values, submitted time.
- **Side Effects:** Scorecard locked and immutable; audit recorded; counts toward aggregation.

#### EVT-JDG-006 · ScoringWindowClosed
- **Classification:** Domain · Integration
- **Priority:** High
- **Description:** The scoring window for a round has closed.
- **Business Meaning:** No further scores; aggregation may run.
- **Trigger:** Schedule reaches window end.
- **Business Objects:** Scoring Window, Round, Scorecard.
- **Producer:** Judging.
- **Consumers:** Judging (aggregation), Notifications, Audit.
- **Preconditions:** Window open elapsed (or approved extension ended).
- **Business Rules References:** [JDG-003](DATA-002-business-rules-catalog.md#rule-jdg-003), [JDG-008](DATA-002-business-rules-catalog.md#rule-jdg-008).
- **Payload:** round reference, closed time.
- **Side Effects:** Late scores blocked; aggregation triggered.

#### EVT-JDG-007 · ScoreAggregated
- **Classification:** Domain · Integration · Business
- **Priority:** Critical
- **Description:** Valid scorecards for a performance have been aggregated into a comparable value.
- **Business Meaning:** Produces the standing that feeds ranking (fairness-critical calculation).
- **Trigger:** Aggregation computed after window close.
- **Business Objects:** Score Aggregation, Scorecard, Performance, Criteria Set.
- **Producer:** Judging.
- **Consumers:** Results, Analytics, Audit.
- **Preconditions:** Only valid, non-recused, locked scorecards included.
- **Business Rules References:** [JDG-009](DATA-002-business-rules-catalog.md#rule-jdg-009), [JDG-011](DATA-002-business-rules-catalog.md#rule-jdg-011).
- **Payload:** aggregation identity, performance reference, round reference, aggregated value, contributing count, method, computed time.
- **Side Effects:** Feeds ranking; ties flagged for tie-break.

#### EVT-JDG-008 · TieBreakDecided
- **Classification:** Domain · Audit
- **Priority:** High
- **Description:** A tie affecting ranking/awards has been resolved.
- **Business Meaning:** Ensures deterministic ordering before finalization.
- **Trigger:** Tie-break decision recorded.
- **Business Objects:** Tie-Break Decision, Score Aggregation, Ranking.
- **Producer:** Judging.
- **Consumers:** Results, Audit.
- **Preconditions:** A tie affects an award/cut line.
- **Business Rules References:** [JDG-010](DATA-002-business-rules-catalog.md#rule-jdg-010).
- **Payload:** decision identity, tied performances, resolution, decided time.
- **Side Effects:** Ranking may be finalized.

---

### 4.8 Results (RES)

---

#### EVT-RES-001 · RankingFinalized
- **Classification:** Domain · Integration
- **Priority:** High
- **Description:** The ranking for a cohort/round has been finalized.
- **Business Meaning:** Standings are fixed and ready to publish.
- **Trigger:** Aggregation final + ties resolved.
- **Business Objects:** Ranking, Ranking Entry, Score Aggregation, Tie-Break Decision.
- **Producer:** Results.
- **Consumers:** Results (publication), Audit.
- **Preconditions:** Aggregations final; ties resolved.
- **Business Rules References:** [RES-003](DATA-002-business-rules-catalog.md#rule-res-003), [JDG-010](DATA-002-business-rules-catalog.md#rule-jdg-010).
- **Payload:** ranking identity, competition/nomination/age-group/round scope, ordered entries, finalized time.
- **Side Effects:** Publication permitted; prize allocation prepared.

#### EVT-RES-002 · ResultPublished
- **Classification:** Domain · Integration · Business · Audit
- **Priority:** Critical
- **Description:** Official results have been published.
- **Business Meaning:** The platform's most visible output; recognition becomes real.
- **Trigger:** Publication after judging finalization.
- **Business Objects:** Result, Ranking, Result Publication, Result Snapshot.
- **Producer:** Results.
- **Consumers:** Notifications, Results (diplomas), Analytics, Audit.
- **Preconditions:** Judging finalized; ranking final.
- **Business Rules References:** [RES-001](DATA-002-business-rules-catalog.md#rule-res-001), [RES-002](DATA-002-business-rules-catalog.md#rule-res-002), [RES-006](DATA-002-business-rules-catalog.md#rule-res-006).
- **Payload:** competition/nomination reference, published ranking reference, published time; participant identity disclosed only where authorized/consented.
- **Side Effects:** Result snapshot captured; diplomas generated; participants notified; leaderboards updated (privacy-respecting).

#### EVT-RES-003 · DiplomaGenerated
- **Classification:** Domain · Integration · Business
- **Priority:** High
- **Description:** A diploma/certificate has been generated for a published result.
- **Business Meaning:** The recognized artifact a participant receives (BG-6).
- **Trigger:** Diploma generation after publication.
- **Business Objects:** Diploma, Certificate, Result, Participant.
- **Producer:** Results.
- **Consumers:** Notifications (delivery), Audit.
- **Preconditions:** Result published.
- **Business Rules References:** [RES-004](DATA-002-business-rules-catalog.md#rule-res-004), [RES-005](DATA-002-business-rules-catalog.md#rule-res-005).
- **Payload:** diploma identity, participant identity, competition reference, award level, verification code, issued time.
- **Side Effects:** Delivery notification; verification code registered.

#### EVT-RES-004 · PrizeAllocated
- **Classification:** Domain · Business
- **Priority:** Medium
- **Description:** A prize has been allocated to a winner.
- **Business Meaning:** Rewards are assigned per ranking within quantity limits.
- **Trigger:** Allocation after ranking finalization.
- **Business Objects:** Prize Allocation, Prize, Ranking, Participant.
- **Producer:** Results.
- **Consumers:** Notifications, Finance (if payout), Audit.
- **Preconditions:** Ranking final; prize quantity available.
- **Business Rules References:** [RES-008](DATA-002-business-rules-catalog.md#rule-res-008), [CMP-007](DATA-002-business-rules-catalog.md#rule-cmp-007).
- **Payload:** allocation identity, prize reference, participant identity, allocated time.
- **Side Effects:** Winner notified; any payout initiated.

#### EVT-RES-005 · ResultDisputed
- **Classification:** Domain · Integration · Audit · Business
- **Priority:** High
- **Description:** A challenge to a published result has been raised.
- **Business Meaning:** Enters fair remediation; contributes to dispute-rate KPI (BG-3).
- **Trigger:** Dispute filed.
- **Business Objects:** Result Dispute, Result.
- **Producer:** Results.
- **Consumers:** Results (resolution), Notifications, Audit.
- **Preconditions:** Result published; within dispute window.
- **Business Rules References:** [RES-002](DATA-002-business-rules-catalog.md#rule-res-002), [RES-007](DATA-002-business-rules-catalog.md#rule-res-007).
- **Payload:** dispute identity, result reference, grounds, raised-by, raised time.
- **Side Effects:** Review workflow started.

#### EVT-RES-006 · DisputeResolved
- **Classification:** Domain · Integration · Audit · Business
- **Priority:** High
- **Description:** A result dispute has been resolved.
- **Business Meaning:** Confirms or corrects an official outcome.
- **Trigger:** Dispute decision recorded.
- **Business Objects:** Dispute Resolution, Result Dispute, Result, Diploma.
- **Producer:** Results.
- **Consumers:** Results (correction), Notifications, Audit.
- **Preconditions:** Dispute reviewed.
- **Business Rules References:** [RES-007](DATA-002-business-rules-catalog.md#rule-res-007), [RES-002](DATA-002-business-rules-catalog.md#rule-res-002).
- **Payload:** dispute identity, outcome (upheld/rejected), resolution summary, decided time.
- **Side Effects:** Upheld → governed result correction + diploma reissue; all audited.

---

### 4.9 Finance (FIN)

---

#### EVT-FIN-001 · OrderCreated
- **Classification:** Domain
- **Priority:** High
- **Description:** A purchase intent (order) has been created (e.g., paid entry).
- **Business Meaning:** Establishes what is owed before payment.
- **Trigger:** Paid application or plan purchase.
- **Business Objects:** Order, Billing Account, Invoice Line Item, Application Fee.
- **Producer:** Finance.
- **Consumers:** Finance (payment), Notifications, Audit.
- **Preconditions:** Priced items exist; single currency.
- **Business Rules References:** [FIN-001](DATA-002-business-rules-catalog.md#rule-fin-001), [FIN-003](DATA-002-business-rules-catalog.md#rule-fin-003).
- **Payload:** order identity, billing account reference, line items, total (Money), currency, created time.
- **Side Effects:** Payment awaited; acceptance gated on payment.

#### EVT-FIN-002 · DiscountApplied
- **Classification:** Domain
- **Priority:** Low
- **Description:** A valid discount code has been applied to an order.
- **Business Meaning:** Reduces the amount owed.
- **Trigger:** Coupon redemption.
- **Business Objects:** Coupon Redemption, Discount Code, Order.
- **Producer:** Finance.
- **Consumers:** Finance (recompute), Audit.
- **Preconditions:** Code active, applicable, within limits.
- **Business Rules References:** [FIN-007](DATA-002-business-rules-catalog.md#rule-fin-007), [FIN-003](DATA-002-business-rules-catalog.md#rule-fin-003).
- **Payload:** order identity, code reference, discount amount (Money), applied time.
- **Side Effects:** Order total recomputed.

#### EVT-FIN-003 · InvoiceIssued
- **Classification:** Domain · Business
- **Priority:** Medium
- **Description:** A formal invoice has been issued for an order.
- **Business Meaning:** The billing document of record.
- **Trigger:** Invoice issuance.
- **Business Objects:** Invoice, Invoice Line Item, Order, Tax Rate.
- **Producer:** Finance.
- **Consumers:** Notifications, Audit.
- **Preconditions:** Order finalized.
- **Business Rules References:** [FIN-005](DATA-002-business-rules-catalog.md#rule-fin-005).
- **Payload:** invoice number, order reference, line items, tax, total (Money), issued time.
- **Side Effects:** Immutable once issued; correction via void/reissue.

#### EVT-FIN-004 · PaymentCaptured
- **Classification:** Domain · Integration · Business · Audit
- **Priority:** Critical
- **Description:** Money for an order has been captured (settled).
- **Business Meaning:** Unlocks paid entitlements (e.g., acceptance).
- **Trigger:** Successful payment capture.
- **Business Objects:** Payment, Payment Transaction, Order, Receipt.
- **Producer:** Finance.
- **Consumers:** Applications (acceptance gate), Notifications (receipt), Audit.
- **Preconditions:** Authorized payment; exact Money amount.
- **Business Rules References:** [FIN-001](DATA-002-business-rules-catalog.md#rule-fin-001), [FIN-006](DATA-002-business-rules-catalog.md#rule-fin-006), [APP-003](DATA-002-business-rules-catalog.md#rule-app-003).
- **Payload:** payment identity, order reference, amount (Money), captured time.
- **Side Effects:** Order marked Paid; acceptance may proceed; receipt issued; audit recorded.

#### EVT-FIN-005 · PaymentFailed
- **Classification:** Domain · Business · Audit
- **Priority:** High
- **Description:** A payment attempt has failed.
- **Business Meaning:** Entitlement remains withheld; retry/alternative needed.
- **Trigger:** Failed authorization/capture.
- **Business Objects:** Payment, Payment Transaction, Order.
- **Producer:** Finance.
- **Consumers:** Notifications, Audit.
- **Preconditions:** Payment attempted.
- **Business Rules References:** [FIN-006](DATA-002-business-rules-catalog.md#rule-fin-006), [APP-003](DATA-002-business-rules-catalog.md#rule-app-003).
- **Payload:** payment identity, order reference, failure reason, failed time.
- **Side Effects:** User prompted to retry; acceptance still gated.

#### EVT-FIN-006 · RefundProcessed
- **Classification:** Domain · Integration · Business · Audit
- **Priority:** High
- **Description:** A refund against a payment has been processed.
- **Business Meaning:** Money returned (e.g., withdrawal/cancellation).
- **Trigger:** Approved refund.
- **Business Objects:** Refund, Payment, Order.
- **Producer:** Finance.
- **Consumers:** Notifications, Audit.
- **Preconditions:** Refund ≤ captured amount.
- **Business Rules References:** [FIN-004](DATA-002-business-rules-catalog.md#rule-fin-004), [FIN-006](DATA-002-business-rules-catalog.md#rule-fin-006).
- **Payload:** refund identity, payment reference, amount (Money), reason, processed time.
- **Side Effects:** Payer notified; balances updated; audit recorded.

---

### 4.10 Notifications (NTF)

---

#### EVT-NTF-001 · NotificationQueued
- **Classification:** Domain
- **Priority:** Medium
- **Description:** A notification has been prepared and queued for dispatch.
- **Business Meaning:** A user is about to be informed of something.
- **Trigger:** A domain event requiring communication.
- **Business Objects:** Notification, Notification Template, Notification Preference.
- **Producer:** Notifications.
- **Consumers:** Notifications (dispatch), Audit.
- **Preconditions:** Recipient permitted on a channel; template exists in primary locale.
- **Business Rules References:** [NTF-001](DATA-002-business-rules-catalog.md#rule-ntf-001), [NTF-003](DATA-002-business-rules-catalog.md#rule-ntf-003).
- **Payload:** notification identity, recipient identity, topic, template reference, queued time.
- **Side Effects:** Scheduled for sending per priority.

#### EVT-NTF-002 · NotificationSent
- **Classification:** Domain · Integration
- **Priority:** Medium
- **Description:** A notification has been sent on a channel.
- **Business Meaning:** The platform has attempted to reach the user.
- **Trigger:** Dispatch to a channel.
- **Business Objects:** Notification, Message, Notification Channel.
- **Producer:** Notifications.
- **Consumers:** Analytics (delivery metrics), Audit.
- **Preconditions:** Queued and permitted.
- **Business Rules References:** [NTF-001](DATA-002-business-rules-catalog.md#rule-ntf-001), [NTF-004](DATA-002-business-rules-catalog.md#rule-ntf-004), [NTF-005](DATA-002-business-rules-catalog.md#rule-ntf-005).
- **Payload:** notification identity, recipient identity, channel, sent time.
- **Side Effects:** Awaits delivery confirmation.

#### EVT-NTF-003 · NotificationDelivered
- **Classification:** Domain · Business
- **Priority:** Low
- **Description:** A notification has been confirmed delivered.
- **Business Meaning:** The user was reached (feeds delivery-success KPI).
- **Trigger:** Delivery receipt received.
- **Business Objects:** Notification Delivery, Delivery Receipt, Notification.
- **Producer:** Notifications.
- **Consumers:** Analytics, Audit.
- **Preconditions:** Notification sent.
- **Business Rules References:** [NTF-001](DATA-002-business-rules-catalog.md#rule-ntf-001).
- **Payload:** notification identity, recipient identity, channel, delivered time.
- **Side Effects:** Delivery metrics updated.

#### EVT-NTF-004 · NotificationFailed
- **Classification:** Domain · Business
- **Priority:** Medium
- **Description:** A notification failed to deliver (e.g., bounce).
- **Business Meaning:** The user may not have been reached; may need an alternative channel.
- **Trigger:** Bounce/failure signal.
- **Business Objects:** Bounce Record, Notification Delivery, Notification.
- **Producer:** Notifications.
- **Consumers:** Analytics, Identity (contact quality), Audit.
- **Preconditions:** Notification sent.
- **Business Rules References:** [NTF-002](DATA-002-business-rules-catalog.md#rule-ntf-002).
- **Payload:** notification identity, recipient identity, channel, failure reason, failed time.
- **Side Effects:** Retry/alternative channel considered for critical notices.

---

### 4.11 Analytics (ANL)

---

#### EVT-ANL-001 · AnalyticsEventCaptured
- **Classification:** Domain
- **Priority:** Low
- **Description:** A derived analytics signal has been captured from a domain event.
- **Business Meaning:** Raw material for metrics and insight (privacy-minimized).
- **Trigger:** Consumption of a source domain event.
- **Business Objects:** Analytics Event.
- **Producer:** Analytics.
- **Consumers:** Analytics (aggregation), Audit.
- **Preconditions:** Source event received; data minimized/pseudonymized.
- **Business Rules References:** [ANL-001](DATA-002-business-rules-catalog.md#rule-anl-001), [ANL-002](DATA-002-business-rules-catalog.md#rule-anl-002).
- **Payload:** event type, occurred time, subject domain, pseudonymized subject reference, measured values.
- **Side Effects:** Rolled up into metrics.

#### EVT-ANL-002 · MetricComputed
- **Classification:** Domain · Business
- **Priority:** Low
- **Description:** A business metric/KPI snapshot has been computed.
- **Business Meaning:** Updates dashboards tracking business goals (BG-1…BG-8).
- **Trigger:** Scheduled or event-driven computation.
- **Business Objects:** KPI Snapshot, Metric Definition, Analytics Event.
- **Producer:** Analytics.
- **Consumers:** Dashboards/Reports (business stakeholders), Audit.
- **Preconditions:** Definition and period fixed.
- **Business Rules References:** [ANL-003](DATA-002-business-rules-catalog.md#rule-anl-003).
- **Payload:** metric reference, period, value, dimensions, computed time.
- **Side Effects:** Dashboards refreshed.

#### EVT-ANL-003 · DataExportGenerated
- **Classification:** Domain · Business · Audit
- **Priority:** Medium
- **Description:** A data export has been generated for a stakeholder.
- **Business Meaning:** Stakeholder receives a scoped, privacy-compliant extract.
- **Trigger:** Export request fulfilled.
- **Business Objects:** Data Export, User Account, Institution.
- **Producer:** Analytics.
- **Consumers:** Notifications, Audit.
- **Preconditions:** Requester scope and privacy verified.
- **Business Rules References:** [ANL-004](DATA-002-business-rules-catalog.md#rule-anl-004).
- **Payload:** export identity, requester identity, scope, generated time, expiry.
- **Side Effects:** Export delivered; access audited; expires per policy.

---

### 4.12 Audit (AUD)

---

#### EVT-AUD-001 · ActionRecorded
- **Classification:** Domain · Audit
- **Priority:** High
- **Description:** A significant action has been recorded immutably in the audit trail.
- **Business Meaning:** The backbone of fairness, security, and compliance evidence.
- **Trigger:** Any significant action across domains.
- **Business Objects:** Audit Log Entry, (any subject object).
- **Producer:** Audit.
- **Consumers:** Compliance/DPO, Security.
- **Preconditions:** A significant action occurred.
- **Business Rules References:** [AUD-001](DATA-002-business-rules-catalog.md#rule-aud-001), [AUD-002](DATA-002-business-rules-catalog.md#rule-aud-002).
- **Payload:** actor identity, action, subject object reference, occurred time, outcome, correlation reference.
- **Side Effects:** Immutable record retained per policy.

#### EVT-AUD-002 · DataSubjectRequestReceived
- **Classification:** Domain · Integration · Business · Audit
- **Priority:** Critical
- **Description:** A data-subject request (access/export/erasure) has been received.
- **Business Meaning:** Starts a legally time-bound obligation (152-ФЗ).
- **Trigger:** DSAR submitted.
- **Business Objects:** Data Subject Request, Participant, User Account.
- **Producer:** Audit.
- **Consumers:** Participants, Performances, Finance, Notifications.
- **Preconditions:** Requester identity to be verified.
- **Business Rules References:** [AUD-003](DATA-002-business-rules-catalog.md#rule-aud-003), [AUD-004](DATA-002-business-rules-catalog.md#rule-aud-004).
- **Payload:** request identity, subject reference, request type, received time, due date.
- **Side Effects:** Fulfilment workflow started; deadline tracked.

#### EVT-AUD-003 · DataErased
- **Classification:** Domain · Integration · Business · Audit
- **Priority:** Critical
- **Description:** Personal data has been erased per a request/retention policy.
- **Business Meaning:** Fulfils the right to erasure and evidences it.
- **Trigger:** Completion of an erasure cascade.
- **Business Objects:** Data Erasure Record, Participant, Retention Policy.
- **Producer:** Audit.
- **Consumers:** Compliance/DPO, Participants, Performances.
- **Preconditions:** No active legal hold; independent lawful bases respected.
- **Business Rules References:** [AUD-005](DATA-002-business-rules-catalog.md#rule-aud-005), [PRT-007](DATA-002-business-rules-catalog.md#rule-prt-007), [FIN-008](DATA-002-business-rules-catalog.md#rule-fin-008).
- **Payload:** erasure record identity, subject reference, scope erased, retained-under-lawful-basis notes, erased time.
- **Side Effects:** Data removed (incl. media/backups per policy); financial/audit records retained; requester informed.

#### EVT-AUD-004 · LegalHoldPlaced
- **Classification:** Domain · Integration · Audit
- **Priority:** Critical
- **Description:** A legal hold has been placed on specified objects.
- **Business Meaning:** Suspends erasure to meet preservation obligations.
- **Trigger:** Legal/compliance decision.
- **Business Objects:** Legal Hold, Retention Policy, (held objects).
- **Producer:** Audit.
- **Consumers:** Participants, Finance, Performances, all erasure paths.
- **Preconditions:** A preservation obligation exists.
- **Business Rules References:** [AUD-004](DATA-002-business-rules-catalog.md#rule-aud-004), [AUD-003](DATA-002-business-rules-catalog.md#rule-aud-003).
- **Payload:** hold identity, scope references, reason, placed time.
- **Side Effects:** Erasure suspended for held objects until lifted.

---

## 5. Event Dependency Graph

An event **depends on** an upstream event when the upstream fact must have occurred for the downstream event to be valid. (`A ⇐ B` reads "A depends on B".)

```
ParticipantActivated (PRT-004)      ⇐ ConsentGranted (IDN-003), GuardianLinked (PRT-002), EmailVerified (IDN-002)
ApplicationSubmitted (APP-001)      ⇐ ParticipantActivated (PRT-004), CompetitionOpened (CMP-004)
EligibilityChecked (APP-002)        ⇐ ApplicationSubmitted (APP-001)
PaymentCaptured (FIN-004)           ⇐ OrderCreated (FIN-001)   [paid competitions only]
ApplicationAccepted (APP-003)       ⇐ EligibilityChecked=pass (APP-002), PaymentCaptured (FIN-004 if paid)
PerformanceUploaded (PRF-001)       ⇐ ApplicationAccepted (APP-003)
MediaScanCompleted (PRF-002)        ⇐ PerformanceUploaded (PRF-001)
PerformanceModerationCleared(PRF-003)⇐ MediaScanCompleted=clean (PRF-002)
PerformanceAccepted (PRF-004)       ⇐ PerformanceModerationCleared (PRF-003)
SubmissionWindowClosed (CMP-005)    ⇐ CompetitionOpened (CMP-004)
JudgingStarted (CMP-006)            ⇐ SubmissionWindowClosed (CMP-005), CriteriaSetFrozen (CMP-002)
JudgeAssigned (JDG-002)             ⇐ JudgingStarted (CMP-006), PerformanceAccepted (PRF-004), JuryPanelFormed (JDG-001)
ScorecardSubmitted (JDG-005)        ⇐ JudgeAssigned (JDG-002)   [blocked by ConflictDeclared/JudgeRecused]
ScoringWindowClosed (JDG-006)       ⇐ JudgingStarted (CMP-006)
ScoreAggregated (JDG-007)           ⇐ ScoringWindowClosed (JDG-006), ScorecardSubmitted (JDG-005), JudgeRecused (JDG-004)
TieBreakDecided (JDG-008)           ⇐ ScoreAggregated (JDG-007)   [only on ties]
RankingFinalized (RES-001)          ⇐ ScoreAggregated (JDG-007), TieBreakDecided (JDG-008 if any)
ResultPublished (RES-002)           ⇐ RankingFinalized (RES-001), CompetitionResultsPhaseEntered (CMP-007)
DiplomaGenerated (RES-003)          ⇐ ResultPublished (RES-002)
PrizeAllocated (RES-004)            ⇐ RankingFinalized (RES-001)
DisputeResolved (RES-006)           ⇐ ResultDisputed (RES-005)
DataErased (AUD-003)                ⇐ DataSubjectRequestReceived (AUD-002)  [suspended by LegalHoldPlaced (AUD-004)]
```

> **Fan-out note:** almost every event above also fans out to `NotificationQueued → NotificationSent` (NTF) and `AnalyticsEventCaptured` (ANL), and the fairness/money/privacy events additionally produce `ActionRecorded` (AUD-001). These universal consumers are omitted from each line for readability.

---

## 6. Cross-Domain Event Flow

How events cross bounded contexts (each arrow = an integration event consumed by another domain). These realize the cross-domain invariants of [DATA-002 §7](DATA-002-business-rules-catalog.md#7-cross-domain-rules).

**Flow A — Consent-to-Participation (XDR-01)**
```
Identity: ConsentGranted ──▶ Participants: ParticipantActivated ──▶ Applications: ApplicationSubmitted
                                                                     (Consent Snapshot frozen at submit)
```

**Flow B — Payment-gated entitlement (XDR-04)**
```
Applications: ApplicationSubmitted ──▶ Finance: OrderCreated ──▶ Finance: PaymentCaptured
                                                                   └──▶ Applications: ApplicationAccepted
```

**Flow C — Safety-before-judging (XDR-05)**
```
Performances: PerformanceUploaded ──▶ MediaScanCompleted ──▶ PerformanceModerationCleared
        ──▶ PerformanceAccepted ──▶ Judging: JudgeAssigned
```

**Flow D — Fairness firewall & Judge-to-Result integrity (XDR-02, XDR-03)**
```
Judging: JuryPanelFormed ──▶ JudgeAssigned ──▶ ScorecardSubmitted ──▶ ScoreAggregated
        (ConflictDeclared/JudgeRecused prune invalid scores)          └──▶ Results: RankingFinalized ──▶ ResultPublished
```

**Flow E — Recognition & communication**
```
Results: ResultPublished ──▶ Results: DiplomaGenerated ──▶ Notifications: NotificationQueued/Sent/Delivered
        └──▶ Analytics: MetricComputed (participation, awards)
```

**Flow F — Erasure with lawful exceptions (XDR-06)**
```
Audit: DataSubjectRequestReceived ──▶ Participants: ParticipantErasureRequested
        ──▶ Performances (media), Finance (retain financial), Audit: DataErased
        (LegalHoldPlaced suspends the cascade)
```

**Flow G — Audit-everything (XDR-07)**
```
[Any fairness/money/privacy/access event] ──▶ Audit: ActionRecorded (immutable)
```

---

## 7. End-to-End Competition Event Timeline

A single competition, from creation to archive, in event order. (Universal fan-out to Notifications/Analytics/Audit implied at each milestone.)

| Phase | Event(s) | Domain | Priority |
|-------|----------|--------|----------|
| **Setup** | CompetitionCreated | CMP | Low |
| | CriteriaSetFrozen (per round, at scoring) | CMP | High |
| | CompetitionPublished | CMP | High |
| **Registration** | CompetitionOpened | CMP | High |
| | ConsentGranted → ParticipantActivated | IDN → PRT | Critical/High |
| | ApplicationSubmitted → EligibilityChecked | APP | High |
| | OrderCreated → PaymentCaptured *(if paid)* | FIN | Critical |
| | ApplicationAccepted | APP | High |
| **Submission** | PerformanceUploaded → MediaScanCompleted → PerformanceModerationCleared → PerformanceAccepted | PRF | Critical/High |
| | SubmissionWindowClosed | CMP | High |
| **Judging** | JuryPanelFormed → JudgeAssigned | JDG | High |
| | JudgingStarted | CMP | Critical |
| | (ConflictDeclared / JudgeRecused as needed) | JDG | Critical |
| | ScorecardSubmitted (many) | JDG | Critical |
| | ScoringWindowClosed | JDG | High |
| | ScoreAggregated → TieBreakDecided *(if ties)* | JDG | Critical/High |
| **Results** | CompetitionResultsPhaseEntered | CMP | High |
| | RankingFinalized → ResultPublished | RES | Critical |
| | DiplomaGenerated → PrizeAllocated | RES | High/Medium |
| | (ResultDisputed → DisputeResolved if raised) | RES | High |
| **Close** | CompetitionArchived | CMP | Low |
| **Any time** | DataSubjectRequestReceived → DataErased / LegalHoldPlaced | AUD | Critical |

---

## 8. Event Ownership Matrix

Each event has **exactly one producing (owning) domain**; consumers are other domains that react. This enforces single-writer ownership and event-by-identity integration (ARCH-001 §9.2).

| Owning Domain | Events Owned | Primary Consumers |
|---------------|--------------|-------------------|
| **Identity** | AccountRegistered, EmailVerified, ConsentGranted, ConsentWithdrawn, RoleAssigned, MfaEnrolled, TermsAccepted, AccountSuspended, AccountDeactivated | Participants, Applications, Notifications, Analytics, Audit |
| **Participants** | ParticipantCreated, GuardianLinked, ParticipantVerified, ParticipantActivated, ParticipantArchived, ParticipantErasureRequested | Applications, Performances, Finance, Analytics, Audit |
| **Institutions** | InstitutionRegistered, InstitutionVerified, TeacherAssigned, ClassGroupCreated, ParticipantJoinedInstitution | Participants, Analytics, Notifications, Audit |
| **Competitions** | CompetitionCreated, CriteriaSetFrozen, CompetitionPublished, CompetitionOpened, SubmissionWindowClosed, JudgingStarted, CompetitionResultsPhaseEntered, CompetitionArchived, CompetitionCancelled | Applications, Performances, Judging, Results, Finance, Notifications, Audit |
| **Applications** | ApplicationSubmitted, EligibilityChecked, ApplicationAccepted, ApplicationWaitlisted, ApplicationRejected, ApplicationWithdrawn | Competitions, Finance, Performances, Notifications, Analytics, Audit |
| **Performances** | PerformanceUploaded, MediaScanCompleted, PerformanceModerationCleared, PerformanceAccepted, PerformanceRejected, PerformanceVersionCreated | Judging, Notifications, Analytics, Audit |
| **Judging** | JuryPanelFormed, JudgeAssigned, ConflictDeclared, JudgeRecused, ScorecardSubmitted, ScoringWindowClosed, ScoreAggregated, TieBreakDecided | Results, Notifications, Analytics, Audit |
| **Results** | RankingFinalized, ResultPublished, DiplomaGenerated, PrizeAllocated, ResultDisputed, DisputeResolved | Notifications, Finance, Analytics, Audit |
| **Finance** | OrderCreated, DiscountApplied, InvoiceIssued, PaymentCaptured, PaymentFailed, RefundProcessed | Applications, Results, Notifications, Audit |
| **Notifications** | NotificationQueued, NotificationSent, NotificationDelivered, NotificationFailed | Analytics, Identity, Audit |
| **Analytics** | AnalyticsEventCaptured, MetricComputed, DataExportGenerated | Business stakeholders (dashboards), Notifications, Audit |
| **Audit** | ActionRecorded, DataSubjectRequestReceived, DataErased, LegalHoldPlaced | Compliance/DPO, Participants, Performances, Finance |

---

## 9. Event Versioning Policy

Events are a **published contract** between domains; changing them carelessly breaks consumers. This policy keeps events stable and evolvable (aligned with API versioning discipline in ARCH-001 §10.2 and additive-event guidance in DATA-001 §10.4).

### 9.1 Principles

- **Events are immutable facts.** A published event's *meaning* never changes. If the meaning changes, it is a **new event**, not a redefinition.
- **Names are stable.** An event name (and its ID) is permanent once released. Renaming = new event + deprecation of the old.
- **Additive change is safe.** New optional payload attributes may be added without a version bump, provided existing consumers keep working.
- **Breaking change requires a new version.** Removing/renaming a payload attribute, changing its meaning, or changing preconditions/semantics is breaking.

### 9.2 Versioning Scheme

- Events carry a **major version** suffix when a breaking change is unavoidable: `ScorecardSubmitted` → `ScorecardSubmitted.v2`.
- Both versions are **published in parallel** during a deprecation window; producers emit the new version and (where feasible) a compatibility shim for the old.
- Minor/additive evolution needs **no** version suffix; it is documented in the event's changelog entry.

### 9.3 Lifecycle & Deprecation

```
Proposed ─▶ Active ─▶ Deprecated ─▶ Retired
```

- **Deprecation window:** minimum **6 months** of parallel availability (mirrors ARCH-001 §10.2 API deprecation), with clear consumer communication.
- A **Retired** event keeps its ID reserved forever; the ID is never reused.
- Every version change is recorded in an event changelog and, where it alters a cross-domain contract, referenced from an ADR (ARCH-001 §30).

### 9.4 Governance

- The **owning domain** owns the event's schema and versioning decisions.
- Breaking changes require sign-off from all consuming domains before release.
- Payloads must remain **privacy-minimized**: no event may add a payload attribute that would re-identify a minor or leak cross-tenant data ([RULE-ANL-001](DATA-002-business-rules-catalog.md#rule-anl-001), [RULE-PRT-006](DATA-002-business-rules-catalog.md#rule-prt-006)).

---

## 10. Summary Statistics

### 10.1 Event Count by Domain

| Domain | Code | Events |
|--------|------|--------|
| Identity | IDN | 9 |
| Participants | PRT | 6 |
| Institutions | INS | 5 |
| Competitions | CMP | 9 |
| Applications | APP | 6 |
| Performances | PRF | 6 |
| Judging | JDG | 8 |
| Results | RES | 6 |
| Finance | FIN | 6 |
| Notifications | NTF | 4 |
| Analytics | ANL | 3 |
| Audit | AUD | 4 |
| **Total** | | **72** |

### 10.2 Distribution by Classification (events may carry multiple)

| Class | Character | Where concentrated |
|-------|-----------|--------------------|
| Domain Event | Every event (primary state fact) | All domains |
| Integration Event | Crosses context boundaries | CMP, APP, PRF, JDG, RES, FIN, IDN, AUD |
| Business Event | Stakeholder-visible milestones | CMP, APP, RES, FIN, ANL |
| Audit Event | Immutably recorded | IDN (consent), JDG (scoring), RES (publication), FIN (money), AUD, PRT (erasure) |

### 10.3 Distribution by Priority (indicative)

| Priority | Approx. count | Examples |
|----------|---------------|----------|
| Critical | 16 | ConsentGranted, JudgingStarted, ScorecardSubmitted, ScoreAggregated, ResultPublished, PaymentCaptured, DataErased |
| High | 30 | EmailVerified, ApplicationSubmitted, JudgeAssigned, RankingFinalized, RefundProcessed |
| Medium | 17 | AccountRegistered, ApplicationWaitlisted, InvoiceIssued, NotificationQueued |
| Low | 9 | ClassGroupCreated, CompetitionArchived, AnalyticsEventCaptured, NotificationDelivered |

---

*End of document — DATA-003 Domain Event Catalog v1.0. Business-language only; no broker technology, no implementation. Defers to [ARCH-001](../architecture/ARCH-001-vt-platform-architecture.md), [DATA-001](DATA-001-business-data-model.md), and [DATA-002](DATA-002-business-rules-catalog.md).*
