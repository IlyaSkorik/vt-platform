# DATA-002 — Business Rules Catalog v1.0

**Project:** «Взлёт талантов» — цифровая экосистема для организации детских творческих конкурсов
**Document type:** Business Rules Catalog (business language only)
**Status:** Draft for review (v1.0)
**Owner:** Domain Architecture Group
**Source of truth:** [ARCH-001 VT Platform Architecture v1.0](../architecture/ARCH-001-vt-platform-architecture.md) · [DATA-001 Business Data Model v1.0](DATA-001-business-data-model.md)
**Last updated:** 2026-07-05

> This document catalogues **all business rules** of the VT Platform in **business language only**. It contains **no** SQL, no Python, no REST, and no implementation detail. Rules reference the business objects defined in [DATA-001](DATA-001-business-data-model.md) and the principles in [ARCH-001](../architecture/ARCH-001-vt-platform-architecture.md). Where a rule realizes an architectural decision (e.g., ADR-0013 pseudonymized judging), it cites it. Technical designs must faithfully enforce these rules.

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [How to Read a Rule](#2-how-to-read-a-rule)
3. [Classification Model](#3-classification-model)
4. [Rules by Domain](#4-rules-by-domain)
   - [Identity (IDN)](#41-identity-idn)
   - [Participants (PRT)](#42-participants-prt)
   - [Institutions (INS)](#43-institutions-ins)
   - [Competitions (CMP)](#44-competitions-cmp)
   - [Applications (APP)](#45-applications-app)
   - [Performances (PRF)](#46-performances-prf)
   - [Judging (JDG)](#47-judging-jdg)
   - [Results (RES)](#48-results-res)
   - [Finance (FIN)](#49-finance-fin)
   - [Notifications (NTF)](#410-notifications-ntf)
   - [Analytics (ANL)](#411-analytics-anl)
   - [Audit (AUD)](#412-audit-aud)
5. [Rule Dependency Matrix](#5-rule-dependency-matrix)
6. [Conflict Matrix](#6-conflict-matrix)
7. [Cross-Domain Rules](#7-cross-domain-rules)
8. [Summary Statistics](#8-summary-statistics)

---

## 1. Purpose & Scope

### 1.1 Purpose

To provide a single, authoritative, unambiguous catalogue of every rule that governs the platform's behavior — the invariants, workflows, permissions, calculations, disclosures, and legal obligations that make «Взлёт талантов» **fair, private, and auditable** (ARCH-001 §1.5). This catalogue is the bridge between the *what* of [DATA-001](DATA-001-business-data-model.md) and the *how* of technical enforcement.

### 1.2 Scope

- **In scope:** business rules across all twelve domains; their triggers, preconditions, outcomes, exceptions, rationale, severity, and type; and the dependency, conflict, and cross-domain relationships between rules.
- **Out of scope:** implementation, storage, API, and UI. How a rule is *enforced* (validation layer, domain invariant, policy module) is a technical concern (ARCH-001 §7, §12); this document states *what must hold*.

### 1.3 Rule Identifier Scheme

```
RULE-<DOMAIN>-<NNN>
```

Domain codes: `IDN` Identity · `PRT` Participants · `INS` Institutions · `CMP` Competitions · `APP` Applications · `PRF` Performances · `JDG` Judging · `RES` Results · `FIN` Finance · `NTF` Notifications · `ANL` Analytics · `AUD` Audit. Numbers are zero-padded, sequential, and **immutable** once assigned (a retired rule keeps its number and is marked `Retired`).

---

## 2. How to Read a Rule

Every rule is specified with the following fields:

- **Rule ID** — stable identifier (§1.3).
- **Title** — one-line statement of the rule.
- **Type** — one or more of the six rule types (§3.2).
- **Severity** — Critical / High / Medium / Low (§3.1).
- **Description** — the rule in full business language.
- **Business Rationale** — *why* the rule exists (the business/regulatory reason).
- **Objects Involved** — the DATA-001 business objects the rule touches.
- **Trigger** — the business event or action that invokes the rule.
- **Preconditions** — what must already be true for the rule to apply.
- **Outcome** — what the rule causes (allow, block, compute, reveal, record).
- **Exceptions** — legitimate cases where the rule is relaxed or overridden.

---

## 3. Classification Model

### 3.1 Severity

| Severity | Meaning | Consequence of violation |
|----------|---------|--------------------------|
| **Critical** | Violates fairness, child safety, privacy, legal compliance, or financial integrity | Must hard-block; incident/audit; may be reportable |
| **High** | Breaks a core workflow or produces incorrect official output | Block the operation; require correction |
| **Medium** | Degrades correctness or experience but is recoverable | Warn/prevent; allow supervised override |
| **Low** | Cosmetic, advisory, or best-practice | Advise; non-blocking |

### 3.2 Rule Types

| Type | Definition |
|------|------------|
| **Validation Rule** | Constrains the shape/content/consistency of data at a point in time |
| **Workflow Rule** | Governs allowed state transitions, sequencing, and gating of processes |
| **Security Rule** | Governs authentication, authorization, scoping, and access |
| **Compliance Rule** | Enforces legal/regulatory obligations (152-ФЗ, consent, retention) |
| **Calculation Rule** | Defines how a derived value is computed |
| **Visibility Rule** | Governs what data is disclosed, to whom, and in what form |

A single rule may carry more than one type (e.g., a consent gate is both Compliance and Workflow).

---

## 4. Rules by Domain

### 4.1 Identity (IDN)

---

#### RULE-IDN-001
- **Title:** Email must be verified before sensitive actions.
- **Type:** Security · Workflow
- **Severity:** High
- **Description:** A User Account may not perform sensitive actions (granting consent, submitting applications, scoring, publishing results, making payments) until its contact email is verified.
- **Business Rationale:** Establishes a trustworthy communication and recovery channel and deters throwaway accounts (ARCH-001 §11.2).
- **Objects Involved:** User Account, Email Verification.
- **Trigger:** Attempt to perform a sensitive action.
- **Preconditions:** Account exists; email not yet verified.
- **Outcome:** The action is blocked until verification completes.
- **Exceptions:** Purely read-only or profile-completion actions are permitted pre-verification.

#### RULE-IDN-002
- **Title:** Privileged roles require multi-factor authentication.
- **Type:** Security · Compliance
- **Severity:** Critical
- **Description:** Accounts holding Administrator, Organizer, or Jury roles must have an active Multi-Factor Enrollment before exercising those roles.
- **Business Rationale:** These roles can affect fairness, money, and personal data; MFA is mandated (ARCH-001 §11.3).
- **Objects Involved:** User Account, Role Assignment, Multi-Factor Enrollment.
- **Trigger:** Activation/first privileged use of the role.
- **Preconditions:** Role assigned; MFA not enrolled.
- **Outcome:** Privileged capabilities are withheld until MFA is enrolled.
- **Exceptions:** None. Break-glass administrator access follows a separate, audited emergency procedure.

#### RULE-IDN-003
- **Title:** One verified email maps to at most one active account.
- **Type:** Validation · Security
- **Severity:** High
- **Description:** A verified email address may be associated with only one Active User Account at a time.
- **Business Rationale:** Prevents duplicate identities and account confusion (DATA-001 §4.1).
- **Objects Involved:** User Account, Email Verification, Email (value object).
- **Trigger:** Account registration or email change.
- **Preconditions:** Another active account already holds the verified email.
- **Outcome:** Registration/change is rejected.
- **Exceptions:** Deactivated/erased accounts free the email for reuse.

#### RULE-IDN-004
- **Title:** Children do not hold independent accounts.
- **Type:** Compliance · Security
- **Severity:** Critical
- **Description:** A minor (Participant) may not authenticate as an independent User Account; they are represented in the Participants domain and acted for by a verified Guardian or authorized Teacher.
- **Business Rationale:** Child-safety and privacy posture for minors (ARCH-001 §11.4, §21.6).
- **Objects Involved:** User Account, Participant, Guardian, Teacher.
- **Trigger:** Account creation.
- **Preconditions:** Registrant is below the platform's independent-account age.
- **Outcome:** No independent account is created; a guardian/teacher-managed Participant is used instead.
- **Exceptions:** None in v1.0.

#### RULE-IDN-005
- **Title:** Consent is purpose-limited and versioned.
- **Type:** Compliance · Validation
- **Severity:** Critical
- **Description:** Each Consent authorizes exactly one declared purpose and records the exact consent-text version in force; separate purposes require separate consents.
- **Business Rationale:** Purpose limitation and evidentiary integrity under 152-ФЗ (ARCH-001 §21.6).
- **Objects Involved:** Consent, Consent Type, ConsentGrant (value object).
- **Trigger:** Consent request/grant.
- **Preconditions:** A purpose and current consent-text version exist.
- **Outcome:** Consent is recorded against a single purpose and text version.
- **Exceptions:** None.

#### RULE-IDN-006
- **Title:** Consent withdrawal must be honored and cascade.
- **Type:** Compliance · Workflow
- **Severity:** Critical
- **Description:** When a Guardian withdraws a Consent, dependent processing tied to that purpose must stop and cascade per the Retention Policy.
- **Business Rationale:** Data-subject rights; privacy by design (ARCH-001 §21.6, §3.2).
- **Objects Involved:** Consent, Retention Policy, Participant, Application, Performance.
- **Trigger:** Consent withdrawal.
- **Preconditions:** Active consent exists; dependent records may exist.
- **Outcome:** Processing halts; downstream data enters the erasure/retention workflow.
- **Exceptions:** Data under a Legal Hold or with an independent lawful basis (e.g., financial records) is retained per policy (see [RULE-AUD-004](#rule-aud-004)).

#### RULE-IDN-007
- **Title:** Deactivation preserves audit history.
- **Type:** Compliance
- **Severity:** High
- **Description:** Deactivating a User Account must not delete its audit trail; erasure follows the DSAR/retention workflow separately.
- **Business Rationale:** Auditability and non-repudiation (ARCH-001 §21.7).
- **Objects Involved:** User Account, Audit Log Entry, Data Subject Request.
- **Trigger:** Account deactivation.
- **Preconditions:** Account is Active/Suspended.
- **Outcome:** Account set inactive; audit records retained.
- **Exceptions:** None.

#### RULE-IDN-008
- **Title:** Role grants cannot exceed the granter's scope.
- **Type:** Security
- **Severity:** Critical
- **Description:** A Role Assignment's scope may not exceed the scope of authority of the account granting it.
- **Business Rationale:** Prevents privilege escalation; least privilege (ARCH-001 §12.4).
- **Objects Involved:** Role, Role Assignment, User Account.
- **Trigger:** Granting a role.
- **Preconditions:** Granter has a bounded scope.
- **Outcome:** Out-of-scope grants are rejected.
- **Exceptions:** Platform Administrators operate at global scope by definition.

#### RULE-IDN-009
- **Title:** Repeated failed logins trigger lockout/backoff.
- **Type:** Security
- **Severity:** High
- **Description:** After a threshold of failed Login Attempts, the account/IP is temporarily locked or throttled.
- **Business Rationale:** Credential-stuffing and brute-force mitigation (ARCH-001 §11.2, §21.3).
- **Objects Involved:** User Account, Login Attempt.
- **Trigger:** Consecutive failed authentications.
- **Preconditions:** Failure count exceeds threshold within a window.
- **Outcome:** Further attempts are backed off; user notified of unusual activity.
- **Exceptions:** Verified recovery flow (Account Recovery Request) may lift lockout.

#### RULE-IDN-010
- **Title:** Terms acceptance is required and versioned.
- **Type:** Compliance · Workflow
- **Severity:** Medium
- **Description:** A user must accept the current platform Terms version before first use; a materially new version requires re-acceptance.
- **Business Rationale:** Contractual clarity and consent to platform use.
- **Objects Involved:** Terms Acceptance, User Account.
- **Trigger:** First login / new terms version published.
- **Preconditions:** Current terms version differs from last accepted.
- **Outcome:** Access gated until acceptance recorded.
- **Exceptions:** Read of legally required notices is always permitted.

---

### 4.2 Participants (PRT)

---

#### RULE-PRT-001
- **Title:** A participant requires verified guardianship or institutional authority before becoming Active.
- **Type:** Compliance · Workflow
- **Severity:** Critical
- **Description:** A Participant may not transition to Active without at least one Active Guardian Relationship **or** an authorized Institution/Teacher link with recorded consent.
- **Business Rationale:** No minor participates without a responsible, verified adult (ARCH-001 §11.4).
- **Objects Involved:** Participant, Guardian Relationship, Teacher, Institution, Consent.
- **Trigger:** Participant activation.
- **Preconditions:** Participant is in Created/Verified state.
- **Outcome:** Activation blocked until guardianship/authority + consent exist.
- **Exceptions:** None.

#### RULE-PRT-002
- **Title:** Age group is always derived, never entered.
- **Type:** Calculation · Validation
- **Severity:** High
- **Description:** A Participant's AgeGroup for a competition is computed from date of birth relative to the competition's reference date; it may not be entered by hand.
- **Business Rationale:** Fair, tamper-resistant cohorting (DATA-001 §4.2, §8).
- **Objects Involved:** Participant, AgeGroup (value object), Competition, Application.
- **Trigger:** Application creation / cohort assignment.
- **Preconditions:** Valid date of birth and competition reference date exist.
- **Outcome:** Age group is computed and bound to the application.
- **Exceptions:** Organizer-defined special categories (e.g., «смешанная группа») explicitly documented per competition.

#### RULE-PRT-003
- **Title:** Guardians manage only their linked participants.
- **Type:** Security · Visibility
- **Severity:** Critical
- **Description:** A Guardian may view/manage only Participants to whom a verified Guardian Relationship exists.
- **Business Rationale:** Data minimization and child privacy (ARCH-001 §12.5, §21.6).
- **Objects Involved:** Guardian, Guardian Relationship, Participant.
- **Trigger:** Any participant access by a guardian.
- **Preconditions:** Relationship state evaluated.
- **Outcome:** Access limited to linked participants; others not even enumerable.
- **Exceptions:** None.

#### RULE-PRT-004
- **Title:** Teachers act only within assigned institution and classes.
- **Type:** Security
- **Severity:** High
- **Description:** A Teacher may manage participants only within their Institution and assigned Class Groups.
- **Business Rationale:** Tenancy scoping (ARCH-001 §12.5).
- **Objects Involved:** Teacher, Teacher Assignment, Class Group, Participant.
- **Trigger:** Teacher action on a participant.
- **Preconditions:** Assignment scope evaluated.
- **Outcome:** Out-of-scope actions rejected.
- **Exceptions:** None.

#### RULE-PRT-005
- **Title:** Teacher-initiated participation still requires guardian consent.
- **Type:** Compliance
- **Severity:** Critical
- **Description:** Even when a Teacher enters a Participant, a valid Guardian Consent for that minor and purpose must exist.
- **Business Rationale:** Institutional authority does not replace parental consent (ARCH-001 §11.4).
- **Objects Involved:** Teacher, Participant, Consent, Application.
- **Trigger:** Teacher creates/submits an application.
- **Preconditions:** No active matching consent.
- **Outcome:** Submission blocked pending consent.
- **Exceptions:** None.

#### RULE-PRT-006
- **Title:** Participant personal identity is minimized and access-restricted.
- **Type:** Visibility · Compliance
- **Severity:** Critical
- **Description:** A Participant's real identity is visible only to the linked guardian, assigned teacher, and authorized organizers; only minimally necessary data is collected.
- **Business Rationale:** Data minimization and access minimization for minors (ARCH-001 §21.6).
- **Objects Involved:** Participant, Participant Profile, Guardian, Teacher, Organizer Assignment.
- **Trigger:** Any read of participant identity.
- **Preconditions:** Viewer role/scope evaluated.
- **Outcome:** Unauthorized viewers see nothing; jury sees pseudonymized alias (see [RULE-JDG-006](#rule-jdg-006)).
- **Exceptions:** Lawful compliance/audit access by the DPO.

#### RULE-PRT-007
- **Title:** Participant erasure cascades per retention policy.
- **Type:** Compliance · Workflow
- **Severity:** Critical
- **Description:** Erasing a Participant cascades to their performances, media, and derived data per the Retention Policy and DSAR obligations.
- **Business Rationale:** Right to erasure; complete removal (ARCH-001 §3.2, §21.6).
- **Objects Involved:** Participant, Performance, Media Asset, Retention Policy, Data Erasure Record.
- **Trigger:** Approved erasure request.
- **Preconditions:** No Legal Hold; DSAR verified.
- **Outcome:** Data erased and an erasure record produced.
- **Exceptions:** Financial/audit records retained under independent lawful basis.

#### RULE-PRT-008
- **Title:** A participant may not be double-linked under conflicting guardianship without review.
- **Type:** Validation
- **Severity:** Medium
- **Description:** Conflicting or duplicate Guardian Relationships for the same Participant require review before both become Active.
- **Business Rationale:** Prevents disputed custody data errors.
- **Objects Involved:** Participant, Guardian Relationship.
- **Trigger:** Second guardian link proposed.
- **Preconditions:** An active relationship already exists.
- **Outcome:** New link enters verification/review.
- **Exceptions:** Two-parent households are normal and auto-approved when non-conflicting.

---

### 4.3 Institutions (INS)

---

#### RULE-INS-001
- **Title:** Only verified institutions access bulk workflows and analytics.
- **Type:** Security · Workflow
- **Severity:** High
- **Description:** Bulk onboarding and institutional analytics are available only to Institutions in the Verified/Active state.
- **Business Rationale:** Trust and abuse-prevention for scaled access (ARCH-001 §12.5, BG-5).
- **Objects Involved:** Institution, Institution Verification, Institution Administrator.
- **Trigger:** Access to bulk/analytics features.
- **Preconditions:** Verification state evaluated.
- **Outcome:** Unverified institutions are limited to basic features.
- **Exceptions:** None.

#### RULE-INS-002
- **Title:** Institution scope bounds administrator and teacher access.
- **Type:** Security · Visibility
- **Severity:** Critical
- **Description:** Institution Administrators and Teachers may access only data belonging to their Institution (tenancy boundary).
- **Business Rationale:** Prevent cross-tenant leakage (ARCH-001 §12.5).
- **Objects Involved:** Institution, Institution Administrator, Teacher, Class Group, Participant.
- **Trigger:** Any institutional data access.
- **Preconditions:** Membership/scope evaluated.
- **Outcome:** Cross-institution access denied and non-enumerable.
- **Exceptions:** Platform Administrators; DPO for compliance.

#### RULE-INS-003
- **Title:** Delegation stays within the institution and is audited.
- **Type:** Security · Compliance
- **Severity:** High
- **Description:** An Institution Administrator may grant Teacher Assignments only within their own institution, and every delegation is recorded.
- **Business Rationale:** Least privilege and accountability (ARCH-001 §12.4, §21.7).
- **Objects Involved:** Institution Administrator, Teacher Assignment, Audit Log Entry.
- **Trigger:** Teacher Assignment grant.
- **Preconditions:** Target teacher/class within institution.
- **Outcome:** Assignment created and audited; out-of-scope rejected.
- **Exceptions:** None.

#### RULE-INS-004
- **Title:** A class group belongs to exactly one institution.
- **Type:** Validation
- **Severity:** Medium
- **Description:** A Class Group must belong to one and only one Institution; membership in it implies institutional membership.
- **Business Rationale:** Clear ownership and consistent scoping (DATA-001 §4.3).
- **Objects Involved:** Class Group, Institution, Participant Group Membership.
- **Trigger:** Class group creation / participant addition.
- **Preconditions:** Institution reference set.
- **Outcome:** Single-institution ownership enforced.
- **Exceptions:** None.

#### RULE-INS-005
- **Title:** Institution verification requires validated evidence.
- **Type:** Compliance · Validation
- **Severity:** High
- **Description:** An Institution reaches Verified only after its legitimacy evidence is validated.
- **Business Rationale:** Prevents impersonation of schools/organizations.
- **Objects Involved:** Institution, Institution Verification, Institution Contact.
- **Trigger:** Verification review.
- **Preconditions:** Evidence submitted.
- **Outcome:** Verified or Rejected with reasons.
- **Exceptions:** None.

---

### 4.4 Competitions (CMP)

---

#### RULE-CMP-001
- **Title:** Competition status transitions are strictly ordered and time-gated.
- **Type:** Workflow
- **Severity:** Critical
- **Description:** A Competition progresses Draft → Published → Open → Submission → Judging → Results → Archived; it cannot skip states or move backward except via a governed correction, and cannot enter Judging before the submission window closes.
- **Business Rationale:** Predictable, fair process integrity (ARCH-001 §2.1; DATA-001 §4.4).
- **Objects Involved:** Competition, Round, Competition Schedule, Competition Status History.
- **Trigger:** Status change request.
- **Preconditions:** Current state and schedule evaluated.
- **Outcome:** Only valid, time-permitted transitions succeed; each is recorded.
- **Exceptions:** Cancellation is an allowed terminal transition from most states.

#### RULE-CMP-002
- **Title:** A publishable competition must be structurally complete.
- **Type:** Validation · Workflow
- **Severity:** High
- **Description:** A Competition may be Published only if it has at least one Nomination, at least one Age Group, and a valid Criteria Set for each nomination/round.
- **Business Rationale:** Prevents empty/unjudgeable competitions.
- **Objects Involved:** Competition, Nomination, Age Group, Criteria Set, Judging Criterion.
- **Trigger:** Publish action.
- **Preconditions:** Structure evaluated.
- **Outcome:** Publish blocked until complete.
- **Exceptions:** None.

#### RULE-CMP-003
- **Title:** Schedule dates must be logically consistent.
- **Type:** Validation
- **Severity:** High
- **Description:** Competition key dates must satisfy open ≤ close ≤ judging-start ≤ results.
- **Business Rationale:** Coherent timeline; avoids impossible windows (DATA-001 §4.4).
- **Objects Involved:** Competition, Competition Schedule, DateRange (value object), Round.
- **Trigger:** Schedule creation/update.
- **Preconditions:** Dates provided.
- **Outcome:** Inconsistent schedules rejected.
- **Exceptions:** Multi-round competitions nest round windows within the overall schedule.

#### RULE-CMP-004
- **Title:** Criterion weights within a criteria set sum to the defined whole.
- **Type:** Validation · Calculation
- **Severity:** High
- **Description:** The Weights of all Judging Criteria in a Criteria Set must sum to the defined whole (e.g., 100%).
- **Business Rationale:** Correct, comparable scoring math (DATA-001 §4.4, §8).
- **Objects Involved:** Criteria Set, Judging Criterion, Weight (value object).
- **Trigger:** Criteria set publish.
- **Preconditions:** All criteria and weights defined.
- **Outcome:** Publish blocked if weights do not sum correctly.
- **Exceptions:** Explicitly unweighted (equal-weight) sets are normalized automatically.

#### RULE-CMP-005
- **Title:** Competition structure freezes once judging starts.
- **Type:** Workflow
- **Severity:** Critical
- **Description:** Nominations, age groups, rounds, and criteria sets become immutable when a round enters scoring; changes thereafter require a governed correction.
- **Business Rationale:** No moving the goalposts mid-judging; fairness (BG-3; ARCH-001 §13.4).
- **Objects Involved:** Competition, Round, Criteria Set, Nomination.
- **Trigger:** Round enters Scoring.
- **Preconditions:** Scoring window opened.
- **Outcome:** Structural edits blocked.
- **Exceptions:** Governed correction with audit and stakeholder notice.

#### RULE-CMP-006
- **Title:** Published competition structure is immutable after results.
- **Type:** Workflow · Compliance
- **Severity:** Critical
- **Description:** After Results are published, the competition's structure is immutable except through the documented correction process.
- **Business Rationale:** Integrity of official outcomes (DATA-001 §4.4).
- **Objects Involved:** Competition, Result, Competition Status History.
- **Trigger:** Post-results edit attempt.
- **Preconditions:** Results published.
- **Outcome:** Edits blocked; corrections audited.
- **Exceptions:** Dispute-driven corrections (see [RULE-RES-007](#rule-res-007)).

#### RULE-CMP-007
- **Title:** Prize allocations cannot exceed prize quantity.
- **Type:** Validation · Calculation
- **Severity:** High
- **Description:** The number of Prize Allocations for a Prize may not exceed its defined quantity.
- **Business Rationale:** Cannot award more than exists (DATA-001 §4.4).
- **Objects Involved:** Prize, Prize Tier, Prize Allocation.
- **Trigger:** Prize allocation.
- **Preconditions:** Remaining quantity evaluated.
- **Outcome:** Over-allocation rejected.
- **Exceptions:** Organizer may increase quantity before results are published.

#### RULE-CMP-008
- **Title:** Only assigned organizers may configure a competition.
- **Type:** Security
- **Severity:** High
- **Description:** Configuration and lifecycle control of a Competition are limited to accounts with an Organizer Assignment for it.
- **Business Rationale:** Ownership and least privilege (ARCH-001 §12.2).
- **Objects Involved:** Competition, Organizer Assignment, User Account.
- **Trigger:** Any competition configuration action.
- **Preconditions:** Organizer scope evaluated.
- **Outcome:** Unauthorized configuration rejected.
- **Exceptions:** Platform Administrators for governance/moderation.

---

### 4.5 Applications (APP)

---

#### RULE-APP-001
- **Title:** No application submission without active matching consent.
- **Type:** Compliance · Workflow
- **Severity:** Critical
- **Description:** An Application cannot be submitted unless an active Consent matching the participation purpose exists and is captured as a Consent Snapshot.
- **Business Rationale:** Lawful basis for processing a minor's participation (ARCH-001 §11.4, §21.6).
- **Objects Involved:** Application, Consent, Consent Snapshot, Participant.
- **Trigger:** Application submit.
- **Preconditions:** Consent state evaluated.
- **Outcome:** Submission blocked absent valid consent; snapshot captured on success.
- **Exceptions:** None.

#### RULE-APP-002
- **Title:** Application must pass the eligibility check to be accepted.
- **Type:** Validation · Workflow
- **Severity:** Critical
- **Description:** An Application may reach Accepted only after passing the Eligibility Check against the competition's Eligibility Rules (age group, institution, entry limits).
- **Business Rationale:** Only valid entries compete (DATA-001 §4.5).
- **Objects Involved:** Application, Eligibility Check, Eligibility Rule, Age Group.
- **Trigger:** Acceptance evaluation.
- **Preconditions:** Eligibility evaluated.
- **Outcome:** Failing entries blocked with reasons surfaced.
- **Exceptions:** Organizer may grant a documented waiver for a specific rule.

#### RULE-APP-003
- **Title:** Paid competitions gate acceptance on payment.
- **Type:** Workflow · Calculation
- **Severity:** High
- **Description:** Where a Competition is paid, an Application is Accepted only when its associated Order is Paid (or the fee is waived).
- **Business Rationale:** Revenue integrity for paid competitions (BG-6).
- **Objects Involved:** Application, Application Fee, Order, Payment.
- **Trigger:** Acceptance evaluation.
- **Preconditions:** Fee assessed; order state evaluated.
- **Outcome:** Acceptance withheld until payment/ waiver.
- **Exceptions:** Fee waiver or discount reducing total to zero.

#### RULE-APP-004
- **Title:** Per-participant entry limits are enforced.
- **Type:** Validation
- **Severity:** Medium
- **Description:** A Participant may not exceed the competition-defined number of Applications per nomination/competition.
- **Business Rationale:** Fair access; prevents flooding.
- **Objects Involved:** Application, Participant, Competition, Nomination, Eligibility Rule.
- **Trigger:** Application create.
- **Preconditions:** Existing entry count evaluated.
- **Outcome:** Excess entries blocked.
- **Exceptions:** Organizer-defined multi-entry nominations.

#### RULE-APP-005
- **Title:** Withdrawal is allowed until the defined cutoff and is audited.
- **Type:** Workflow · Compliance
- **Severity:** Medium
- **Description:** An Application may be withdrawn until the competition's withdrawal cutoff; the withdrawal is recorded.
- **Business Rationale:** Participant autonomy with process integrity (DATA-001 §4.5).
- **Objects Involved:** Application, Application Withdrawal, Competition Schedule, Audit Log Entry.
- **Trigger:** Withdrawal request.
- **Preconditions:** Before cutoff; application not already judged.
- **Outcome:** Application withdrawn; downstream performances voided; refund policy applied.
- **Exceptions:** After cutoff, withdrawal requires organizer approval.

#### RULE-APP-006
- **Title:** Consent snapshot is immutable once captured.
- **Type:** Compliance · Validation
- **Severity:** Critical
- **Description:** The Consent Snapshot bound to an Application is never modified after capture.
- **Business Rationale:** Evidentiary proof of the consent that authorized the entry (DATA-001 §4.5).
- **Objects Involved:** Consent Snapshot, Application, Consent.
- **Trigger:** Any edit attempt on a snapshot.
- **Preconditions:** Snapshot exists.
- **Outcome:** Edits rejected.
- **Exceptions:** None.

#### RULE-APP-007
- **Title:** Waitlist promotion respects capacity and order.
- **Type:** Workflow · Calculation
- **Severity:** Low
- **Description:** When capacity frees up, Waitlist Entries are promoted in recorded order.
- **Business Rationale:** Fair, transparent queueing.
- **Objects Involved:** Waitlist Entry, Application, Competition.
- **Trigger:** Capacity becomes available.
- **Preconditions:** Waitlist non-empty; capacity > current accepted.
- **Outcome:** Next entry promoted to Accepted (subject to consent/payment gates).
- **Exceptions:** Organizer may close a waitlist.

---

### 4.6 Performances (PRF)

---

#### RULE-PRF-001
- **Title:** A performance cannot enter judging until scanned clean and moderation-cleared.
- **Type:** Security · Workflow · Compliance
- **Severity:** Critical
- **Description:** A Performance may be presented to judging only after its media pass Antivirus Scan (clean) and Content Moderation (cleared).
- **Business Rationale:** Child safety, platform safety, and content integrity (ARCH-001 §21.3).
- **Objects Involved:** Performance, Media Asset, Antivirus Scan Result, Content Moderation Flag.
- **Trigger:** Performance readiness for judging.
- **Preconditions:** Scan and moderation states evaluated.
- **Outcome:** Unsafe/uncleared performances withheld from judging.
- **Exceptions:** None.

#### RULE-PRF-002
- **Title:** Infected or quarantined media is never exposed.
- **Type:** Security
- **Severity:** Critical
- **Description:** A Media Asset failing the Antivirus Scan is quarantined and never served or shown.
- **Business Rationale:** Prevents malware distribution (ARCH-001 §21.3).
- **Objects Involved:** Media Asset, Antivirus Scan Result.
- **Trigger:** Scan result = infected.
- **Preconditions:** Asset uploaded.
- **Outcome:** Asset quarantined; submitter notified to replace.
- **Exceptions:** None.

#### RULE-PRF-003
- **Title:** Media must satisfy the nomination's requirements.
- **Type:** Validation
- **Severity:** High
- **Description:** A Media Asset's type and size must meet the target Nomination's media requirements.
- **Business Rationale:** Comparable, judgeable submissions (DATA-001 §4.6).
- **Objects Involved:** Media Asset, FileMetadata (value object), Nomination, Performance.
- **Trigger:** Media upload/attach.
- **Preconditions:** Nomination requirements known.
- **Outcome:** Non-conforming media rejected.
- **Exceptions:** Organizer-configured tolerances.

#### RULE-PRF-004
- **Title:** Media bytes are stored externally; only references are held.
- **Type:** Validation
- **Severity:** Medium
- **Description:** The Performance holds media references and metadata only; binary content lives in external object storage.
- **Business Rationale:** Scale, durability, and clean domain modeling (ARCH-001 §9.6).
- **Objects Involved:** Performance, Media Asset, Media Metadata.
- **Trigger:** Media registration.
- **Outcome:** Only references/metadata recorded in the domain.
- **Preconditions:** Upload target available.
- **Exceptions:** None.

#### RULE-PRF-005
- **Title:** The scored version is fixed when the round opens.
- **Type:** Workflow
- **Severity:** High
- **Description:** Re-submission before the deadline creates a new Performance Version; the version judged is the one current when the round opens.
- **Business Rationale:** Determinism and fairness in what is judged (DATA-001 §4.6).
- **Objects Involved:** Performance, Performance Version, Round.
- **Trigger:** Round opens for scoring.
- **Preconditions:** One or more versions exist.
- **Outcome:** The active version is frozen for judging.
- **Exceptions:** Governed correction if a defect is proven.

#### RULE-PRF-006
- **Title:** Upheld high-severity moderation blocks judging and results.
- **Type:** Compliance · Workflow
- **Severity:** Critical
- **Description:** A Content Moderation Flag upheld at high severity removes the Performance from judging and any results.
- **Business Rationale:** No inappropriate content in a children's platform (ARCH-001 §21.3).
- **Objects Involved:** Content Moderation Flag, Performance, Result.
- **Trigger:** Moderation flag upheld (high).
- **Preconditions:** Flag reviewed.
- **Outcome:** Performance excluded; participant/guardian notified.
- **Exceptions:** Overturn on appeal restores eligibility if time permits.

---

### 4.7 Judging (JDG)

---

#### RULE-JDG-001
- **Title:** A judge cannot evaluate their own student.
- **Type:** Security · Compliance
- **Severity:** Critical
- **Description:** A Jury Member who is (or is linked as) the Teacher of a Participant may not be assigned to, or score, that participant's Performance.
- **Business Rationale:** Eliminates the most direct conflict of interest; core fairness (BG-3).
- **Objects Involved:** Jury Member, Teacher, Participant, Performance, Judge Assignment, Conflict of Interest Declaration.
- **Trigger:** Judge Assignment.
- **Preconditions:** Teacher–participant relationship detected for the candidate judge.
- **Outcome:** Assignment must be rejected (and any existing score voided via recusal).
- **Exceptions:** None.

#### RULE-JDG-002
- **Title:** Judges may score only performances they are assigned.
- **Type:** Security
- **Severity:** Critical
- **Description:** A Jury Member may submit scores only for Performances covered by an active Judge Assignment to them in the current round.
- **Business Rationale:** Scoping and integrity (ARCH-001 §12.1).
- **Objects Involved:** Jury Member, Judge Assignment, Performance, Scorecard.
- **Trigger:** Score submission.
- **Preconditions:** Assignment scope evaluated.
- **Outcome:** Out-of-scope scoring rejected.
- **Exceptions:** None.

#### RULE-JDG-003
- **Title:** No scoring before the round opens or after it closes.
- **Type:** Workflow
- **Severity:** Critical
- **Description:** A Scorecard may be submitted only within the Round's open Scoring Window.
- **Business Rationale:** Determinism and fairness; domain invariant (ARCH-001 §13.4).
- **Objects Involved:** Round, Scoring Window, Scorecard, Performance.
- **Trigger:** Score submission.
- **Preconditions:** Window state evaluated.
- **Outcome:** Early/late submissions rejected.
- **Exceptions:** Organizer-approved window extension (audited) before results.

#### RULE-JDG-004
- **Title:** A scorecard is valid only if the full rubric is scored.
- **Type:** Validation
- **Severity:** High
- **Description:** A Scorecard is valid only when every Judging Criterion in the frozen Criteria Set has a Criterion Score.
- **Business Rationale:** Complete, comparable evaluations (DATA-001 §4.7).
- **Objects Involved:** Scorecard, Criterion Score, Criteria Set, Judging Criterion.
- **Trigger:** Scorecard submit.
- **Preconditions:** Criteria set frozen.
- **Outcome:** Incomplete scorecards rejected.
- **Exceptions:** None.

#### RULE-JDG-005
- **Title:** Each criterion score lies within its defined scale.
- **Type:** Validation
- **Severity:** High
- **Description:** A Criterion Score's value must fall within the ScoreValue scale of its criterion.
- **Business Rationale:** Meaningful, bounded scoring (DATA-001 §8).
- **Objects Involved:** Criterion Score, Judging Criterion, ScoreValue (value object).
- **Trigger:** Score entry.
- **Preconditions:** Scale known.
- **Outcome:** Out-of-range values rejected.
- **Exceptions:** None.

#### RULE-JDG-006
- **Title:** Judges see performances pseudonymized.
- **Type:** Visibility · Compliance
- **Severity:** Critical
- **Description:** Jury Members see a Performance without the Participant's real identity (display alias only).
- **Business Rationale:** Fairness and minor privacy (ARCH-001 §21.6; ADR-0013).
- **Objects Involved:** Jury Member, Performance, Participant.
- **Trigger:** Judge views assigned performance.
- **Preconditions:** Judging context.
- **Outcome:** Identity withheld; alias shown.
- **Exceptions:** Live performance formats where in-person identity is unavoidable are governed by explicit competition rules and consent.

#### RULE-JDG-007
- **Title:** Conflicts of interest must be declared before scoring.
- **Type:** Compliance · Workflow
- **Severity:** Critical
- **Description:** A Jury Member must file any Conflict of Interest Declaration before scoring; accepted conflicts prevent assignment/scoring of the affected work.
- **Business Rationale:** Transparent fairness (BG-3).
- **Objects Involved:** Jury Member, Conflict of Interest Declaration, Recusal, Judge Assignment.
- **Trigger:** Onboarding to a panel / before scoring.
- **Preconditions:** Potential conflict exists.
- **Outcome:** Conflicted assignments blocked; recusal recorded.
- **Exceptions:** None.

#### RULE-JDG-008
- **Title:** Submitted scorecards lock and become immutable.
- **Type:** Workflow · Compliance
- **Severity:** Critical
- **Description:** Once Submitted within a closed window, a Scorecard is Locked and immutable; corrections require a governed, audited process.
- **Business Rationale:** Non-repudiation and auditability of scoring (ARCH-001 §3.2, §21.7).
- **Objects Involved:** Scorecard, Criterion Score, Audit Log Entry.
- **Trigger:** Scorecard submit / window close.
- **Preconditions:** Submitted.
- **Outcome:** Locked; edits require correction workflow.
- **Exceptions:** Governed correction with audit trail.

#### RULE-JDG-009
- **Title:** Only valid, non-recused, locked scorecards contribute to aggregation.
- **Type:** Calculation
- **Severity:** Critical
- **Description:** Score Aggregation includes only Scorecards that are valid, from non-recused judges, and locked.
- **Business Rationale:** Correct, defensible results (BG-3).
- **Objects Involved:** Score Aggregation, Scorecard, Recusal.
- **Trigger:** Aggregation computation.
- **Preconditions:** Scorecards finalized.
- **Outcome:** Invalid/recused scores excluded; method recorded.
- **Exceptions:** None.

#### RULE-JDG-010
- **Title:** Ties are resolved by a recorded tie-break decision before finalization.
- **Type:** Calculation · Workflow
- **Severity:** High
- **Description:** Equal aggregated scores affecting ranking/awards must be resolved by a documented Tie-Break Decision before a Ranking is finalized.
- **Business Rationale:** Deterministic, transparent ordering.
- **Objects Involved:** Score Aggregation, Tie-Break Decision, Ranking.
- **Trigger:** Tie detected during ranking.
- **Preconditions:** Tie affects an award/cut line.
- **Outcome:** Tie resolved and recorded; ranking finalized.
- **Exceptions:** Competition rules may permit shared placements.

#### RULE-JDG-011
- **Title:** Recusal voids the affected scores.
- **Type:** Compliance · Calculation
- **Severity:** Critical
- **Description:** When a Jury Member is recused for a Performance, their Scores for it are void and excluded from aggregation.
- **Business Rationale:** Remove tainted evaluations (BG-3).
- **Objects Involved:** Recusal, Jury Member, Scorecard, Score Aggregation.
- **Trigger:** Recusal effective.
- **Preconditions:** Scores may already exist.
- **Outcome:** Affected scores voided; aggregation recomputed.
- **Exceptions:** None.

---

### 4.8 Results (RES)

---

#### RULE-RES-001
- **Title:** Results are published only after judging is finalized.
- **Type:** Workflow
- **Severity:** Critical
- **Description:** A Result may be Published only after Score Aggregation for its round is finalized and ranking complete.
- **Business Rationale:** No premature or partial official outcomes (DATA-001 §4.8).
- **Objects Involved:** Result, Score Aggregation, Ranking, Result Publication.
- **Trigger:** Publish action.
- **Preconditions:** Judging finalized.
- **Outcome:** Publication proceeds; otherwise blocked.
- **Exceptions:** None.

#### RULE-RES-002
- **Title:** Published results are immutable except by governed correction.
- **Type:** Workflow · Compliance
- **Severity:** Critical
- **Description:** After publication, Results cannot change except through the documented Dispute Resolution/correction process, which is audited.
- **Business Rationale:** Trust in official outcomes (ARCH-001 §21.7).
- **Objects Involved:** Result, Result Snapshot, Dispute Resolution, Audit Log Entry.
- **Trigger:** Post-publication change attempt.
- **Preconditions:** Result published.
- **Outcome:** Direct edits blocked; corrections routed through the process.
- **Exceptions:** Upheld disputes (see [RULE-RES-007](#rule-res-007)).

#### RULE-RES-003
- **Title:** Ranking derives strictly from aggregation and tie-breaks.
- **Type:** Calculation
- **Severity:** High
- **Description:** A Ranking's order derives solely from finalized Score Aggregations and recorded Tie-Break Decisions.
- **Business Rationale:** Objective, reproducible standings (BG-3).
- **Objects Involved:** Ranking, Ranking Entry, Score Aggregation, Tie-Break Decision.
- **Trigger:** Ranking finalization.
- **Preconditions:** Aggregations final.
- **Outcome:** Deterministic ordering produced.
- **Exceptions:** None.

#### RULE-RES-004
- **Title:** A diploma is issued only for a published result.
- **Type:** Workflow · Validation
- **Severity:** High
- **Description:** A Diploma or Certificate is generated only for a Result in Published state.
- **Business Rationale:** No recognition without a valid outcome (DATA-001 §4.8).
- **Objects Involved:** Diploma, Certificate, Result.
- **Trigger:** Diploma generation.
- **Preconditions:** Result published.
- **Outcome:** Artifact generated; otherwise blocked.
- **Exceptions:** Participation certificates may be issued to all eligible participants per competition policy.

#### RULE-RES-005
- **Title:** Every diploma carries a unique verification code.
- **Type:** Validation · Security
- **Severity:** High
- **Description:** Each Diploma/Certificate must carry a globally unique, non-guessable VerificationCode.
- **Business Rationale:** Authenticity and anti-forgery (DATA-001 §8, §9.4).
- **Objects Involved:** Diploma, Certificate, VerificationCode (value object).
- **Trigger:** Diploma generation.
- **Preconditions:** Result published.
- **Outcome:** Unique code assigned and recorded.
- **Exceptions:** None.

#### RULE-RES-006
- **Title:** Result visibility respects participant privacy.
- **Type:** Visibility · Compliance
- **Severity:** High
- **Description:** Publicly displayed results/leaderboards respect participant privacy: real identity is shown only to authorized viewers; public views use permitted display forms.
- **Business Rationale:** Minor privacy (ARCH-001 §21.6).
- **Objects Involved:** Result, Leaderboard, Participant, Consent.
- **Trigger:** Result/leaderboard display.
- **Preconditions:** Viewer scope and consent-to-display evaluated.
- **Outcome:** Identity disclosed only where authorized/consented.
- **Exceptions:** Guardians may consent to public recognition of their child.

#### RULE-RES-007
- **Title:** An upheld dispute triggers governed correction and possible reissue.
- **Type:** Workflow · Compliance
- **Severity:** Critical
- **Description:** When a Result Dispute is upheld, a governed correction updates the Result and, if needed, revokes and reissues the Diploma.
- **Business Rationale:** Fair remediation with integrity (BG-3).
- **Objects Involved:** Result Dispute, Dispute Resolution, Result, Diploma, Audit Log Entry.
- **Trigger:** Dispute upheld.
- **Preconditions:** Dispute reviewed.
- **Outcome:** Result corrected; artifacts reissued; all audited.
- **Exceptions:** None.

#### RULE-RES-008
- **Title:** Prize allocation follows finalized ranking.
- **Type:** Calculation · Workflow
- **Severity:** Medium
- **Description:** Prize Allocations are derived from the finalized Ranking and Prize Tier definitions.
- **Business Rationale:** Consistent reward assignment.
- **Objects Involved:** Prize Allocation, Ranking, Prize, Prize Tier.
- **Trigger:** Post-ranking allocation.
- **Preconditions:** Ranking final; prizes defined.
- **Outcome:** Allocations produced within quantity limits (see [RULE-CMP-007](#rule-cmp-007)).
- **Exceptions:** Sponsor-specific special prizes per competition rules.

---

### 4.9 Finance (FIN)

---

#### RULE-FIN-001
- **Title:** Money is always precise; never approximate.
- **Type:** Calculation · Validation
- **Severity:** Critical
- **Description:** All monetary amounts use the Money value object (exact minor units + currency); floating-point money is prohibited.
- **Business Rationale:** Financial correctness (ARCH-001 §9.4).
- **Objects Involved:** Money (value object), Order, Invoice, Payment, Fee, Refund.
- **Trigger:** Any monetary computation/storage.
- **Preconditions:** Amount and currency defined.
- **Outcome:** Exact arithmetic; rounding rules explicit.
- **Exceptions:** None.

#### RULE-FIN-002
- **Title:** Monetary arithmetic occurs only within one currency.
- **Type:** Validation · Calculation
- **Severity:** High
- **Description:** Amounts of different currencies may not be added/compared without an explicit, recorded conversion.
- **Business Rationale:** Prevents silent currency errors (DATA-001 §8).
- **Objects Involved:** Money (value object), Order, Invoice Line Item.
- **Trigger:** Monetary operation.
- **Preconditions:** Currencies compared.
- **Outcome:** Mixed-currency operations rejected without conversion.
- **Exceptions:** Documented conversion with recorded rate.

#### RULE-FIN-003
- **Title:** Order total equals line items less discounts, single currency.
- **Type:** Calculation
- **Severity:** High
- **Description:** An Order's total is the sum of its Invoice Line Items minus applied discounts, expressed in one currency.
- **Business Rationale:** Correct, auditable billing (DATA-001 §4.9).
- **Objects Involved:** Order, Invoice Line Item, Coupon Redemption, Discount Code, Money.
- **Trigger:** Order calculation.
- **Preconditions:** Line items and discounts known.
- **Outcome:** Deterministic total computed.
- **Exceptions:** Taxes added per applicable Tax Rate.

#### RULE-FIN-004
- **Title:** A refund cannot exceed the captured amount.
- **Type:** Validation · Calculation
- **Severity:** Critical
- **Description:** The total of Refunds against a Payment may not exceed the amount captured.
- **Business Rationale:** Prevents over-refunding / financial loss (DATA-001 §4.9).
- **Objects Involved:** Refund, Payment, Payment Transaction, Money.
- **Trigger:** Refund request.
- **Preconditions:** Captured amount and prior refunds evaluated.
- **Outcome:** Over-refunds rejected.
- **Exceptions:** Goodwill credits are separate instruments, not refunds.

#### RULE-FIN-005
- **Title:** An issued invoice is immutable; correct by void + reissue.
- **Type:** Compliance · Workflow
- **Severity:** High
- **Description:** Once Issued, an Invoice cannot be edited; corrections are made by voiding and reissuing.
- **Business Rationale:** Financial record integrity and auditability.
- **Objects Involved:** Invoice, Invoice Line Item, Receipt.
- **Trigger:** Post-issue edit attempt.
- **Preconditions:** Invoice issued.
- **Outcome:** Edits blocked; void/reissue path used.
- **Exceptions:** None.

#### RULE-FIN-006
- **Title:** Every payment state change is audited.
- **Type:** Compliance · Security
- **Severity:** High
- **Description:** All Payment and Refund state changes produce audit records.
- **Business Rationale:** Traceability and dispute defense (ARCH-001 §21.7).
- **Objects Involved:** Payment, Refund, Audit Log Entry.
- **Trigger:** Payment/refund transition.
- **Preconditions:** Transition occurs.
- **Outcome:** Audit entry recorded.
- **Exceptions:** None.

#### RULE-FIN-007
- **Title:** Discount codes are validated before application.
- **Type:** Validation
- **Severity:** Medium
- **Description:** A Discount Code must be active, within its limits, and applicable to the order before a Coupon Redemption is recorded.
- **Business Rationale:** Prevents invalid/expired discounts and abuse.
- **Objects Involved:** Discount Code, Coupon Redemption, Order.
- **Trigger:** Applying a code.
- **Preconditions:** Code state and applicability evaluated.
- **Outcome:** Invalid codes rejected; valid ones reduce total.
- **Exceptions:** Stackable-code policy where explicitly allowed.

#### RULE-FIN-008
- **Title:** Financial records are retained under an independent lawful basis.
- **Type:** Compliance
- **Severity:** High
- **Description:** Payment/invoice records are retained per financial-record obligations even when related personal data is erased; personal identifiers are minimized where possible.
- **Business Rationale:** Legal retention duties coexisting with privacy (ARCH-001 §21.6).
- **Objects Involved:** Invoice, Payment, Retention Policy, Data Erasure Record.
- **Trigger:** Participant erasure affecting a payer.
- **Preconditions:** Financial retention period active.
- **Outcome:** Financial records retained; linked personal data minimized.
- **Exceptions:** After the financial retention period, records are purged.

---

### 4.10 Notifications (NTF)

---

#### RULE-NTF-001
- **Title:** Notifications respect recipient preferences and consent.
- **Type:** Compliance · Visibility
- **Severity:** High
- **Description:** A Notification is sent on a channel only if the recipient has not opted out (per Notification Preference) and any required consent exists.
- **Business Rationale:** Respectful, lawful communication (ARCH-001 §2.1, §21.6).
- **Objects Involved:** Notification, Notification Preference, Notification Channel, Subscription Preference.
- **Trigger:** Notification dispatch.
- **Preconditions:** Preferences evaluated.
- **Outcome:** Opted-out channels skipped.
- **Exceptions:** Critical transactional notices per [RULE-NTF-002](#rule-ntf-002).

#### RULE-NTF-002
- **Title:** Critical transactional notices are exempt from marketing opt-out.
- **Type:** Compliance · Workflow
- **Severity:** Medium
- **Description:** Essential notices (security alerts, consent changes, result publication, payment receipts) are delivered regardless of marketing opt-out.
- **Business Rationale:** Users must receive information material to their rights and safety.
- **Objects Involved:** Notification, Notification Topic, Notification Preference.
- **Trigger:** Critical event.
- **Preconditions:** Notice classified critical.
- **Outcome:** Delivered on an available essential channel.
- **Exceptions:** Full account closure ends all delivery.

#### RULE-NTF-003
- **Title:** A template must exist in the primary locale before use.
- **Type:** Validation
- **Severity:** Medium
- **Description:** A Notification Template must exist in ru-RU (primary locale) before it can be used to send.
- **Business Rationale:** Guaranteed baseline localization (ARCH-001 §8.6).
- **Objects Involved:** Notification Template, Locale (value object).
- **Trigger:** Template publish/use.
- **Preconditions:** Locale coverage evaluated.
- **Outcome:** Use blocked until primary-locale version exists.
- **Exceptions:** None.

#### RULE-NTF-004
- **Title:** Deadline and result notices are prioritized over promotional messages.
- **Type:** Workflow
- **Severity:** Low
- **Description:** Time-sensitive notices (deadlines, results) take dispatch priority over promotional content.
- **Business Rationale:** Users must not miss critical timing.
- **Objects Involved:** Notification, Notification Topic, Reminder.
- **Trigger:** Concurrent dispatch.
- **Preconditions:** Mixed-priority queue.
- **Outcome:** Higher-priority notices sent first.
- **Exceptions:** None.

#### RULE-NTF-005
- **Title:** Notifications never expose sensitive personal data of minors.
- **Type:** Compliance · Visibility · Security
- **Severity:** Critical
- **Description:** Message content must not include sensitive personal data of a minor beyond what the recipient is authorized to see.
- **Business Rationale:** Privacy by design; logs/messages redact PII (ARCH-001 §19.1, §21.6).
- **Objects Involved:** Notification, Message, Participant.
- **Trigger:** Message composition.
- **Preconditions:** Recipient authorization evaluated.
- **Outcome:** Sensitive data omitted/redacted.
- **Exceptions:** Guardians receive their own child's information.

---

### 4.11 Analytics (ANL)

---

#### RULE-ANL-001
- **Title:** Analytics never re-identifies minors.
- **Type:** Compliance · Visibility
- **Severity:** Critical
- **Description:** Analytics data is minimized and pseudonymized so that it cannot re-identify a Participant.
- **Business Rationale:** Privacy by design for derived data (ARCH-001 §21.6).
- **Objects Involved:** Analytics Event, KPI Snapshot, Participant.
- **Trigger:** Analytics capture/aggregation.
- **Preconditions:** Event derived from source.
- **Outcome:** Only pseudonymized/minimized data retained.
- **Exceptions:** None.

#### RULE-ANL-002
- **Title:** Analytics is read-only and never mutates source data.
- **Type:** Security · Workflow
- **Severity:** High
- **Description:** The Analytics domain derives from domain events and must not modify source-of-truth business objects.
- **Business Rationale:** Integrity of authoritative data (ARCH-001 §20.3, DATA-001 §7).
- **Objects Involved:** Analytics Event, Aggregate View, (any source object).
- **Trigger:** Analytics processing.
- **Preconditions:** Events consumed.
- **Outcome:** Derived views produced; sources untouched.
- **Exceptions:** None.

#### RULE-ANL-003
- **Title:** KPI snapshots are reproducible from their inputs.
- **Type:** Calculation
- **Severity:** Medium
- **Description:** A KPI Snapshot must be reproducible from its Metric Definition, period, and source events.
- **Business Rationale:** Trustworthy, auditable metrics.
- **Objects Involved:** KPI Snapshot, Metric Definition, Analytics Event.
- **Trigger:** KPI computation.
- **Preconditions:** Definition and period fixed.
- **Outcome:** Deterministic value produced.
- **Exceptions:** None.

#### RULE-ANL-004
- **Title:** Data exports honor scope and privacy.
- **Type:** Security · Compliance · Visibility
- **Severity:** High
- **Description:** A Data Export contains only data the requester is authorized to receive and respects minor-privacy rules.
- **Business Rationale:** Prevents leakage via exports (ARCH-001 §12, §21.6).
- **Objects Involved:** Data Export, User Account, Institution, Participant.
- **Trigger:** Export request.
- **Preconditions:** Requester scope evaluated.
- **Outcome:** Scoped, privacy-compliant export produced.
- **Exceptions:** DPO compliance exports under lawful basis.

---

### 4.12 Audit (AUD)

---

#### RULE-AUD-001
- **Title:** Significant actions are recorded immutably.
- **Type:** Compliance · Security
- **Severity:** Critical
- **Description:** Authentication, authorization decisions, scoring, result publication, consent changes, and personal-data operations must produce append-only Audit Log Entries.
- **Business Rationale:** Fairness, non-repudiation, and legal defensibility (ARCH-001 §21.7).
- **Objects Involved:** Audit Log Entry, (any subject object).
- **Trigger:** Any significant action.
- **Preconditions:** Action occurs.
- **Outcome:** Immutable audit entry recorded within the action's boundary.
- **Exceptions:** None.

#### RULE-AUD-002
- **Title:** Audit records are never updated or deleted outside policy.
- **Type:** Compliance
- **Severity:** Critical
- **Description:** Audit Log Entries are append-only; they may be purged only when the Retention Policy permits.
- **Business Rationale:** Tamper-evidence and compliance (ARCH-001 §21.7).
- **Objects Involved:** Audit Log Entry, Retention Policy.
- **Trigger:** Any modification/deletion attempt.
- **Preconditions:** Entry exists.
- **Outcome:** Mutations blocked; policy-based purge only.
- **Exceptions:** Court-ordered actions under governed procedure.

#### RULE-AUD-003
- **Title:** Data-subject requests are fulfilled within regulatory timelines.
- **Type:** Compliance · Workflow
- **Severity:** Critical
- **Description:** A Data Subject Request (access, export, erasure) must be verified and fulfilled within the legal timeline, cascading to media and backups per policy.
- **Business Rationale:** 152-ФЗ data-subject rights (ARCH-001 §3.2, §21.6).
- **Objects Involved:** Data Subject Request, Data Erasure Record, Retention Policy, Participant.
- **Trigger:** DSAR received.
- **Preconditions:** Requester identity verified.
- **Outcome:** Request fulfilled and evidenced within deadline.
- **Exceptions:** Legal Hold suspends erasure (see [RULE-AUD-004](#rule-aud-004)).

#### RULE-AUD-004
- **Title:** A legal hold suspends erasure.
- **Type:** Compliance
- **Severity:** Critical
- **Description:** While a Legal Hold is active on objects, erasure (including DSAR-driven) is suspended for those objects until the hold is lifted.
- **Business Rationale:** Legal preservation obligations override routine erasure.
- **Objects Involved:** Legal Hold, Data Subject Request, Retention Policy, (held objects).
- **Trigger:** Erasure attempt on held objects.
- **Preconditions:** Active hold exists.
- **Outcome:** Erasure deferred; requester informed of lawful delay.
- **Exceptions:** None.

#### RULE-AUD-005
- **Title:** Retention periods govern all terminal lifecycle states.
- **Type:** Compliance
- **Severity:** High
- **Description:** Each data class is retained for its defined period, then erased by the defined method; terminal states across domains follow the Retention Policy.
- **Business Rationale:** Storage limitation and purpose limitation (ARCH-001 §21.6).
- **Objects Involved:** Retention Policy, (all domains), Data Erasure Record.
- **Trigger:** Retention period elapses.
- **Preconditions:** No Legal Hold; independent lawful basis absent.
- **Outcome:** Data erased per method; erasure recorded.
- **Exceptions:** Independent lawful bases (e.g., finance, see [RULE-FIN-008](#rule-fin-008)).

---

## 5. Rule Dependency Matrix

A rule **depends on** another when the depended-upon rule must hold first for it to be meaningful or enforceable. (`A → B` reads "A depends on B".)

| Rule | Depends on | Nature of dependency |
|------|------------|----------------------|
| RULE-IDN-002 | RULE-IDN-001 | MFA presumes a verified, usable account |
| RULE-PRT-001 | RULE-IDN-004, RULE-IDN-005 | Guardianship/consent presume the identity & consent model |
| RULE-PRT-005 | RULE-IDN-005, RULE-PRT-001 | Teacher entry still needs valid guardian consent |
| RULE-APP-001 | RULE-IDN-005, RULE-PRT-001 | Application consent gate needs consent + active participant |
| RULE-APP-002 | RULE-PRT-002, RULE-CMP-002 | Eligibility needs derived age group + defined competition structure |
| RULE-APP-003 | RULE-FIN-001, RULE-FIN-003 | Payment gate needs correct order totals |
| RULE-PRF-001 | RULE-PRF-002, RULE-PRF-006 | Judging readiness needs clean scan + moderation clearance |
| RULE-JDG-001 | RULE-JDG-007 | Own-student block realized via COI/recusal machinery |
| RULE-JDG-002 | RULE-CMP-008 | Assignment scoping presumes valid organizer configuration |
| RULE-JDG-003 | RULE-CMP-001, RULE-CMP-005 | Scoring window depends on lifecycle + frozen structure |
| RULE-JDG-004 | RULE-CMP-004, RULE-CMP-005 | Full-rubric scoring needs a valid, frozen criteria set |
| RULE-JDG-009 | RULE-JDG-004, RULE-JDG-008, RULE-JDG-011 | Aggregation consumes only valid, locked, non-recused scores |
| RULE-JDG-010 | RULE-JDG-009 | Tie-break operates on aggregated results |
| RULE-RES-001 | RULE-JDG-009, RULE-JDG-010, RULE-RES-003 | Publication needs finalized aggregation and ranking |
| RULE-RES-004 | RULE-RES-001 | Diploma needs a published result |
| RULE-RES-005 | RULE-RES-004 | Verification code issued with the diploma |
| RULE-RES-007 | RULE-RES-002, RULE-AUD-001 | Correction runs through the governed, audited path |
| RULE-RES-008 | RULE-RES-003, RULE-CMP-007 | Allocation follows ranking within quantity limits |
| RULE-FIN-004 | RULE-FIN-001 | Refund limit needs precise money |
| RULE-NTF-001 | RULE-NTF-002 | Preference filter yields to critical-notice exemption |
| RULE-PRT-007 | RULE-AUD-003, RULE-AUD-004, RULE-FIN-008 | Erasure cascade obeys DSAR, holds, and financial retention |
| RULE-AUD-003 | RULE-AUD-004 | DSAR fulfillment yields to active legal holds |
| RULE-ANL-001 | RULE-PRT-006 | Analytics privacy builds on participant access-minimization |

---

## 6. Conflict Matrix

Rules that pull in opposite directions, and the **governing resolution** (which rule wins, and why). These are intentional tensions resolved by explicit precedence — not defects.

| Rule A | Rule B | Tension | Resolution (precedence) |
|--------|--------|---------|--------------------------|
| RULE-IDN-006 (Consent withdrawal cascades erasure) | RULE-FIN-008 (Retain financial records) | Withdraw-and-erase vs. legal retention | **FIN-008 wins** for financial records only; personal identifiers minimized; non-financial data still erased |
| RULE-AUD-003 (DSAR erasure timeline) | RULE-AUD-004 (Legal hold suspends erasure) | Erase vs. preserve | **AUD-004 wins**; erasure resumes when hold lifts; requester informed of lawful delay |
| RULE-PRT-007 (Participant erasure cascades) | RULE-AUD-002 (Audit immutable) | Erase everything vs. keep audit trail | **AUD-002 wins** for audit entries; audit is minimized but retained per policy |
| RULE-JDG-006 (Pseudonymized to jury) | RULE-RES-006 (Results may show identity) | Hide identity vs. public recognition | Phase-scoped: **JDG-006 wins during judging**; **RES-006 governs post-publication**, and only with guardian consent to display |
| RULE-NTF-001 (Respect opt-out) | RULE-NTF-002 (Critical notices exempt) | Silence vs. must-inform | **NTF-002 wins** for essential/transactional notices; marketing remains opt-out |
| RULE-APP-005 (Withdrawal before cutoff) | RULE-CMP-005 (Structure/scoring freeze) | Late withdrawal vs. locked judging | **CMP-005 wins** once scoring starts; post-cutoff withdrawal needs organizer approval |
| RULE-PRF-006 (Uphold blocks results) | RULE-RES-002 (Results immutable) | Remove content vs. immutable results | **PRF-006 wins** pre-publication; post-publication routes through governed correction (RES-007) |
| RULE-CMP-007 (Allocation ≤ quantity) | RULE-RES-008 (Allocation follows ranking) | Ranking demands vs. scarce prizes | **CMP-007 wins**; ties/overflow resolved by tie-break (JDG-010) or organizer quantity increase before publication |

---

## 7. Cross-Domain Rules

Rules whose enforcement spans multiple domains. These are the platform's **integration invariants** — realized across bounded contexts via domain events and interfaces (ARCH-001 §4.8, §7.4), never by one domain reaching into another.

| Rule | Domains spanned | Cross-domain invariant |
|------|-----------------|------------------------|
| **XDR-01 — Consent-to-Participation chain** (IDN-005, PRT-001, APP-001, APP-006) | Identity → Participants → Applications | No minor is entered anywhere without an active, purpose-matched consent, snapshotted immutably at entry |
| **XDR-02 — Fairness firewall** (JDG-001, JDG-006, JDG-007, JDG-011, PRT-004) | Participants → Judging | A judge never scores their own student and never sees participant identity; conflicts force recusal that voids scores |
| **XDR-03 — Judge-to-Result integrity** (JDG-003, JDG-004, JDG-008, JDG-009, RES-001, RES-003) | Judging → Results | Only complete, in-window, locked, non-recused scores flow into finalized rankings and published results |
| **XDR-04 — Payment-gated entitlement** (FIN-001, FIN-003, APP-003, RES-004) | Finance → Applications → Results | Paid entitlements (acceptance, some artifacts) are granted only when money is correctly settled |
| **XDR-05 — Safety-before-judging** (PRF-001, PRF-002, PRF-006, JDG-002) | Performances → Judging | No unsafe or uncleared media is ever assigned or scored |
| **XDR-06 — Erasure with lawful exceptions** (IDN-006, PRT-007, AUD-003, AUD-004, AUD-005, FIN-008) | Identity → Participants → Audit → Finance | Erasure requests cascade platform-wide, except where legal holds or independent lawful bases require retention |
| **XDR-07 — Audit-everything** (AUD-001, AUD-002; realized by JDG-008, FIN-006, RES-002, INS-003) | Audit ↔ all domains | Every fairness-, money-, access-, or privacy-significant action is immutably recorded |
| **XDR-08 — Privacy of derived data** (PRT-006, ANL-001, ANL-004, NTF-005, RES-006) | Participants → Analytics → Notifications → Results | A minor's identity is never re-exposed through analytics, exports, notifications, or public results without authorization/consent |
| **XDR-09 — Tenancy isolation** (INS-002, PRT-003, PRT-004, ANL-004) | Institutions → Participants → Analytics | Institutional and guardian scopes bound every read/write and export; no cross-tenant leakage |
| **XDR-10 — Structural freeze integrity** (CMP-005, CMP-006, PRF-005, JDG-003) | Competitions → Performances → Judging | Once scoring begins, what is judged and how it is judged cannot change outside a governed, audited correction |

---

## 8. Summary Statistics

### 8.1 Rule Count by Domain

| Domain | Code | Rules |
|--------|------|-------|
| Identity | IDN | 10 |
| Participants | PRT | 8 |
| Institutions | INS | 5 |
| Competitions | CMP | 8 |
| Applications | APP | 7 |
| Performances | PRF | 6 |
| Judging | JDG | 11 |
| Results | RES | 8 |
| Finance | FIN | 8 |
| Notifications | NTF | 5 |
| Analytics | ANL | 4 |
| Audit | AUD | 5 |
| **Total** | | **85** |

Plus **10 cross-domain rules** (XDR-01 … XDR-10) composed from the above.

### 8.2 Distribution by Severity (indicative)

| Severity | Approx. count | Character |
|----------|---------------|-----------|
| Critical | 33 | Fairness, child safety, privacy, compliance, financial integrity |
| High | 33 | Core workflow / official-output correctness |
| Medium | 14 | Recoverable correctness/experience |
| Low | 5 | Advisory / prioritization |

### 8.3 Distribution by Type (rules may carry multiple types)

| Type | Where it dominates |
|------|--------------------|
| Validation | Data consistency across all domains (esp. CMP, APP, PRF, FIN) |
| Workflow | Lifecycle gating (CMP, APP, JDG, RES) |
| Security | Access & scoping (IDN, INS, PRT, JDG) |
| Compliance | Consent, privacy, retention, audit (IDN, PRT, AUD, FIN) |
| Calculation | Scoring & money (JDG, RES, FIN) |
| Visibility | Disclosure & pseudonymization (PRT, JDG, RES, ANL, NTF) |

---

*End of document — DATA-002 Business Rules Catalog v1.0. Business-language only; all enforcement defers to the architecture in [ARCH-001](../architecture/ARCH-001-vt-platform-architecture.md) and the objects in [DATA-001](DATA-001-business-data-model.md).*
