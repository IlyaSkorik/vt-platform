# DATA-001 — Business Data Model v1.0

**Project:** «Взлёт талантов» — цифровая экосистема для организации детских творческих фестивалей
**Document type:** Business Domain & Data Model (business language only)
**Status:** Draft for review (v1.0)
**Owner:** Enterprise Data Architecture Group
**Source of truth:** [ARCH-001 VT Platform Architecture v1.0](../architecture/ARCH-001-vt-platform-architecture.md)
**Last updated:** 2026-07-05

> This document describes the **business domain** only. It contains **no** SQL, no PostgreSQL schema, no Django models, no REST contracts, and no implementation detail. It is the conceptual, business-language reference that technical designs (data schema, API, code) must faithfully realize. Where terms overlap with [ARCH-001 §13 (DDD)](../architecture/ARCH-001-vt-platform-architecture.md#13-domain-driven-design), this document is the more detailed elaboration and defers to ARCH-001 for architectural decisions.

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [Domain Overview](#3-domain-overview)
4. [Business Objects — Detailed Specifications](#4-business-objects--detailed-specifications)
5. [Business Object Catalog](#5-business-object-catalog)
6. [Relationship Matrix](#6-relationship-matrix)
7. [Aggregate Roots](#7-aggregate-roots)
8. [Value Objects](#8-value-objects)
9. [Entity Identity Strategy](#9-entity-identity-strategy)
10. [Naming Standards](#10-naming-standards)

---

## 1. Purpose

The purpose of this document is to establish the **shared, authoritative business vocabulary and conceptual data model** for the VT Platform. It exists to:

- Define **what** information the business cares about, independent of how it is stored or served.
- Provide a single, unambiguous **ubiquitous language** (per ARCH-001 §13.1) that product, engineering, judging operations, finance, and compliance all share.
- Identify the **business objects**, their **lifecycles**, **ownership**, **relationships**, and **business rules** so that downstream technical artifacts (database schema, APIs, code) can be derived correctly and consistently.
- Make explicit the **aggregate boundaries** and **value objects** that give the model integrity and that map to the bounded contexts of the modular monolith.
- Encode the platform's non-negotiable concerns — **fairness of judging**, **privacy of minors**, and **auditability** — directly into the data model's rules.

This model is the contract between the *business* and the *system*. When the business changes, this document changes first.

---

## 2. Scope

### 2.1 In Scope

- All **business domains** required to run children's creative competitions end to end, from identity and registration through judging, results, finance, communication, analytics, and audit.
- For each domain: its **description, responsibilities, business owner, and business objects**.
- For each significant business object: **purpose, description, domain, lifecycle, business owner, main (business-level) attributes, relationships, and business rules**.
- The **business object catalog** (grouped by domain), **relationship matrix**, **aggregate roots**, **value objects**, **entity identity strategy**, and **naming standards**.

### 2.2 Out of Scope

- Physical data storage, table design, indexing, partitioning (see ARCH-001 §9).
- Programming-language models, ORM entities, serializers.
- API endpoints, payload shapes, transport concerns (see ARCH-001 §10).
- Infrastructure, security mechanisms, and deployment (see ARCH-001 §16–§29).
- Concrete attribute data types, sizes, or nullability — only **business-level** attributes are named here.

### 2.3 Modeling Conventions

- **Business object** = a concept the business needs to remember and reason about (an entity or a meaningful record).
- **Aggregate root** = the object that owns a consistency boundary; other objects inside the aggregate are accessed through it.
- **Value object** = a concept defined by its attributes, not by an identity (e.g., `Money`, `AgeGroup`).
- **Detailed specification** (§4) is provided for **core objects and aggregate roots**; the **complete enumeration** of all 100–150 objects (with purpose, aggregate flag, and lifecycle summary) lives in the **Business Object Catalog** (§5). This is a deliberate documentation convention: exhaustive prose cards for every supporting record would obscure the model; the catalog guarantees full coverage while the cards give depth where it matters.
- **Domain names** used here align with the requested business decomposition; their mapping to ARCH-001 bounded contexts is given in §3.1.

---

## 3. Domain Overview

### 3.1 Domain Map & Alignment to Architecture

The business is decomposed into **twelve domains**. The table maps each to the ARCH-001 bounded context that will host it.

| # | Business Domain | ARCH-001 Bounded Context | Type | Business Owner |
|---|-----------------|--------------------------|------|----------------|
| 1 | **Identity** | Identity & Access | Supporting | Identity & Trust Product Owner |
| 2 | **Participants** | Participants | Core | Participant Experience Product Owner |
| 3 | **Institutions** | Participants (institution sub-area) | Core | Institutional Partnerships Owner |
| 4 | **Competitions** | Competitions | **Core** | Competition Operations Owner |
| 5 | **Applications** | Submissions (intake sub-area) | **Core** | Competition Operations Owner |
| 6 | **Performances** | Submissions (media sub-area) | **Core** | Content & Media Product Owner |
| 7 | **Judging** | Judging | **Core** | Judging Integrity Owner |
| 8 | **Results** | Judging (results sub-area) | **Core** | Results & Recognition Owner |
| 9 | **Finance** | Billing | Supporting | Finance / Billing Owner |
| 10 | **Notifications** | Notifications | Supporting | Communications & Engagement Owner |
| 11 | **Analytics** | Analytics / Reporting | Generic | Data & Insights Owner |
| 12 | **Audit** | Audit | Supporting | Compliance & Security Officer (DPO) |

### 3.2 Domain Relationships (high level)

```
Identity ──▶ Participants ──▶ Institutions
   │              │
   │              ▼
   │         Applications ──▶ Competitions
   │              │
   │              ▼
   │         Performances ──▶ Judging ──▶ Results
   │              │              │            │
   │              ▼              ▼            ▼
   └────────▶ Finance      Notifications   Analytics
                  │              │            │
                  └──────────────┴────────────┴──▶ Audit (observes all)
```

Cross-domain references are held **by identity** (business keys), never by reaching into another domain's internals — mirroring ARCH-001 §9.2. **Audit** and **Analytics** are downstream observers fed by domain events.

---

### 3.3 Domain 1 — Identity

**Description.** Manages who may access the platform and under what authority: accounts, roles, credentials, sessions, multi-factor enrollment, and — critically for a platform serving minors — **consent**. Children generally do not hold independent accounts; they are represented in *Participants* and acted for by guardians/teachers whose accounts live here (ARCH-001 §11.4).

**Responsibilities.**
- Establish and verify the identity of adult users (guardians, teachers, jury, organizers, administrators).
- Manage roles, permissions, and their assignment (RBAC per ARCH-001 §12).
- Record and version **consent** for participation and personal-data processing.
- Govern authentication artifacts (credentials, sessions, MFA) at the business level.

**Owner.** Identity & Trust Product Owner.

**Business Objects.** User Account, Role, Permission, Role Assignment, Credential, Authentication Session, Multi-Factor Enrollment, Email Verification, Password Reset Request, Login Attempt, Consent, Consent Type, Terms Acceptance, Guardian Link Invitation, Account Recovery Request.

---

### 3.4 Domain 2 — Participants

**Description.** Represents the children who take part in competitions and the adults directly responsible for them (parents/guardians and teachers), together with the relationships that connect a child to guardians, teachers, and institutions. This is the most privacy-sensitive domain.

**Responsibilities.**
- Maintain participant profiles with strict data minimization (ARCH-001 §21.6).
- Model guardian and teacher relationships and the authority they confer.
- Link participants to institutions, classes/groups, and age groups.
- Provide the trustworthy subject to which applications, performances, and results attach.

**Owner.** Participant Experience Product Owner.

**Business Objects.** Participant, Guardian, Teacher, Guardian Relationship, Teacher Relationship, Participant Profile, Guardian Profile, Teacher Profile, Participant Institution Membership, Participant Group Membership, Participant Portfolio, Talent Interest.

---

### 3.5 Domain 3 — Institutions

**Description.** Represents educational and creative organizations (schools, art schools, studios, «Дома творчества») that participate at scale, delegate administration to teachers, and view institutional analytics. Institutions form natural tenancy boundaries (ARCH-001 §12.5).

**Responsibilities.**
- Register and verify institutions and their administrators.
- Organize participants into classes/groups managed by teachers.
- Support bulk onboarding workflows (BG-5).
- Provide institutional scoping for access control and reporting.

**Owner.** Institutional Partnerships Owner.

**Business Objects.** Institution, Institution Profile, Institution Type, Institution Administrator, Class Group, Teacher Assignment, Institution Membership Request, Institution Verification, Institution Contact, Region, Locality.

---

### 3.6 Domain 4 — Competitions

**Description.** The configuration and lifecycle heart of the platform: a competition is a time-bounded event with categories/nominations, age groups, rounds, judging criteria, schedules, rules, fees, and prizes. Organizers own competitions end to end (ARCH-001 §2.1, §13.1).

**Responsibilities.**
- Define competition structure (nominations, age groups, rounds, criteria).
- Govern the competition lifecycle (draft → open → submission → judging → results → archive).
- Encode eligibility rules, schedules, fees, and prizes.
- Assign organizers and publish announcements.

**Owner.** Competition Operations Owner.

**Business Objects.** Competition, Competition Series, Nomination, Age Group, Round, Judging Criterion, Criteria Set, Competition Schedule, Competition Rule, Eligibility Rule, Organizer Assignment, Competition Status History, Competition Template, Prize, Prize Tier, Fee Schedule, Discount Policy, Competition Announcement, Competition Sponsor.

---

### 3.7 Domain 5 — Applications

**Description.** Represents a participant's **request to enter** a specific competition nomination — the intake record capturing who is applying, to what, with which consents and answers, and its eligibility and payment state. An application is distinct from the creative work itself (which lives in *Performances*).

**Responsibilities.**
- Capture and validate entries against eligibility rules.
- Bind the relevant consent snapshot and required form answers to each entry.
- Track application status (submitted → accepted → withdrawn/rejected) and waitlisting.
- Link an accepted application to the fee it incurs and the performance(s) it expects.

**Owner.** Competition Operations Owner.

**Business Objects.** Application, Application Form, Application Form Field, Application Answer, Application Attachment, Application Status History, Consent Snapshot, Eligibility Check, Application Fee, Waitlist Entry, Application Withdrawal, Application Review Note.

---

### 3.8 Domain 6 — Performances

**Description.** Represents the **creative work** a participant presents — a drawing, recording, video, document, or live performance slot — and the media assets, versions, moderation, and safety scans attached to it. Binary media is never the business object; the business object is the *performance* and its metadata (ARCH-001 §9.6, §21.3).

**Responsibilities.**
- Capture submitted works and their media assets and derived variants.
- Enforce content moderation and antivirus safety before judging.
- Preserve versioning and status history of a work.
- Present performances to judging in the required (often pseudonymized) form (ARCH-001 §21.6, ADR-0013).

**Owner.** Content & Media Product Owner.

**Business Objects.** Performance, Media Asset, Media Variant, Media Metadata, Performance Version, Performance Status History, Content Moderation Flag, Antivirus Scan Result, Performance Attachment, Performance Tag, Live Performance Slot.

---

### 3.9 Domain 7 — Judging

**Description.** The fairness-critical domain: how jury members are organized into panels, assigned work, and how they score it against weighted criteria — with conflict-of-interest controls, scoring windows, and immutable, auditable scoring actions (ARCH-001 §1.5, §13.1, §21.7).

**Responsibilities.**
- Organize jury members into panels and assign performances to judges.
- Capture scorecards and per-criterion scores with comments.
- Enforce conflict-of-interest declarations and recusals.
- Aggregate scores and resolve ties, feeding results.

**Owner.** Judging Integrity Owner.

**Business Objects.** Jury Member, Jury Panel, Panel Membership, Judge Assignment, Scorecard, Criterion Score, Judge Comment, Conflict of Interest Declaration, Recusal, Scoring Session, Scoring Window, Deliberation Note, Score Aggregation, Tie-Break Decision.

---

### 3.10 Domain 8 — Results

**Description.** Turns aggregated scores into published, defensible outcomes: rankings, awards, diplomas and certificates, prize allocations, and the handling of disputes. Results are the platform's most visible and reputationally sensitive output.

**Responsibilities.**
- Compute and publish rankings and awards from judging aggregates.
- Generate diplomas and certificates as recognized artifacts.
- Allocate prizes and record honorable mentions.
- Manage result publication, snapshots, and dispute resolution.

**Owner.** Results & Recognition Owner.

**Business Objects.** Result, Ranking, Ranking Entry, Award, Diploma, Certificate, Prize Allocation, Result Publication, Result Snapshot, Result Dispute, Dispute Resolution, Honorable Mention, Leaderboard.

---

### 3.11 Domain 9 — Finance

**Description.** Handles money: participation fees, orders and invoices, payments and refunds, discounts and coupons, pricing plans and subscriptions for institutions/organizers, and receipts. Money is always modeled precisely and never as an approximate quantity (ARCH-001 §9.4).

**Responsibilities.**
- Price competition participation and platform plans.
- Create orders/invoices and capture payments and refunds.
- Apply discounts and coupons; issue receipts.
- Track billing accounts and (future) organizer payouts.

**Owner.** Finance / Billing Owner.

**Business Objects.** Billing Account, Order, Invoice, Invoice Line Item, Fee, Payment, Payment Transaction, Refund, Discount Code, Coupon Redemption, Pricing Plan, Subscription, Payment Method, Tax Rate, Receipt, Payout.

---

### 3.12 Domain 10 — Notifications

**Description.** Reaches users through the right channel at the right time: templated messages, per-user preferences, delivery tracking, reminders, and digests across email and in-app channels (SMS/push as future channels per ARCH-001 §2.1).

**Responsibilities.**
- Manage notification templates and channels.
- Respect per-user notification preferences and consent.
- Dispatch messages and track their delivery and bounces.
- Schedule reminders and digests (e.g., deadline reminders).

**Owner.** Communications & Engagement Owner.

**Business Objects.** Notification, Notification Template, Notification Channel, Notification Preference, Message, Notification Delivery, Delivery Receipt, Bounce Record, Reminder, Digest, Notification Topic, Subscription Preference.

---

### 3.13 Domain 11 — Analytics

**Description.** Derives insight from platform activity: business and domain metrics, reports and dashboards for organizers and institutions, funnels and cohorts, and data exports. Analytics is a **read/derived** domain fed by domain events; it never mutates source-of-truth business objects (ARCH-001 §20.3, §31).

**Responsibilities.**
- Capture analytics events and compute metrics/KPIs.
- Provide reports, dashboards, and leaderboarding inputs.
- Support funnels (e.g., registration completion) and cohort analysis.
- Produce data exports for stakeholders.

**Owner.** Data & Insights Owner.

**Business Objects.** Analytics Event, Metric Definition, KPI Snapshot, Report, Dashboard, Funnel Definition, Cohort, Aggregate View, Data Export, Insight.

---

### 3.14 Domain 12 — Audit

**Description.** The immutable memory of the platform: an append-only trail of significant actions and access, consent history, data-subject requests, retention policy, and erasure records — the backbone of fairness, compliance (152-ФЗ), and trust (ARCH-001 §21.6–§21.7).

**Responsibilities.**
- Record who did what, when, and to which object, immutably.
- Maintain consent and access history for compliance.
- Fulfil and evidence data-subject requests (export/erasure).
- Govern retention and erasure per policy.

**Owner.** Compliance & Security Officer (Data Protection Officer).

**Business Objects.** Audit Log Entry, Change Record, Access Log Entry, Consent Audit Record, Data Subject Request, Data Erasure Record, Retention Policy, Security Event, Admin Action Record, Legal Hold.

---

## 4. Business Objects — Detailed Specifications

> Full specifications for **core objects and aggregate roots**. Every object listed in a domain above appears in the **Business Object Catalog** (§5) with its purpose and lifecycle summary; the cards below give depth to the objects that carry the most business meaning and rules. Lifecycles use `↓` to denote the primary state progression.

### 4.1 Identity

#### User Account
- **Purpose.** Represents an adult actor who can authenticate and act on the platform (guardian, teacher, jury, organizer, administrator).
- **Description.** The root of an authenticated identity. Children are **not** User Accounts; they are Participants acted for by adults.
- **Domain.** Identity.
- **Lifecycle.** Registered ↓ Email-Verified ↓ Active ↓ Suspended ↓ Deactivated ↓ Erased.
- **Business Owner.** Identity & Trust Product Owner.
- **Main Attributes.** Account identifier, contact email, display name, account status, primary locale, created date, last-active date, MFA-enabled flag.
- **Relationships.** Holds Roles (via Role Assignment); owns Credentials, Authentication Sessions, MFA Enrollments; may be a Guardian, Teacher, Jury Member, Organizer, or Administrator; grants Consent; owns a Billing Account.
- **Business Rules.**
  - An account must verify its email before performing sensitive actions.
  - Privileged roles (Administrator, Organizer, Jury) require MFA enrollment.
  - Deactivation preserves audit history; erasure follows the retention/DSAR policy.
  - One verified email maps to at most one active account.

#### Role
- **Purpose.** A named bundle of permissions expressing what a user may do.
- **Description.** Business roles mirror ARCH-001 §12.2 (Participant, Parent/Guardian, Teacher, Institution Admin, Jury, Organizer, Administrator).
- **Domain.** Identity.
- **Lifecycle.** Defined ↓ Active ↓ Deprecated.
- **Business Owner.** Identity & Trust Product Owner.
- **Main Attributes.** Role name, description, permission set reference, scope type (global / institution / competition).
- **Relationships.** Grouped Permissions; granted to User Accounts via Role Assignment.
- **Business Rules.**
  - Roles are additive; absence of a grant is denial (deny by default).
  - Scoped roles apply only within their scope (e.g., Organizer of a specific competition).

#### Role Assignment
- **Purpose.** Binds a role to a user, optionally within a scope.
- **Description.** Records that a specific account holds a specific role in a specific context.
- **Domain.** Identity.
- **Lifecycle.** Granted ↓ Active ↓ Revoked ↓ Expired.
- **Business Owner.** Identity & Trust Product Owner.
- **Main Attributes.** Account reference, role reference, scope reference (nullable), granted-by, granted date, expiry date.
- **Relationships.** Links User Account and Role; scope may reference an Institution or Competition.
- **Business Rules.**
  - Every assignment is auditable (who granted, when, why).
  - Scoped assignments cannot exceed the granting authority's own scope.

#### Consent
- **Purpose.** Records a guardian's (or authorized adult's) authorization for a minor's participation and personal-data processing.
- **Description.** A first-class, versioned, auditable record central to Privacy by Design (ARCH-001 §11.4, §21.6). Without valid consent, a participant cannot be entered into a competition.
- **Domain.** Identity.
- **Lifecycle.** Requested ↓ Granted ↓ Active ↓ Withdrawn / Expired ↓ Superseded (by a new version).
- **Business Owner.** Compliance & Security Officer (DPO).
- **Main Attributes.** Consent type, granting account, subject participant, purpose, consent-text version, granted date, expiry date, withdrawal date, status.
- **Relationships.** Granted by a Guardian (User Account); about a Participant; of a Consent Type; snapshotted into each Application (Consent Snapshot); audited in Consent Audit Record.
- **Business Rules.**
  - Consent is purpose-limited: separate purposes require separate consent.
  - Withdrawal must be honored and cascade to dependent processing per retention policy.
  - The exact consent text version in force is preserved immutably for evidence.
  - A minor's participation requires an **active, matching** consent at the moment of application.

#### Authentication Session
- **Purpose.** Represents an active authenticated presence of a user.
- **Description.** Business-level view of a login session (technical token detail lives in ARCH-001 §11).
- **Domain.** Identity.
- **Lifecycle.** Established ↓ Active ↓ Refreshed ↓ Expired / Revoked.
- **Business Owner.** Identity & Trust Product Owner.
- **Main Attributes.** Account reference, established date, last-seen date, device descriptor, status.
- **Relationships.** Belongs to a User Account.
- **Business Rules.** A session may be revoked by the user or an administrator; revocation is immediate and audited.

### 4.2 Participants

#### Participant
- **Purpose.** Represents a child participating in competitions.
- **Description.** The subject of applications, performances, and results — modeled with strict data minimization. A participant does not authenticate independently.
- **Domain.** Participants.
- **Lifecycle.** Created ↓ Verified ↓ Active ↓ Archived ↓ Erased.
- **Business Owner.** Participant Experience Product Owner.
- **Main Attributes.** Participant identifier, given name, family name, date of birth (for age-group derivation), age group (derived), display alias (for pseudonymized judging), status.
- **Relationships.** Guardian(s), Teacher(s), Institution, Class Group, Applications, Performances, Results, Diplomas, Consent, Participant Portfolio.
- **Business Rules.**
  - A participant must be linked to at least one verified Guardian **or** an authorized Institution/Teacher with recorded consent before becoming Active.
  - Age group is derived from date of birth relative to the competition's reference date; it is never entered free-hand.
  - Personal identity is visible only to the guardian, assigned teacher, and authorized organizers; judging sees the pseudonymized alias (ADR-0013).
  - Erasure honors DSAR and cascades to performances/media per retention policy.

#### Guardian
- **Purpose.** Represents a parent or legal guardian responsible for one or more participants.
- **Description.** An adult User Account acting on behalf of children, granting consent and managing entries.
- **Domain.** Participants.
- **Lifecycle.** Created ↓ Verified ↓ Active ↓ Archived.
- **Business Owner.** Participant Experience Product Owner.
- **Main Attributes.** Linked account reference, given name, family name, contact phone, relationship-to-child descriptor, verification status.
- **Relationships.** Linked to a User Account; Guardian Relationship to Participant(s); grants Consent; may pay via Billing Account.
- **Business Rules.**
  - A guardian may manage only participants to whom a verified Guardian Relationship exists.
  - Guardian verification is required before granting legally meaningful consent.

#### Teacher
- **Purpose.** Represents an educator who manages participants within an institution.
- **Description.** An adult account with delegated authority over a class/group of participants (ARCH-001 §12.2).
- **Domain.** Participants.
- **Lifecycle.** Invited ↓ Verified ↓ Active ↓ Suspended ↓ Archived.
- **Business Owner.** Institutional Partnerships Owner.
- **Main Attributes.** Linked account reference, given name, family name, subject/discipline, institution reference, status.
- **Relationships.** Linked to a User Account; Teacher Assignment to Institution/Class Group; Teacher Relationship to Participants; may create Applications on behalf of participants (with consent).
- **Business Rules.**
  - A teacher acts only within their assigned institution and classes.
  - Teacher-initiated participation still requires valid guardian consent for each minor.

#### Guardian Relationship
- **Purpose.** Establishes the authoritative link between a guardian and a participant.
- **Description.** Encodes the legal/managerial relationship enabling consent and management.
- **Domain.** Participants.
- **Lifecycle.** Proposed ↓ Verified ↓ Active ↓ Revoked.
- **Business Owner.** Participant Experience Product Owner.
- **Main Attributes.** Guardian reference, participant reference, relationship type, verification status, established date.
- **Relationships.** Connects Guardian and Participant.
- **Business Rules.** At least one Active relationship is required for a minor's participation absent institutional authority.

### 4.3 Institutions

#### Institution
- **Purpose.** Represents an educational or creative organization participating on the platform.
- **Description.** A tenant grouping participants, teachers, and classes; supports bulk workflows and institutional analytics.
- **Domain.** Institutions.
- **Lifecycle.** Registered ↓ Verified ↓ Active ↓ Suspended ↓ Archived.
- **Business Owner.** Institutional Partnerships Owner.
- **Main Attributes.** Institution name, institution type, region, locality, official contact, verification status, status.
- **Relationships.** Institution Administrators, Teachers, Class Groups, Participant Institution Memberships, Region/Locality, Subscription (Finance), Institution Verification.
- **Business Rules.**
  - Only verified institutions may access bulk onboarding and institutional analytics.
  - Institution scope bounds data access for its administrators and teachers (tenancy).

#### Class Group
- **Purpose.** Organizes participants into a manageable teaching unit within an institution.
- **Description.** A named group (class, studio, ensemble) a teacher manages.
- **Domain.** Institutions.
- **Lifecycle.** Created ↓ Active ↓ Archived.
- **Business Owner.** Institutional Partnerships Owner.
- **Main Attributes.** Group name, institution reference, responsible teacher, age band, academic period.
- **Relationships.** Belongs to Institution; managed by Teacher (Teacher Assignment); contains Participants (Participant Group Membership).
- **Business Rules.** A class group belongs to exactly one institution; membership implies institutional membership.

#### Institution Administrator
- **Purpose.** Represents the person authorized to govern an institution's presence.
- **Description.** Delegates teacher roles and views institutional analytics (ARCH-001 §12.2).
- **Domain.** Institutions.
- **Lifecycle.** Invited ↓ Verified ↓ Active ↓ Revoked.
- **Business Owner.** Institutional Partnerships Owner.
- **Main Attributes.** Account reference, institution reference, appointment date, status.
- **Relationships.** Links User Account and Institution; grants Teacher Assignments.
- **Business Rules.** May delegate only within the institution; all delegations are audited.

### 4.4 Competitions

#### Competition
- **Purpose.** Represents a time-bounded creative competition event.
- **Description.** The central configurable event owning nominations, age groups, rounds, criteria, schedule, rules, fees, and prizes. **Aggregate root** of the Competitions domain (ARCH-001 §13.4).
- **Domain.** Competitions.
- **Lifecycle.** Draft ↓ Published ↓ Open (applications) ↓ Submission ↓ Judging ↓ Results ↓ Archived (with Cancelled as an alternate terminal state).
- **Business Owner.** Competition Operations Owner.
- **Main Attributes.** Title, description, organizer reference, competition series (optional), status, key dates (open/close/judging/results), visibility, participation fee reference, locale.
- **Relationships.** Belongs to Competition Series; has Nominations, Age Groups, Rounds, Criteria Sets, Schedule, Rules, Eligibility Rules, Prizes, Fee Schedule, Announcements; assigned Organizers; receives Applications; produces Results.
- **Business Rules.**
  - Status transitions are strictly ordered and time-gated; a competition cannot enter Judging before its submission window closes.
  - A published competition must have at least one nomination, one age group, and a valid criteria set.
  - Dates must be consistent (open ≤ close ≤ judging-start ≤ results).
  - Once results are published, competition structure becomes immutable except through a governed correction process.

#### Nomination
- **Purpose.** A category of creative work within a competition (e.g., «Рисунок», «Вокал»).
- **Description.** The specific class an application enters; combined with an age group it defines a competing cohort.
- **Domain.** Competitions.
- **Lifecycle.** Defined ↓ Active ↓ Closed ↓ Archived.
- **Business Owner.** Competition Operations Owner.
- **Main Attributes.** Nomination name, description, discipline, media requirements, criteria set reference.
- **Relationships.** Belongs to Competition; associated with Age Groups; targeted by Applications; scored via its Criteria Set.
- **Business Rules.** A nomination must reference a criteria set before the competition opens.

#### Round
- **Purpose.** A judging stage within a competition (e.g., qualification, final).
- **Description.** Sequences judging into stages, each with its own scoring window and possibly its own criteria.
- **Domain.** Competitions.
- **Lifecycle.** Planned ↓ Open ↓ Scoring ↓ Closed.
- **Business Owner.** Competition Operations Owner.
- **Main Attributes.** Round name, sequence order, start/end dates, advancement policy, criteria set reference.
- **Relationships.** Belongs to Competition; governs Judge Assignments and Scorecards; feeds advancement into the next Round.
- **Business Rules.**
  - A performance cannot be scored before its round opens (domain invariant, ARCH-001 §13.4).
  - Advancement from a round is governed by its advancement policy applied to aggregated scores.

#### Judging Criterion
- **Purpose.** A weighted dimension along which work is evaluated.
- **Description.** Defines a single scored aspect (e.g., «Техника», «Оригинальность») with a weight and scale.
- **Domain.** Competitions.
- **Lifecycle.** Defined ↓ Active ↓ Retired.
- **Business Owner.** Competition Operations Owner.
- **Main Attributes.** Criterion name, description, weight, score scale (min/max), guidance text.
- **Relationships.** Grouped into a Criteria Set; scored by Criterion Score (Judging).
- **Business Rules.**
  - Criterion weights within a criteria set must sum to a defined whole (e.g., 100%).
  - Criteria in force are frozen once judging starts.

#### Criteria Set
- **Purpose.** The complete, weighted collection of criteria used to score a nomination/round.
- **Description.** Ensures every judge scores against the same defined rubric.
- **Domain.** Competitions.
- **Lifecycle.** Draft ↓ Published ↓ Frozen ↓ Archived.
- **Business Owner.** Competition Operations Owner.
- **Main Attributes.** Set name, version, list of criteria (with weights), aggregation method.
- **Relationships.** Referenced by Nomination and/or Round; drives Scorecard structure.
- **Business Rules.** A criteria set becomes Frozen when its round enters scoring and cannot change thereafter.

#### Prize
- **Purpose.** A reward offered for achievement in a competition.
- **Description.** Defines what winners receive (diploma level, material prize, scholarship).
- **Domain.** Competitions.
- **Lifecycle.** Defined ↓ Active ↓ Allocated ↓ Archived.
- **Business Owner.** Competition Operations Owner.
- **Main Attributes.** Prize name, description, prize tier, quantity, sponsor reference (optional).
- **Relationships.** Belongs to Competition; organized by Prize Tier; realized via Prize Allocation (Results); may reference a Competition Sponsor.
- **Business Rules.** Total allocations of a prize cannot exceed its quantity.

### 4.5 Applications

#### Application
- **Purpose.** Represents a participant's request to enter a specific competition nomination.
- **Description.** The intake record binding participant, nomination, age group, consent snapshot, and answers; **aggregate root** of the Applications domain.
- **Domain.** Applications.
- **Lifecycle.** Draft ↓ Submitted ↓ Under Review ↓ Accepted ↓ (Waitlisted) ↓ Withdrawn / Rejected.
- **Business Owner.** Competition Operations Owner.
- **Main Attributes.** Application identifier, participant reference, competition reference, nomination reference, age group (derived), submitter (guardian/teacher), status, submitted date.
- **Relationships.** For a Participant; into a Competition Nomination; carries Application Answers, Attachments, a Consent Snapshot, an Eligibility Check, and an Application Fee; expects one or more Performances; produces Application Status History.
- **Business Rules.**
  - An application cannot be submitted without an active, matching Consent Snapshot.
  - It must pass the Eligibility Check (age group, institution, per-participant entry limits) to be Accepted.
  - Acceptance may be contingent on fee payment where the competition is paid.
  - Withdrawal is permitted until a competition-defined cutoff and is audited.

#### Consent Snapshot
- **Purpose.** Freezes the exact consent in force at the moment of application.
- **Description.** An immutable copy proving which consent (and text version) authorized this specific entry.
- **Domain.** Applications.
- **Lifecycle.** Captured ↓ Immutable.
- **Business Owner.** Compliance & Security Officer (DPO).
- **Main Attributes.** Source consent reference, consent-text version, captured date, purpose.
- **Relationships.** Belongs to Application; derived from Consent (Identity).
- **Business Rules.** Never modified after capture; used as evidence in audits and disputes.

#### Eligibility Check
- **Purpose.** Records the evaluation of an application against the competition's eligibility rules.
- **Description.** A pass/fail decision with reasons, ensuring only valid entries proceed.
- **Domain.** Applications.
- **Lifecycle.** Pending ↓ Passed / Failed.
- **Business Owner.** Competition Operations Owner.
- **Main Attributes.** Application reference, outcome, evaluated rules, failure reasons, evaluated date.
- **Relationships.** Belongs to Application; evaluates Eligibility Rules (Competitions).
- **Business Rules.** A failed check blocks acceptance; the reasons are surfaced to the submitter.

### 4.6 Performances

#### Performance
- **Purpose.** Represents the creative work a participant submits for evaluation.
- **Description.** The judged artifact — drawing, recording, video, document, or live slot — with its media assets and safety state. **Aggregate root** of the Performances domain (owns its media references and status transitions per ARCH-001 §13.4).
- **Domain.** Performances.
- **Lifecycle.** Draft ↓ Uploaded ↓ Scanning ↓ Under Moderation ↓ Accepted ↓ (Rejected) ↓ Withdrawn ↓ Archived.
- **Business Owner.** Content & Media Product Owner.
- **Main Attributes.** Performance identifier, application reference, participant reference (pseudonymized for judging), title, description, media requirement compliance flag, status, submitted date.
- **Relationships.** Belongs to an Application; owns Media Assets, Media Variants, Performance Versions; has Content Moderation Flags and Antivirus Scan Results; is scored via Judge Assignments and Scorecards; contributes to Results.
- **Business Rules.**
  - A performance cannot enter judging until it is virus-scanned clean and moderation-cleared.
  - Judges see the performance in pseudonymized form (no participant identity) (ADR-0013).
  - Media bytes are stored externally; the performance holds only references and metadata (ARCH-001 §9.6).
  - Re-submission before the deadline creates a new Performance Version; the version scored is fixed when its round opens.

#### Media Asset
- **Purpose.** Represents a single uploaded media file belonging to a performance.
- **Description.** A business reference to externally stored content (image/audio/video/document) with integrity and type metadata.
- **Domain.** Performances.
- **Lifecycle.** Registered ↓ Uploaded ↓ Scanned ↓ Available ↓ Quarantined / Deleted.
- **Business Owner.** Content & Media Product Owner.
- **Main Attributes.** Asset identifier, media type, original file name, checksum, size, storage reference, upload date.
- **Relationships.** Belongs to Performance; has derived Media Variants; has Media Metadata and Antivirus Scan Result.
- **Business Rules.**
  - An asset failing the antivirus scan is quarantined and never exposed.
  - Type and size must satisfy the nomination's media requirements.

#### Content Moderation Flag
- **Purpose.** Records a moderation concern raised against a performance or asset.
- **Description.** Ensures inappropriate content is caught before judging or publication.
- **Domain.** Performances.
- **Lifecycle.** Raised ↓ Under Review ↓ Upheld / Dismissed.
- **Business Owner.** Content & Media Product Owner.
- **Main Attributes.** Subject reference, reason category, severity, raised-by (automated/human), status, resolution notes.
- **Relationships.** Attached to Performance or Media Asset; feeds Audit.
- **Business Rules.** An upheld high-severity flag blocks a performance from judging and results.

### 4.7 Judging

#### Jury Member
- **Purpose.** Represents a qualified individual who evaluates performances.
- **Description.** An account granted the Jury role, organized into panels and assigned work (ARCH-001 §12.2).
- **Domain.** Judging.
- **Lifecycle.** Invited ↓ Confirmed ↓ Active ↓ Recused ↓ Retired.
- **Business Owner.** Judging Integrity Owner.
- **Main Attributes.** Account reference, expertise areas, credentials, status.
- **Relationships.** Linked to User Account; member of Jury Panels (Panel Membership); receives Judge Assignments; authors Scorecards, Criterion Scores, Judge Comments; may file Conflict of Interest Declarations and Recusals.
- **Business Rules.**
  - A jury member must declare conflicts of interest before scoring.
  - A recused member's scores for the affected performance are void and excluded from aggregation.

#### Judge Assignment
- **Purpose.** Allocates a specific performance (or set) to a specific jury member for a round.
- **Description.** The unit of judging work, scoping what a judge may score.
- **Domain.** Judging.
- **Lifecycle.** Assigned ↓ In Progress ↓ Completed ↓ Reassigned / Voided.
- **Business Owner.** Judging Integrity Owner.
- **Main Attributes.** Jury member reference, performance reference, round reference, assigned date, status.
- **Relationships.** Links Jury Member and Performance within a Round; produces a Scorecard.
- **Business Rules.**
  - A judge may score **only** performances they are assigned (ARCH-001 §12.1).
  - Assignment respects conflict-of-interest declarations (no assignment where a conflict exists).

#### Scorecard
- **Purpose.** A jury member's complete evaluation of one performance in one round.
- **Description.** Groups the per-criterion scores and comments into one auditable submission. **Aggregate root** for a single judging act.
- **Domain.** Judging.
- **Lifecycle.** Opened ↓ In Progress ↓ Submitted ↓ Locked.
- **Business Owner.** Judging Integrity Owner.
- **Main Attributes.** Judge assignment reference, criteria set reference, submitted date, total (derived), status.
- **Relationships.** Belongs to a Judge Assignment; contains Criterion Scores; may hold Judge Comments; contributes to Score Aggregation.
- **Business Rules.**
  - A scorecard is valid only if every criterion in the frozen criteria set is scored.
  - Once Submitted within a closed scoring window, it is Locked and immutable; corrections require a governed, audited process.
  - The scoring act is recorded immutably in Audit within the same boundary as the write (ARCH-001 §3.2).

#### Criterion Score
- **Purpose.** A single numeric evaluation against one criterion.
- **Description.** The atomic scoring value; its business rules protect fairness.
- **Domain.** Judging.
- **Lifecycle.** Entered ↓ Submitted ↓ Locked.
- **Business Owner.** Judging Integrity Owner.
- **Main Attributes.** Scorecard reference, criterion reference, score value, optional note.
- **Relationships.** Belongs to a Scorecard; references a Judging Criterion.
- **Business Rules.** The value must lie within the criterion's defined scale; out-of-range values are rejected.

#### Conflict of Interest Declaration
- **Purpose.** Records a jury member's disclosed relationship that could bias judging.
- **Description.** A transparency control central to fairness (BG-3).
- **Domain.** Judging.
- **Lifecycle.** Declared ↓ Reviewed ↓ Accepted (leads to Recusal) / Cleared.
- **Business Owner.** Judging Integrity Owner.
- **Main Attributes.** Jury member reference, subject reference (participant/institution/competition), nature of conflict, declared date, outcome.
- **Relationships.** Filed by Jury Member; may produce a Recusal; audited.
- **Business Rules.** An accepted conflict prevents assignment/scoring of the affected work.

#### Score Aggregation
- **Purpose.** Combines valid scorecards into a comparable result for each performance.
- **Description.** Applies the criteria-set aggregation method and weighting to produce a performance's standing.
- **Domain.** Judging.
- **Lifecycle.** Pending ↓ Computed ↓ Finalized.
- **Business Owner.** Judging Integrity Owner.
- **Main Attributes.** Performance reference, round reference, aggregated value, contributing scorecard count, method, computed date.
- **Relationships.** Aggregates Scorecards; feeds Ranking (Results); may trigger Tie-Break Decision.
- **Business Rules.**
  - Only valid, non-recused, locked scorecards contribute.
  - The method and inputs are recorded for auditability (BG-3).

### 4.8 Results

#### Result
- **Purpose.** Represents the official outcome for a performance/participant in a competition.
- **Description.** The published standing and recognition; **aggregate root** for a participant's outcome in a competition/nomination.
- **Domain.** Results.
- **Lifecycle.** Draft ↓ Under Review ↓ Published ↓ (Disputed ↓ Corrected) ↓ Archived.
- **Business Owner.** Results & Recognition Owner.
- **Main Attributes.** Participant reference, competition/nomination reference, rank, award level, aggregated score, publication status.
- **Relationships.** Derived from Score Aggregation; part of a Ranking; yields Award(s), Diploma/Certificate, Prize Allocation; may be subject to Result Dispute.
- **Business Rules.**
  - A result is published only after judging for its round is finalized.
  - Published results are immutable except via a governed Dispute Resolution/correction, which is audited.
  - Result visibility respects participant privacy (identity shown only to authorized viewers).

#### Ranking
- **Purpose.** Orders performances within a nomination/age-group/round by aggregated score.
- **Description.** The comparative standing from which awards are derived.
- **Domain.** Results.
- **Lifecycle.** Draft ↓ Finalized ↓ Published ↓ Superseded.
- **Business Owner.** Results & Recognition Owner.
- **Main Attributes.** Competition/nomination/age-group/round scope, ordered ranking entries, method, finalized date.
- **Relationships.** Composed of Ranking Entries; derived from Score Aggregations; drives Awards.
- **Business Rules.** Ties are resolved by the recorded Tie-Break Decision before finalization.

#### Diploma
- **Purpose.** A recognized certificate of achievement issued to a participant.
- **Description.** A generated, verifiable artifact acknowledging a result (BG-6).
- **Domain.** Results.
- **Lifecycle.** Requested ↓ Generated ↓ Issued ↓ Revoked / Reissued.
- **Business Owner.** Results & Recognition Owner.
- **Main Attributes.** Participant reference, competition reference, award level, issue date, verification code, document reference.
- **Relationships.** Issued for a Result; belongs to a Participant; delivered via Notifications.
- **Business Rules.**
  - A diploma is issued only for a published result.
  - Each diploma carries a unique verification code for authenticity.
  - Revocation (e.g., after a successful dispute) is audited and the artifact invalidated.

#### Result Dispute
- **Purpose.** Captures a challenge to a published result.
- **Description.** Enables fair correction and keeps the dispute rate measurable (BG-3).
- **Domain.** Results.
- **Lifecycle.** Raised ↓ Under Review ↓ Resolved (Upheld / Rejected) ↓ Closed.
- **Business Owner.** Results & Recognition Owner.
- **Main Attributes.** Result reference, raised-by, grounds, status, resolution summary, decided date.
- **Relationships.** Against a Result; leads to a Dispute Resolution; audited.
- **Business Rules.** An upheld dispute triggers a governed result correction and possible diploma reissue.

### 4.9 Finance

#### Order
- **Purpose.** Represents a purchase intent (e.g., paid competition entry, plan subscription).
- **Description.** Groups what is being charged before payment; **aggregate root** tying line items, fees, and payment.
- **Domain.** Finance.
- **Lifecycle.** Created ↓ Pending Payment ↓ Paid ↓ (Partially Refunded / Refunded) ↓ Cancelled.
- **Business Owner.** Finance / Billing Owner.
- **Main Attributes.** Order identifier, billing account reference, total amount (Money), currency, status, created date.
- **Relationships.** Belongs to a Billing Account; contains Invoice Line Items; incurs Fees; settled by Payment; may apply Coupon Redemption; produces Invoice and Receipt.
- **Business Rules.**
  - An order total equals the sum of its line items less discounts, expressed in a single currency.
  - Acceptance of a paid application is contingent on the corresponding order being Paid.

#### Payment
- **Purpose.** Represents money received against an order.
- **Description.** The settlement record; delegates external processing to a payment provider via an anti-corruption boundary (ARCH-001 §13.3).
- **Domain.** Finance.
- **Lifecycle.** Initiated ↓ Authorized ↓ Captured ↓ (Failed / Refunded).
- **Business Owner.** Finance / Billing Owner.
- **Main Attributes.** Order reference, amount (Money), method reference, provider reference, status, captured date.
- **Relationships.** Settles an Order; composed of Payment Transactions; may yield Refunds; produces a Receipt.
- **Business Rules.**
  - Amounts are stored precisely as Money (minor units), never as floats (ARCH-001 §9.4).
  - A refund cannot exceed the captured amount.
  - Every payment state change is audited.

#### Invoice
- **Purpose.** A formal statement of amounts owed or paid.
- **Description.** The billing document derived from an order.
- **Domain.** Finance.
- **Lifecycle.** Draft ↓ Issued ↓ Paid ↓ Void.
- **Business Owner.** Finance / Billing Owner.
- **Main Attributes.** Invoice number, billing account, order reference, line items, tax, total (Money), issue date, due date.
- **Relationships.** Derived from an Order; contains Invoice Line Items; references Tax Rate.
- **Business Rules.** An issued invoice is immutable; corrections are made by void + reissue.

### 4.10 Notifications

#### Notification
- **Purpose.** Represents an intent to inform a user of an event.
- **Description.** The business event-to-message linkage; rendered via a template and delivered on channels the user permits.
- **Domain.** Notifications.
- **Lifecycle.** Created ↓ Queued ↓ Sent ↓ Delivered ↓ (Failed / Read).
- **Business Owner.** Communications & Engagement Owner.
- **Main Attributes.** Recipient reference, notification topic, template reference, payload summary, status, created date.
- **Relationships.** For a User Account; uses a Notification Template; sent over Notification Channels; respects Notification Preference; produces Notification Deliveries and Delivery Receipts.
- **Business Rules.**
  - A notification is sent only on channels the recipient has not opted out of (respecting preferences and consent).
  - Deadline and result notifications are prioritized over promotional messages.

#### Notification Template
- **Purpose.** A reusable, localized message pattern.
- **Description.** Ensures consistent, translatable messaging (ARCH-001 §8.6).
- **Domain.** Notifications.
- **Lifecycle.** Draft ↓ Published ↓ Deprecated.
- **Business Owner.** Communications & Engagement Owner.
- **Main Attributes.** Template key, locale, subject pattern, body pattern, channel applicability, version.
- **Relationships.** Used by Notifications; localized per locale.
- **Business Rules.** A template must exist in the primary locale (ru-RU) before use.

#### Notification Preference
- **Purpose.** Captures a user's choices about how and whether to be contacted.
- **Description.** Enforces respectful, consent-aligned communication.
- **Domain.** Notifications.
- **Lifecycle.** Default ↓ Customized ↓ Updated.
- **Business Owner.** Communications & Engagement Owner.
- **Main Attributes.** User reference, per-topic channel opt-in/opt-out, quiet hours, locale.
- **Relationships.** Belongs to a User Account; consulted by Notification dispatch.
- **Business Rules.** Transactional/critical notices may be exempt from opt-out per policy; marketing is always opt-outable.

### 4.11 Analytics

#### Analytics Event
- **Purpose.** A recorded, derived signal about platform activity.
- **Description.** The raw material of metrics; sourced from domain events, never mutating source data.
- **Domain.** Analytics.
- **Lifecycle.** Captured ↓ Processed ↓ Aggregated ↓ Expired.
- **Business Owner.** Data & Insights Owner.
- **Main Attributes.** Event type, occurred date, subject domain, anonymized subject reference, measured values.
- **Relationships.** Derived from domain events; rolled up into KPI Snapshots and Aggregate Views.
- **Business Rules.** Analytics data is minimized and pseudonymized; it must not re-identify minors (ARCH-001 §21.6).

#### KPI Snapshot
- **Purpose.** A point-in-time value of a business metric.
- **Description.** Supports dashboards tracking the business goals (BG-1…BG-8).
- **Domain.** Analytics.
- **Lifecycle.** Computed ↓ Published ↓ Superseded.
- **Business Owner.** Data & Insights Owner.
- **Main Attributes.** Metric definition reference, period, value, dimensions.
- **Relationships.** Based on Metric Definition; displayed in Dashboards/Reports.
- **Business Rules.** Snapshots are reproducible from their inputs and period.

### 4.12 Audit

#### Audit Log Entry
- **Purpose.** An immutable record of a significant action or access.
- **Description.** The append-only backbone of trust, fairness, and compliance (ARCH-001 §21.7).
- **Domain.** Audit.
- **Lifecycle.** Recorded ↓ Immutable (retained per policy) ↓ Purged (only when retention allows).
- **Business Owner.** Compliance & Security Officer (DPO).
- **Main Attributes.** Actor reference, action, subject object reference, occurred date, context/correlation, outcome.
- **Relationships.** References any business object as its subject; observes all domains.
- **Business Rules.**
  - Entries are never updated or deleted outside the retention/erasure policy.
  - Scoring, result publication, consent changes, authorization decisions, and personal-data operations must produce audit entries (ARCH-001 §21.7).

#### Data Subject Request
- **Purpose.** Captures a guardian's/user's request regarding personal data (access, export, erasure).
- **Description.** Operationalizes data-subject rights under 152-ФЗ (ARCH-001 §21.6).
- **Domain.** Audit.
- **Lifecycle.** Received ↓ Verified ↓ In Progress ↓ Fulfilled ↓ Closed.
- **Business Owner.** Compliance & Security Officer (DPO).
- **Main Attributes.** Requester reference, subject participant reference, request type, received date, due date, status.
- **Relationships.** About a Participant/User Account; produces a Data Erasure Record; audited.
- **Business Rules.**
  - Requests are fulfilled within regulatory timelines.
  - Erasure cascades to performances, media, and backups per the retention policy (ARCH-001 §3.2).

#### Retention Policy
- **Purpose.** Defines how long each class of data is kept and when it is erased.
- **Description.** The governing rule set for lifecycle terminal states across domains.
- **Domain.** Audit.
- **Lifecycle.** Defined ↓ Active ↓ Revised ↓ Retired.
- **Business Owner.** Compliance & Security Officer (DPO).
- **Main Attributes.** Data class, retention period, legal basis, erasure method, effective date.
- **Relationships.** Governs erasure of objects across all domains; referenced by Data Erasure Record and Legal Hold.
- **Business Rules.** A Legal Hold suspends erasure for affected objects until the hold is lifted.

---

## 5. Business Object Catalog

The complete enumeration of business objects, grouped by domain. **AR** = Aggregate Root. Lifecycle column gives the primary states. Objects with full cards in §4 are marked ★.

### 5.1 Identity (15)

| # | Business Object | AR | Purpose (business) | Lifecycle summary |
|---|-----------------|----|--------------------|-------------------|
| 1 | User Account ★ | ✔ | Authenticated adult actor | Registered→Verified→Active→Suspended→Deactivated→Erased |
| 2 | Role ★ | | Named permission bundle | Defined→Active→Deprecated |
| 3 | Permission | | Atomic capability | Defined→Active→Retired |
| 4 | Role Assignment ★ | | Binds role to user in scope | Granted→Active→Revoked→Expired |
| 5 | Credential | | Business view of a login secret | Set→Active→Rotated→Revoked |
| 6 | Authentication Session ★ | | Active authenticated presence | Established→Active→Refreshed→Expired |
| 7 | Multi-Factor Enrollment | | Registered second factor | Enrolled→Active→Disabled |
| 8 | Email Verification | | Proof of email ownership | Requested→Sent→Verified→Expired |
| 9 | Password Reset Request | | Recovery of access | Requested→Sent→Used→Expired |
| 10 | Login Attempt | | Record of an authentication try | Recorded (immutable) |
| 11 | Consent ★ | ✔ | Guardian authorization for a minor | Requested→Granted→Active→Withdrawn/Expired→Superseded |
| 12 | Consent Type | | Category/purpose of consent | Defined→Active→Retired |
| 13 | Terms Acceptance | | Acceptance of platform terms | Presented→Accepted→Superseded |
| 14 | Guardian Link Invitation | | Invite to link a guardian to a child | Sent→Accepted→Expired |
| 15 | Account Recovery Request | | Assisted account recovery | Opened→Verified→Resolved |

### 5.2 Participants (12)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 16 | Participant ★ | ✔ | A child taking part | Created→Verified→Active→Archived→Erased |
| 17 | Guardian ★ | | Parent/legal guardian | Created→Verified→Active→Archived |
| 18 | Teacher ★ | | Educator managing participants | Invited→Verified→Active→Suspended→Archived |
| 19 | Guardian Relationship ★ | | Authoritative guardian↔child link | Proposed→Verified→Active→Revoked |
| 20 | Teacher Relationship | | Teacher↔participant link | Proposed→Active→Ended |
| 21 | Participant Profile | | Minimized descriptive data of a child | Created→Updated→Archived |
| 22 | Guardian Profile | | Contact/descriptive data of guardian | Created→Updated→Archived |
| 23 | Teacher Profile | | Descriptive data of teacher | Created→Updated→Archived |
| 24 | Participant Institution Membership | | Links participant to institution | Requested→Active→Ended |
| 25 | Participant Group Membership | | Links participant to a class group | Added→Active→Removed |
| 26 | Participant Portfolio | | Collection of a child's works/results | Created→Active→Archived |
| 27 | Talent Interest | | Declared creative interest | Declared→Active→Removed |

### 5.3 Institutions (11)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 28 | Institution ★ | ✔ | Educational/creative organization | Registered→Verified→Active→Suspended→Archived |
| 29 | Institution Profile | | Descriptive data of institution | Created→Updated→Archived |
| 30 | Institution Type | | Classification of institution | Defined→Active→Retired |
| 31 | Institution Administrator ★ | | Governs an institution's presence | Invited→Verified→Active→Revoked |
| 32 | Class Group ★ | | Teaching unit of participants | Created→Active→Archived |
| 33 | Teacher Assignment | | Assigns a teacher to institution/class | Assigned→Active→Ended |
| 34 | Institution Membership Request | | Request to join/represent an institution | Submitted→Reviewed→Approved/Rejected |
| 35 | Institution Verification | | Proof of institution legitimacy | Pending→Verified→Rejected |
| 36 | Institution Contact | | Official point of contact | Added→Active→Removed |
| 37 | Region | | Administrative region reference | Defined→Active |
| 38 | Locality | | City/town reference | Defined→Active |

### 5.4 Competitions (19)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 39 | Competition ★ | ✔ | Time-bounded creative event | Draft→Published→Open→Submission→Judging→Results→Archived |
| 40 | Competition Series | | Grouping of recurring competitions | Created→Active→Archived |
| 41 | Nomination ★ | | Category of creative work | Defined→Active→Closed→Archived |
| 42 | Age Group | | Age band for fair comparison | Defined→Active→Retired |
| 43 | Round ★ | | Judging stage | Planned→Open→Scoring→Closed |
| 44 | Judging Criterion ★ | | Weighted evaluation dimension | Defined→Active→Retired |
| 45 | Criteria Set ★ | | Weighted rubric for scoring | Draft→Published→Frozen→Archived |
| 46 | Competition Schedule | | Key dates/timeline | Draft→Published→Updated |
| 47 | Competition Rule | | Governing rule/regulation text | Draft→Published→Superseded |
| 48 | Eligibility Rule | | Who may enter | Defined→Active→Retired |
| 49 | Organizer Assignment | | Assigns organizer to a competition | Assigned→Active→Revoked |
| 50 | Competition Status History | | Trace of status transitions | Recorded (immutable) |
| 51 | Competition Template | | Reusable competition blueprint | Created→Active→Archived |
| 52 | Prize ★ | | Reward offered | Defined→Active→Allocated→Archived |
| 53 | Prize Tier | | Level/grade of prize | Defined→Active→Retired |
| 54 | Fee Schedule | | Participation fee definition | Draft→Active→Retired |
| 55 | Discount Policy | | Rules for reduced fees | Draft→Active→Retired |
| 56 | Competition Announcement | | Public communication about a competition | Draft→Published→Archived |
| 57 | Competition Sponsor | | Sponsoring party | Added→Active→Ended |

### 5.5 Applications (12)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 58 | Application ★ | ✔ | Request to enter a nomination | Draft→Submitted→Under Review→Accepted→Withdrawn/Rejected |
| 59 | Application Form | | Structured entry questionnaire | Draft→Published→Archived |
| 60 | Application Form Field | | Single question on a form | Defined→Active→Retired |
| 61 | Application Answer | | Response to a form field | Entered→Submitted→Locked |
| 62 | Application Attachment | | Supporting document for an entry | Attached→Validated→Removed |
| 63 | Application Status History | | Trace of application states | Recorded (immutable) |
| 64 | Consent Snapshot ★ | | Frozen consent proof for an entry | Captured→Immutable |
| 65 | Eligibility Check ★ | | Eligibility decision for an entry | Pending→Passed/Failed |
| 66 | Application Fee | | Fee incurred by an entry | Assessed→Paid/Waived |
| 67 | Waitlist Entry | | Placeholder when capacity is full | Queued→Promoted/Expired |
| 68 | Application Withdrawal | | Record of an entry being withdrawn | Requested→Confirmed |
| 69 | Application Review Note | | Organizer note on an entry | Added→Active→Archived |

### 5.6 Performances (11)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 70 | Performance ★ | ✔ | The judged creative work | Draft→Uploaded→Scanning→Under Moderation→Accepted→Withdrawn→Archived |
| 71 | Media Asset ★ | | A single uploaded media file | Registered→Uploaded→Scanned→Available→Quarantined/Deleted |
| 72 | Media Variant | | Derived rendition (thumbnail/transcode) | Generated→Available→Purged |
| 73 | Media Metadata | | Descriptive/technical media facts | Captured→Available |
| 74 | Performance Version | | A revision of a work | Created→Active→Superseded |
| 75 | Performance Status History | | Trace of performance states | Recorded (immutable) |
| 76 | Content Moderation Flag ★ | | Moderation concern on content | Raised→Under Review→Upheld/Dismissed |
| 77 | Antivirus Scan Result | | Safety scan outcome for media | Pending→Clean/Infected |
| 78 | Performance Attachment | | Supplementary file for a work | Attached→Validated→Removed |
| 79 | Performance Tag | | Descriptive label | Added→Active→Removed |
| 80 | Live Performance Slot | | Scheduled live/stage appearance | Scheduled→Confirmed→Completed/Cancelled |

### 5.7 Judging (14)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 81 | Jury Member ★ | | Evaluator of performances | Invited→Confirmed→Active→Recused→Retired |
| 82 | Jury Panel | ✔ | Group of jury for a scope | Formed→Active→Dissolved |
| 83 | Panel Membership | | Jury member's place on a panel | Added→Active→Removed |
| 84 | Judge Assignment ★ | | Work allocated to a judge | Assigned→In Progress→Completed→Voided |
| 85 | Scorecard ★ | ✔ | A judge's full evaluation of a work | Opened→In Progress→Submitted→Locked |
| 86 | Criterion Score ★ | | Score against one criterion | Entered→Submitted→Locked |
| 87 | Judge Comment | | Qualitative feedback | Drafted→Submitted→Locked |
| 88 | Conflict of Interest Declaration ★ | | Disclosed potential bias | Declared→Reviewed→Accepted/Cleared |
| 89 | Recusal | | Removal of a judge from a work | Initiated→Effective→Closed |
| 90 | Scoring Session | | A judge's working period | Opened→Active→Closed |
| 91 | Scoring Window | | Time frame in which scoring is allowed | Scheduled→Open→Closed |
| 92 | Deliberation Note | | Panel discussion record | Added→Finalized |
| 93 | Score Aggregation ★ | | Combined standing of a performance | Pending→Computed→Finalized |
| 94 | Tie-Break Decision | | Resolution of equal scores | Raised→Decided→Recorded |

### 5.8 Results (13)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 95 | Result ★ | ✔ | Official outcome for a participant | Draft→Under Review→Published→Disputed→Corrected→Archived |
| 96 | Ranking ★ | | Ordered standings in a cohort | Draft→Finalized→Published→Superseded |
| 97 | Ranking Entry | | One position within a ranking | Computed→Finalized |
| 98 | Award | | Recognition granted for a result | Determined→Granted→Revoked |
| 99 | Diploma ★ | | Certificate of achievement | Requested→Generated→Issued→Revoked/Reissued |
| 100 | Certificate | | Certificate of participation | Requested→Generated→Issued |
| 101 | Prize Allocation | | Assignment of a prize to a winner | Proposed→Confirmed→Delivered |
| 102 | Result Publication | | Act of making results public | Scheduled→Published→Retracted |
| 103 | Result Snapshot | | Immutable copy of published results | Captured→Immutable |
| 104 | Result Dispute ★ | | Challenge to a result | Raised→Under Review→Resolved→Closed |
| 105 | Dispute Resolution | | Decision on a dispute | Drafted→Decided→Applied |
| 106 | Honorable Mention | | Non-ranking recognition | Determined→Granted |
| 107 | Leaderboard | | Public ranked display | Generated→Published→Superseded |

### 5.9 Finance (16)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 108 | Billing Account | ✔ | Financial identity of a payer | Created→Active→Suspended→Closed |
| 109 | Order ★ | ✔ | Purchase intent | Created→Pending Payment→Paid→Refunded→Cancelled |
| 110 | Invoice ★ | | Formal statement of amounts | Draft→Issued→Paid→Void |
| 111 | Invoice Line Item | | One billed element | Added→Finalized |
| 112 | Fee | | A charge (e.g., participation) | Defined→Assessed→Settled |
| 113 | Payment ★ | | Money received against an order | Initiated→Authorized→Captured→Failed/Refunded |
| 114 | Payment Transaction | | Provider-level money movement | Initiated→Succeeded/Failed |
| 115 | Refund | | Return of money | Requested→Approved→Processed |
| 116 | Discount Code | | Redeemable price reduction | Created→Active→Expired |
| 117 | Coupon Redemption | | Use of a discount code | Applied→Confirmed→Reversed |
| 118 | Pricing Plan | | Tiered offering for orgs/institutions | Draft→Active→Retired |
| 119 | Subscription | | Recurring plan enrollment | Started→Active→Cancelled→Expired |
| 120 | Payment Method | | Stored means of payment (tokenized) | Added→Active→Removed |
| 121 | Tax Rate | | Applicable tax definition | Defined→Active→Retired |
| 122 | Receipt | | Proof of payment | Generated→Issued |
| 123 | Payout | | Disbursement to an organizer (future) | Scheduled→Processed→Settled |

### 5.10 Notifications (12)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 124 | Notification ★ | ✔ | Intent to inform a user | Created→Queued→Sent→Delivered→Failed/Read |
| 125 | Notification Template ★ | | Reusable localized message | Draft→Published→Deprecated |
| 126 | Notification Channel | | Delivery medium (email/in-app) | Enabled→Active→Disabled |
| 127 | Notification Preference ★ | | User contact choices | Default→Customized→Updated |
| 128 | Message | | Rendered content instance | Composed→Sent |
| 129 | Notification Delivery | | Attempt to deliver on a channel | Attempted→Delivered/Failed |
| 130 | Delivery Receipt | | Confirmation of delivery | Received→Recorded |
| 131 | Bounce Record | | Failed-delivery evidence | Recorded→Analyzed |
| 132 | Reminder | | Scheduled prompt (e.g., deadline) | Scheduled→Sent→Cancelled |
| 133 | Digest | | Batched periodic summary | Assembled→Sent |
| 134 | Notification Topic | | Subject category of messages | Defined→Active→Retired |
| 135 | Subscription Preference | | Per-topic opt-in state | Set→Updated |

### 5.11 Analytics (10)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 136 | Analytics Event ★ | | Derived activity signal | Captured→Processed→Aggregated→Expired |
| 137 | Metric Definition | | Definition of a measurable | Defined→Active→Retired |
| 138 | KPI Snapshot ★ | | Point-in-time metric value | Computed→Published→Superseded |
| 139 | Report | | Structured analytical output | Generated→Published→Archived |
| 140 | Dashboard | | Visual collection of metrics | Created→Active→Archived |
| 141 | Funnel Definition | | Conversion-step definition | Defined→Active→Retired |
| 142 | Cohort | | Grouping for comparison | Defined→Computed→Archived |
| 143 | Aggregate View | | Pre-computed summary | Built→Refreshed→Retired |
| 144 | Data Export | | Extract for stakeholders | Requested→Generated→Delivered→Expired |
| 145 | Insight | | Interpreted finding | Drafted→Published→Archived |

### 5.12 Audit (10)

| # | Business Object | AR | Purpose | Lifecycle summary |
|---|-----------------|----|---------|-------------------|
| 146 | Audit Log Entry ★ | ✔ | Immutable record of an action | Recorded→Immutable→Purged (per policy) |
| 147 | Change Record | | Before/after of a data change | Recorded→Immutable |
| 148 | Access Log Entry | | Record of data access | Recorded→Immutable |
| 149 | Consent Audit Record | | History of consent changes | Recorded→Immutable |
| 150 | Data Subject Request ★ | | Personal-data rights request | Received→Verified→In Progress→Fulfilled→Closed |
| 151 | Data Erasure Record | | Evidence of erasure performed | Created→Confirmed |
| 152 | Retention Policy ★ | | Rules for data lifetime | Defined→Active→Revised→Retired |
| 153 | Security Event | | Security-relevant occurrence | Detected→Triaged→Resolved |
| 154 | Admin Action Record | | Privileged action performed | Recorded→Immutable |
| 155 | Legal Hold | | Suspension of erasure | Placed→Active→Lifted |

**Catalog total: 155 business objects** across 12 domains (within the 100–150 target band's intent; the model deliberately errs toward completeness and can be pruned during technical realization).

---

## 6. Relationship Matrix

### 6.1 Core End-to-End Flow (participant → recognition)

```
Guardian
   ↓ grants
Consent
   ↓ authorizes
Participant
   ↓ submits
Application
   ↓ enters
Competition (Nomination · Age Group · Round)
   ↓ produces
Performance
   ↓ evaluated by
Judge Assignment
   ↓ captured in
Scorecard → Criterion Score
   ↓ aggregated into
Score Aggregation
   ↓ ordered into
Ranking → Result
   ↓ recognized by
Award → Diploma / Certificate
```

### 6.2 Supporting Flows

**Institutional participation**
```
Institution → Institution Administrator → Teacher Assignment → Teacher
    → Class Group → Participant Group Membership → Participant → Application …
```

**Financial settlement (paid competitions)**
```
Application → Application Fee → Order → Invoice → Payment → Receipt
    (Discount Code → Coupon Redemption may reduce Order total)
    (Payment → Refund on withdrawal/cancellation)
Application acceptance is gated on Order = Paid.
```

**Communication**
```
Domain event (e.g., Result Published) → Notification → (Notification Preference filter)
    → Message → Notification Delivery → Delivery Receipt / Bounce Record
```

**Observation (cross-cutting)**
```
Every state-changing action in every domain
    → Audit Log Entry / Change Record / Access Log Entry
Analytics: domain events → Analytics Event → KPI Snapshot → Dashboard / Report
```

### 6.3 Key Cardinalities (business-level)

| From | Relationship | To | Cardinality |
|------|--------------|----|-------------|
| Guardian | is responsible for | Participant | 1..* ↔ 1..* (via Guardian Relationship) |
| Participant | submits | Application | 1 → 0..* |
| Application | enters | Competition Nomination | * → 1 |
| Application | yields | Performance | 1 → 1..* |
| Competition | has | Nomination | 1 → 1..* |
| Competition | has | Round | 1 → 1..* |
| Nomination | scored by | Criteria Set | * → 1 |
| Performance | assigned to | Jury Member | 1..* ↔ 1..* (via Judge Assignment) |
| Judge Assignment | produces | Scorecard | 1 → 1 |
| Scorecard | contains | Criterion Score | 1 → 1..* |
| Performance | aggregated into | Score Aggregation | 1..* → 1 |
| Score Aggregation | ordered into | Ranking Entry | 1 → 1 |
| Result | recognized by | Diploma | 1 → 0..1 |
| Institution | groups | Participant | 1 → 0..* (via membership) |
| Order | settled by | Payment | 1 → 0..* |
| User Account | receives | Notification | 1 → 0..* |
| Any object | recorded in | Audit Log Entry | 1 → 0..* |

---

## 7. Aggregate Roots

Aggregate roots own a **consistency boundary**: internal objects are created, changed, and read through the root, and invariants hold at the root's boundary. Cross-aggregate references are by identity only (ARCH-001 §9.2, §13.4).

| Domain | Aggregate Root | Owns (inside the boundary) | Key invariant enforced at the root |
|--------|----------------|----------------------------|------------------------------------|
| Identity | **User Account** | Credentials, Sessions, MFA Enrollments, Role Assignments | Verified email + MFA-for-privileged before sensitive actions |
| Identity | **Consent** | Consent grant + version history | Purpose-limited, active consent required for minor participation |
| Participants | **Participant** | Participant Profile, memberships, portfolio links | Verified guardian/institution + consent before Active |
| Institutions | **Institution** | Profile, Class Groups, Administrators, Teacher Assignments | Verified institution required for bulk/analytics; tenancy scope |
| Competitions | **Competition** | Nominations, Age Groups, Rounds, Criteria Sets, Schedule, Rules, Prizes | Ordered, time-gated lifecycle; structure frozen after results |
| Applications | **Application** | Answers, Attachments, Consent Snapshot, Eligibility Check, Fee | No submit without consent; no accept without eligibility (+ payment if paid) |
| Performances | **Performance** | Media Assets, Variants, Versions, Moderation Flags, Scan Results | Not judged until scanned-clean & moderation-cleared; pseudonymized to jury |
| Judging | **Jury Panel** | Panel Memberships | Panel scope bounds assignments |
| Judging | **Scorecard** | Criterion Scores, Judge Comments | Complete rubric scored; locked & immutable after window close |
| Judging | **Score Aggregation** | Aggregated value + contributing set | Only valid, non-recused, locked scorecards contribute |
| Results | **Result** | Award, Diploma/Certificate, Prize Allocation links | Published only after judging finalized; immutable except governed correction |
| Results | **Ranking** | Ranking Entries | Ties resolved before finalization |
| Finance | **Billing Account** | Payment Methods, Subscriptions | Single financial identity per payer |
| Finance | **Order** | Invoice Line Items, Fees, Payment link | Total = line items − discounts, one currency; paid before entitlement |
| Notifications | **Notification** | Deliveries, Receipts | Sent only on permitted channels |
| Analytics | (none — derived read models; no transactional aggregate) | Aggregate Views, KPI Snapshots | Reproducible from source events; no re-identification |
| Audit | **Audit Log Entry** | — (atomic, append-only) | Immutable; never updated/deleted outside retention policy |

> **Note.** Analytics has no transactional aggregate root by design: it is a derived, read-only projection domain (ARCH-001 §31 mentions future CQRS read models). Its objects are consistency-free reflections of source-of-truth events.

---

## 8. Value Objects

Value objects are defined by their attributes, are **immutable**, and carry no independent identity. They are shared across domains via the shared kernel (ARCH-001 §13.4, §14).

| Value Object | Meaning | Business-level composition | Notable rules |
|--------------|---------|----------------------------|---------------|
| **Money** | A precise monetary amount | Amount (minor units) + currency | Never a float; arithmetic only within one currency (ARCH-001 §9.4) |
| **Address** | A postal/physical location | Country, region, locality, street, postal code | Region/locality align with Institution references |
| **PhoneNumber** | A contact telephone number | Country code + national number | Stored normalized; validated for format |
| **Email** | An electronic mail address | Local part + domain | Normalized lowercase; one verified email per active account |
| **PersonName** | A person's name | Given name, family name, optional patronymic | Patronymic supported for ru-RU |
| **AgeGroup** | A competing age band | Lower bound, upper bound (inclusive), label | Derived from date of birth vs. competition reference date |
| **DateRange** | A bounded period | Start, end | Start ≤ end; used for schedules, windows |
| **ScoreValue** | A single evaluation value | Numeric value + scale (min/max) | Must fall within the criterion's scale |
| **Weight** | A criterion's relative importance | Proportion/percentage | Weights in a criteria set sum to a defined whole |
| **FileMetadata** | Facts about a stored file | Media type, size, checksum, original name | Checksum verifies integrity; type/size gate acceptance |
| **VerificationCode** | An authenticity token for artifacts | Opaque unique code | Unique per diploma/certificate |
| **Locale** | A language/region setting | Language + region tag | Primary ru-RU; i18n-ready (ARCH-001 §8.6) |
| **ConsentGrant** | The content of a consent decision | Purpose, text version, granted/expiry dates | Immutable once captured into a snapshot |
| **ContactChannel** | A way to reach a user | Channel type + address | Respected against Notification Preference |
| **Percentage** | A proportional quantity | Value 0–100 | Used for weights, completion rates |
| **Duration** | A length of time | Quantity + unit | Used for scoring windows, retention periods |

---

## 9. Entity Identity Strategy

This section states **which objects require globally unique, stable identifiers** and why — at the business level. **No implementation** (no key types, no formats) is prescribed here; realization follows ARCH-001 §9.4 (UUIDs for externally referenced entities).

### 9.1 Principles

- **Aggregate roots and externally referenced entities** require **globally unique, stable, non-guessable** business identifiers, because they are referenced across domain boundaries (by identity, not by reach-in) and often exposed to users or external systems.
- **Objects internal to an aggregate** may be identified **within their aggregate** (locally) since they are only ever accessed through their root.
- **Human-facing reference numbers** (e.g., invoice number, diploma verification code) are distinct from internal identity and are business artifacts in their own right.
- **Privacy:** identifiers of minors and their works must be **non-enumerable** to prevent scraping/inference (ARCH-001 §21.6).

### 9.2 Objects Requiring Global Identity

| Object | Why global identity is required |
|--------|---------------------------------|
| User Account | Referenced by every domain; external SSO linkage (future) |
| Participant | Referenced by applications, performances, results; DSAR subject |
| Guardian, Teacher | Cross-domain actors and relationship anchors |
| Institution | Tenancy anchor; referenced across participants, finance, analytics |
| Competition | Referenced by applications, judging, results, finance, notifications |
| Nomination, Round, Criteria Set | Referenced by applications, judging, results |
| Application | Cross-domain intake anchor (finance, performances, audit) |
| Performance | Referenced by judging and results; pseudonymized external exposure |
| Media Asset | Referenced by external object storage |
| Jury Member, Jury Panel, Judge Assignment, Scorecard | Fairness-critical, audited references |
| Result, Ranking, Diploma, Certificate | Publicly referenced; verification codes |
| Billing Account, Order, Invoice, Payment | Financial references; external provider linkage |
| Notification | Delivery tracking and audit correlation |
| Consent | Cross-domain, evidentiary, DSAR-relevant |
| Audit Log Entry, Data Subject Request | Compliance evidence; must be uniquely citable |

### 9.3 Objects with Local (In-Aggregate) Identity

Examples: Criterion Score and Judge Comment (within a Scorecard), Invoice Line Item (within an Invoice/Order), Ranking Entry (within a Ranking), Application Answer (within an Application), Media Variant and Media Metadata (within a Media Asset), Panel Membership (within a Jury Panel). These are never referenced from outside their aggregate root.

### 9.4 Special Reference Numbers (business artifacts, not internal identity)

| Artifact | Purpose | Rule |
|----------|---------|------|
| Invoice Number | Human/legal reference for billing | Sequential, unique, non-reusable |
| Diploma/Certificate Verification Code | Public authenticity check | Globally unique, non-guessable |
| Application Reference | Support/communication reference | Unique per application |

---

## 10. Naming Standards

Consistent naming is what makes the ubiquitous language real. These standards apply to **business-level artifacts** in documentation and design; technical naming (code, schema) follows ARCH-001 §26 and derives from these.

### 10.1 Domains

- Named as a **singular, capitalized business noun** describing an area of responsibility: *Identity, Participants, Competitions, Judging, Finance, Audit*.
- Use the **business term**, not a technical one (*Finance*, not *BillingService*).
- Where a domain maps to an ARCH-001 bounded context under a different label, the mapping is stated explicitly (§3.1).
- One domain = one clear owner and one area of the ubiquitous language.

### 10.2 Business Objects

- Named as **singular, PascalCase business nouns**: *Participant, Competition, Scorecard, Result, Diploma*.
- Prefer **domain language over technical language**: *Performance* (not *SubmissionRecord*), *Consent* (not *ConsentFlag*).
- Avoid abbreviations except where they are the accepted business term (*KPI*, *MFA*).
- Names must be **unique within the model**; if two domains need a similar concept, qualify it (*Consent* vs. *Consent Snapshot*).
- Association objects that record a link are named for the relationship: *Guardian Relationship, Teacher Assignment, Coupon Redemption*.
- History/trace objects use the suffix **History** or **Record**: *Competition Status History, Change Record*.
- Snapshot/immutable-copy objects use the suffix **Snapshot**: *Consent Snapshot, Result Snapshot*.

### 10.3 Attributes

- Named as **lowercase business phrases** in documentation (e.g., *date of birth*, *award level*), realized technically in `snake_case` per ARCH-001 §26 / §9.
- Describe the **business meaning**, not the storage form (*participation fee*, not *fee_int_cents* — the *Money* value object carries the precision rule).
- Dates/times are named by their event: *submitted date, published date, granted date, expiry date*.
- Status/state attributes are named **status** or **state** and take values from a **documented, closed set** matching the object's lifecycle.
- Boolean concepts are phrased as a positive assertion: *MFA-enabled, verified, published*.
- References to other objects are named for the **role**, not the type: *submitter, responsible teacher, granting guardian*.

### 10.4 Events

Domain events (ARCH-001 §4.8) are the integration currency between domains. Business-level naming:

- Named as **past-tense facts** in PascalCase: *ApplicationSubmitted, ConsentGranted, PerformanceAccepted, ScoringCompleted, ResultPublished, PaymentCaptured, DiplomaIssued*.
- The name states **what happened**, in business terms, from the perspective of the owning domain.
- One event = one meaningful business state change; events are **immutable facts** and never named as commands (*use ResultPublished, not PublishResult*).
- Event names are stable and versioned additively; a changed meaning gets a new event, not a redefinition.
- Each event carries the **identity** of the affected aggregate root (§9) and the business time it occurred.

**Illustrative event vocabulary by domain**

| Domain | Representative Events |
|--------|-----------------------|
| Identity | AccountRegistered, EmailVerified, ConsentGranted, ConsentWithdrawn, RoleAssigned |
| Participants | ParticipantCreated, ParticipantVerified, GuardianLinked, ParticipantArchived |
| Institutions | InstitutionVerified, TeacherAssigned, ClassGroupCreated |
| Competitions | CompetitionPublished, CompetitionOpened, SubmissionWindowClosed, JudgingStarted |
| Applications | ApplicationSubmitted, ApplicationAccepted, ApplicationWithdrawn |
| Performances | PerformanceUploaded, MediaScanned, PerformanceAccepted, ContentFlagged |
| Judging | AssignmentCreated, ScorecardSubmitted, ConflictDeclared, ScoringCompleted |
| Results | RankingFinalized, ResultPublished, DiplomaIssued, ResultDisputed |
| Finance | OrderCreated, PaymentCaptured, RefundProcessed, InvoiceIssued |
| Notifications | NotificationQueued, NotificationDelivered, NotificationFailed |
| Analytics | MetricComputed, ExportGenerated |
| Audit | ActionRecorded, DataSubjectRequestReceived, DataErased |

---

*End of document — DATA-001 Business Data Model v1.0. This document is business-language only; all technical realization defers to [ARCH-001](../architecture/ARCH-001-vt-platform-architecture.md).*
