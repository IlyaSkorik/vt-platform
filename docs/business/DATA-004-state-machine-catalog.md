# DATA-004 — State Machine Catalog v1.0

**Project:** «Взлёт талантов» — цифровая экосистема для организации детских творческих фестивалей
**Document type:** State Machine Catalog (business language only)
**Status:** Draft for review (v1.0)
**Owner:** Enterprise Architecture Group
**Source of truth:** [ARCH-001](../architecture/ARCH-001-vt-platform-architecture.md) · [DATA-001 Business Data Model](DATA-001-business-data-model.md) · [DATA-002 Business Rules Catalog](DATA-002-business-rules-catalog.md) · [DATA-003 Domain Event Catalog](DATA-003-domain-event-catalog.md)
**Last updated:** 2026-07-05

> This document defines the **lifecycle state machines** of every major business object (aggregate root) on the VT Platform, in **business language only** — no implementation, no code, no storage detail. States and lifecycles are taken from [DATA-001 §4/§7](DATA-001-business-data-model.md#7-aggregate-roots); transitions reference the rules of [DATA-002](DATA-002-business-rules-catalog.md) and produce/consume the events of [DATA-003](DATA-003-domain-event-catalog.md). This catalogue must not contradict its sources.

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [How to Read a State Machine](#2-how-to-read-a-state-machine)
3. [Conventions](#3-conventions)
4. [State Machines by Aggregate Root](#4-state-machines-by-aggregate-root)
   - [Competition (CMP)](#41-competition-cmp) · [Application (APP)](#42-application-app) · [Participant (PRT)](#43-participant-prt) · [Performance (PRF)](#44-performance-prf) · [Judge Assignment (JDA)](#45-judge-assignment-jda) · [Score Sheet / Scorecard (SCR)](#46-score-sheet--scorecard-scr) · [Result (RES)](#47-result-res) · [Diploma (DIP)](#48-diploma-dip) · [Invoice (INV)](#49-invoice-inv) · [Payment (PAY)](#410-payment-pay) · [Notification (NTF)](#411-notification-ntf)
5. [State Transition Matrix](#5-state-transition-matrix)
6. [Invalid Transition Matrix](#6-invalid-transition-matrix)
7. [Cross-Aggregate State Dependencies](#7-cross-aggregate-state-dependencies)
8. [State Ownership Rules](#8-state-ownership-rules)
9. [Summary Statistics](#9-summary-statistics)

---

## 1. Purpose & Scope

### 1.1 Purpose

To make the **allowed lifecycle** of each aggregate root explicit, deterministic, and auditable: which states exist, who may move an object between them, under what conditions, which rules govern each move, and which events each move produces or consumes. State machines are where the platform's fairness, privacy, and financial-integrity rules become **enforceable sequencing** rather than prose.

### 1.2 Scope

- **In scope:** the lifecycle, states, transitions, entry/exit conditions, allowed actors, governing rules, and produced/consumed events for every major aggregate root; the state transition matrix; the invalid transition matrix; cross-aggregate state dependencies; and state ownership rules.
- **Out of scope:** implementation of state machines, storage of state, concurrency mechanisms, and UI. *How* a transition is executed is a technical concern (ARCH-001 §7.4); this document says *which transitions are legal and why*.

### 1.3 Aggregate Roots Covered

The eleven required major objects, each an aggregate root per [DATA-001 §7](DATA-001-business-data-model.md#7-aggregate-roots): **Competition, Application, Participant, Performance, Judge Assignment, Score Sheet (Scorecard), Result, Diploma, Invoice, Payment, Notification.** Other aggregate roots (Consent, Order, Institution, Jury Panel, Ranking, Billing Account) follow the same modeling discipline and are governed by the same [State Ownership Rules](#8-state-ownership-rules); they will be added in later revisions.

---

## 2. How to Read a State Machine

Each aggregate root is documented as:

- **Lifecycle** — a diagram of states and legal transitions.
- **States** — a table of every state with **entry conditions**, **exit conditions**, **allowed actors**, and whether it is **terminal**.
- **Transitions** — each with the ten-field template below.
- **Business Rules** — the DATA-002 rules that govern this object's lifecycle.
- **Produced / Consumed Events** — the DATA-003 events this object emits and reacts to.
- **Terminal States** — the states from which no further transition is allowed.

**Transition template (ten fields):** Transition ID · Source State · Target State · Trigger · Actor · Preconditions · Business Rules References · Produced Events · Failure Conditions · Rollback Strategy.

---

## 3. Conventions

- **Transition IDs:** `TRN-<OBJ>-<NNN>` where `<OBJ>` ∈ {CMP, APP, PRT, PRF, JDA, SCR, RES, DIP, INV, PAY, NTF}.
- **Actors:** business roles from [ARCH-001 §12.2](../architecture/ARCH-001-vt-platform-architecture.md#12-authorization-rbac) — Participant, Guardian, Teacher, Institution Admin, Jury, Organizer, Administrator — plus **System** (a scheduled/time- or event-driven transition with no human actor, e.g., a deadline passing) and **Payment Provider** (external, via anti-corruption boundary).
- **Rollback strategy** in a business model means the **compensating action** taken when a transition cannot complete or must be undone. Because a transition is atomic at its boundary (ARCH-001 §7.4), a *failed* transition leaves the object in its source state (no partial move); an *already-completed* transition that must be undone requires a **compensating transition** and, where an event was already published, a **compensating event** — never silent mutation.
- **Events already published are immutable facts** (DATA-003 §9.1); they are corrected by emitting a new compensating event, not by retracting the original.

---

## 4. State Machines by Aggregate Root

### 4.1 Competition (CMP)

**Owning domain:** Competitions. **Aggregate root:** Competition (owns nominations, age groups, rounds, criteria sets, schedule, prizes).

**Lifecycle**
```
Draft ─▶ Published ─▶ Open ─▶ Submission ─▶ Judging ─▶ Results ─▶ Archived
   │         │         │          │            │
   └─────────┴─────────┴──────────┴────────────┴──────────────▶ Cancelled
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Draft | Competition created | Structurally complete & schedule consistent | Organizer | No |
| Published | Passed publish validation | Open date reached | Organizer, System | No |
| Open | Application window opened | Application window ends | System | No |
| Submission | Performance submission window active | Submission window closes | System | No |
| Judging | Submission closed, criteria frozen, panels formed | Judging finalized | Organizer, System | No |
| Results | Judging finalized | Archival | Organizer, System | No |
| Archived | Results published & finalized | — | Organizer, System | **Yes** |
| Cancelled | Cancellation decision | — | Organizer, Administrator | **Yes** |

**Transitions**

**TRN-CMP-001 · Draft → Published**
- **Trigger:** Organizer publishes the competition.
- **Actor:** Organizer.
- **Preconditions:** ≥1 Nomination, ≥1 Age Group, valid Criteria Set per nomination/round; schedule dates consistent.
- **Business Rules:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [CMP-002](DATA-002-business-rules-catalog.md#rule-cmp-002), [CMP-003](DATA-002-business-rules-catalog.md#rule-cmp-003), [CMP-008](DATA-002-business-rules-catalog.md#rule-cmp-008).
- **Produced Events:** CompetitionPublished ([EVT-CMP-003](DATA-003-domain-event-catalog.md#evt-cmp-003)).
- **Failure Conditions:** Incomplete structure or inconsistent dates.
- **Rollback Strategy:** Guarded — validation failure leaves it in Draft (no state change).

**TRN-CMP-002 · Published → Open**
- **Trigger:** Schedule reaches the application open date.
- **Actor:** System.
- **Preconditions:** Competition published; open date reached.
- **Business Rules:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [CMP-003](DATA-002-business-rules-catalog.md#rule-cmp-003).
- **Produced Events:** CompetitionOpened ([EVT-CMP-004](DATA-003-domain-event-catalog.md#evt-cmp-004)).
- **Failure Conditions:** Date not yet reached.
- **Rollback Strategy:** None (time-driven, idempotent).

**TRN-CMP-003 · Open → Submission**
- **Trigger:** Application window ends / submission phase begins.
- **Actor:** System.
- **Preconditions:** Open window elapsed; accepted applications exist.
- **Business Rules:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001).
- **Produced Events:** *(phase change; no distinct integration event — surfaced within Competitions)*.
- **Failure Conditions:** Window still open.
- **Rollback Strategy:** None (time-driven).

**TRN-CMP-004 · Submission → Judging**
- **Trigger:** Submission window closes and judging begins.
- **Actor:** System (close), Organizer (start judging).
- **Preconditions:** Submission window closed; criteria set frozen; jury panels formed.
- **Business Rules:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [CMP-005](DATA-002-business-rules-catalog.md#rule-cmp-005), [JDG-003](DATA-002-business-rules-catalog.md#rule-jdg-003).
- **Produced Events:** SubmissionWindowClosed ([EVT-CMP-005](DATA-003-domain-event-catalog.md#evt-cmp-005)), CriteriaSetFrozen ([EVT-CMP-002](DATA-003-domain-event-catalog.md#evt-cmp-002)), JudgingStarted ([EVT-CMP-006](DATA-003-domain-event-catalog.md#evt-cmp-006)).
- **Failure Conditions:** Criteria not frozen or no panels.
- **Rollback Strategy:** Guarded — cannot enter Judging until preconditions met; structure freeze is irreversible except by governed correction.

**TRN-CMP-005 · Judging → Results**
- **Trigger:** Judging finalized (all aggregation complete).
- **Actor:** Organizer, System.
- **Preconditions:** Score aggregation finalized for all rounds.
- **Business Rules:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [RES-001](DATA-002-business-rules-catalog.md#rule-res-001).
- **Produced Events:** CompetitionResultsPhaseEntered ([EVT-CMP-007](DATA-003-domain-event-catalog.md#evt-cmp-007)).
- **Failure Conditions:** Aggregation incomplete.
- **Rollback Strategy:** Guarded; if a dispute later overturns outcomes, correction runs via Result's dispute path (not a state reversal here).

**TRN-CMP-006 · Results → Archived**
- **Trigger:** Organizer archives after results are published.
- **Actor:** Organizer, System.
- **Preconditions:** Results published and finalized.
- **Business Rules:** [CMP-006](DATA-002-business-rules-catalog.md#rule-cmp-006).
- **Produced Events:** CompetitionArchived ([EVT-CMP-008](DATA-003-domain-event-catalog.md#evt-cmp-008)).
- **Failure Conditions:** Unresolved disputes.
- **Rollback Strategy:** None (terminal); structure immutable.

**TRN-CMP-007 · {Draft|Published|Open|Submission|Judging} → Cancelled**
- **Trigger:** Organizer/Administrator cancels the competition.
- **Actor:** Organizer, Administrator.
- **Preconditions:** Competition not yet Archived.
- **Business Rules:** [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001), [FIN-004](DATA-002-business-rules-catalog.md#rule-fin-004).
- **Produced Events:** CompetitionCancelled ([EVT-CMP-009](DATA-003-domain-event-catalog.md#evt-cmp-009)).
- **Failure Conditions:** Already archived.
- **Rollback Strategy:** Compensating — applications voided and fees refunded (RefundProcessed); participants notified. Cancellation itself is terminal.

**Consumed Events:** ScoreAggregated ([EVT-JDG-007](DATA-003-domain-event-catalog.md#evt-jdg-007)) → informs Judging→Results; RankingFinalized ([EVT-RES-001](DATA-003-domain-event-catalog.md#evt-res-001)).
**Terminal States:** Archived, Cancelled.

---

### 4.2 Application (APP)

**Owning domain:** Applications. **Aggregate root:** Application (owns answers, attachments, consent snapshot, eligibility check, fee).

**Lifecycle**
```
Draft ─▶ Submitted ─▶ Under Review ─▶ Accepted
                          │    │
                          │    └──▶ Waitlisted ──▶ Accepted
                          └──▶ Rejected
Submitted/Under Review/Accepted ─▶ Withdrawn
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Draft | Application started | Submitted with valid consent | Guardian, Teacher | No |
| Submitted | Submitted with consent snapshot | Eligibility evaluated | Guardian, Teacher | No |
| Under Review | Eligibility being evaluated | Decision made | Organizer, System | No |
| Waitlisted | Eligible but no capacity | Capacity frees / window ends | System, Organizer | No |
| Accepted | Eligibility passed (+ payment if paid) | Withdrawal | Organizer, System | No* |
| Rejected | Eligibility failed / decision | — | Organizer, System | **Yes** |
| Withdrawn | Withdrawal confirmed | — | Guardian, Teacher, Organizer | **Yes** |

\* Accepted is not terminal: it may transition to Withdrawn.

**Transitions**

**TRN-APP-001 · Draft → Submitted**
- **Trigger:** Guardian/Teacher submits the application.
- **Actor:** Guardian, Teacher.
- **Preconditions:** Participant Active; active matching Consent captured as Consent Snapshot; competition Open.
- **Business Rules:** [APP-001](DATA-002-business-rules-catalog.md#rule-app-001), [APP-006](DATA-002-business-rules-catalog.md#rule-app-006), [PRT-002](DATA-002-business-rules-catalog.md#rule-prt-002).
- **Produced Events:** ApplicationSubmitted ([EVT-APP-001](DATA-003-domain-event-catalog.md#evt-app-001)).
- **Failure Conditions:** No active consent; competition not open; participant not active.
- **Rollback Strategy:** Guarded — stays in Draft if consent/eligibility gate fails.

**TRN-APP-002 · Submitted → Under Review**
- **Trigger:** Eligibility evaluation begins.
- **Actor:** System.
- **Preconditions:** Application submitted.
- **Business Rules:** [APP-002](DATA-002-business-rules-catalog.md#rule-app-002).
- **Produced Events:** EligibilityChecked ([EVT-APP-002](DATA-003-domain-event-catalog.md#evt-app-002)).
- **Failure Conditions:** Missing eligibility inputs.
- **Rollback Strategy:** None (automatic evaluation).

**TRN-APP-003 · Under Review → Accepted**
- **Trigger:** Eligibility passed (and payment captured if paid).
- **Actor:** Organizer, System.
- **Preconditions:** Eligibility pass; Order Paid or fee waived (paid competitions).
- **Business Rules:** [APP-002](DATA-002-business-rules-catalog.md#rule-app-002), [APP-003](DATA-002-business-rules-catalog.md#rule-app-003).
- **Produced Events:** ApplicationAccepted ([EVT-APP-003](DATA-003-domain-event-catalog.md#evt-app-003)).
- **Failure Conditions:** Eligibility fail; payment not captured.
- **Rollback Strategy:** Guarded — remains Under Review pending payment; routes to Rejected on eligibility fail.

**TRN-APP-004 · Under Review → Waitlisted**
- **Trigger:** Eligible but capacity full.
- **Actor:** System, Organizer.
- **Preconditions:** Eligibility pass; no capacity.
- **Business Rules:** [APP-007](DATA-002-business-rules-catalog.md#rule-app-007).
- **Produced Events:** ApplicationWaitlisted ([EVT-APP-004](DATA-003-domain-event-catalog.md#evt-app-004)).
- **Failure Conditions:** Capacity available (would accept instead).
- **Rollback Strategy:** None; queue position recorded.

**TRN-APP-005 · Waitlisted → Accepted**
- **Trigger:** Capacity frees; promotion in recorded order.
- **Actor:** System, Organizer.
- **Preconditions:** Capacity available; consent/payment still valid.
- **Business Rules:** [APP-007](DATA-002-business-rules-catalog.md#rule-app-007), [APP-003](DATA-002-business-rules-catalog.md#rule-app-003).
- **Produced Events:** ApplicationAccepted ([EVT-APP-003](DATA-003-domain-event-catalog.md#evt-app-003)).
- **Failure Conditions:** Consent lapsed / payment missing.
- **Rollback Strategy:** Guarded — remains Waitlisted if gates unmet.

**TRN-APP-006 · Under Review → Rejected**
- **Trigger:** Eligibility failed or organizer decision.
- **Actor:** Organizer, System.
- **Preconditions:** Eligibility fail or documented decision.
- **Business Rules:** [APP-002](DATA-002-business-rules-catalog.md#rule-app-002).
- **Produced Events:** ApplicationRejected ([EVT-APP-005](DATA-003-domain-event-catalog.md#evt-app-005)).
- **Failure Conditions:** None (terminal decision).
- **Rollback Strategy:** Compensating — any held fee refunded; applicant notified.

**TRN-APP-007 · {Submitted|Under Review|Accepted} → Withdrawn**
- **Trigger:** Guardian/Teacher withdraws (or organizer-approved late withdrawal).
- **Actor:** Guardian, Teacher, Organizer.
- **Preconditions:** Before withdrawal cutoff and not yet judged; else organizer approval.
- **Business Rules:** [APP-005](DATA-002-business-rules-catalog.md#rule-app-005), [CMP-005](DATA-002-business-rules-catalog.md#rule-cmp-005).
- **Produced Events:** ApplicationWithdrawn ([EVT-APP-006](DATA-003-domain-event-catalog.md#evt-app-006)).
- **Failure Conditions:** After scoring started without approval.
- **Rollback Strategy:** Compensating — associated Performances voided; refund per policy; audited.

**Consumed Events:** PaymentCaptured ([EVT-FIN-004](DATA-003-domain-event-catalog.md#evt-fin-004)) → enables Accepted; CompetitionCancelled ([EVT-CMP-009](DATA-003-domain-event-catalog.md#evt-cmp-009)) → forces Withdrawn.
**Terminal States:** Rejected, Withdrawn.

---

### 4.3 Participant (PRT)

**Owning domain:** Participants. **Aggregate root:** Participant.

**Lifecycle**
```
Created ─▶ Verified ─▶ Active ─▶ Archived ─▶ Erased
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Created | Created by guardian/teacher | Details verified | Guardian, Teacher | No |
| Verified | Required details verified | Guardianship + consent present | Guardian, Teacher, System | No |
| Active | Verified + guardianship + active consent | Archival | Guardian, Teacher | No |
| Archived | Deactivated / season ended | Erasure | Guardian, Teacher, Administrator | No |
| Erased | Erasure completed | — | System (DPO-authorized) | **Yes** |

**Transitions**

**TRN-PRT-001 · Created → Verified**
- **Trigger:** Participant details verified.
- **Actor:** Guardian, Teacher, System.
- **Preconditions:** Required minimized details present; valid date of birth.
- **Business Rules:** [PRT-002](DATA-002-business-rules-catalog.md#rule-prt-002).
- **Produced Events:** ParticipantVerified ([EVT-PRT-003](DATA-003-domain-event-catalog.md#evt-prt-003)).
- **Failure Conditions:** Missing/invalid details.
- **Rollback Strategy:** Guarded — remains Created.

**TRN-PRT-002 · Verified → Active**
- **Trigger:** Guardianship/authority and active matching consent established.
- **Actor:** Guardian, Teacher.
- **Preconditions:** Active Guardian Relationship or authorized Institution/Teacher link; active Consent.
- **Business Rules:** [PRT-001](DATA-002-business-rules-catalog.md#rule-prt-001), [IDN-005](DATA-002-business-rules-catalog.md#rule-idn-005).
- **Produced Events:** ParticipantActivated ([EVT-PRT-004](DATA-003-domain-event-catalog.md#evt-prt-004)).
- **Failure Conditions:** No verified guardianship or no consent.
- **Rollback Strategy:** Guarded — remains Verified until conditions met.

**TRN-PRT-003 · Active → Archived**
- **Trigger:** Archival action or season end.
- **Actor:** Guardian, Teacher, Administrator.
- **Preconditions:** No blocking active applications.
- **Business Rules:** [PRT-007](DATA-002-business-rules-catalog.md#rule-prt-007) (archival ≠ erasure).
- **Produced Events:** ParticipantArchived ([EVT-PRT-005](DATA-003-domain-event-catalog.md#evt-prt-005)).
- **Failure Conditions:** Active applications in progress.
- **Rollback Strategy:** Reactivation allowed (Archived → Active) subject to valid consent.

**TRN-PRT-004 · {Active|Archived} → Erased**
- **Trigger:** Approved erasure (DSAR or consent withdrawal).
- **Actor:** System (DPO-authorized).
- **Preconditions:** Verified DSAR or consent withdrawal; **no active Legal Hold**; financial/audit retained under lawful basis.
- **Business Rules:** [PRT-007](DATA-002-business-rules-catalog.md#rule-prt-007), [AUD-003](DATA-002-business-rules-catalog.md#rule-aud-003), [AUD-004](DATA-002-business-rules-catalog.md#rule-aud-004), [FIN-008](DATA-002-business-rules-catalog.md#rule-fin-008).
- **Produced Events:** ParticipantErasureRequested ([EVT-PRT-006](DATA-003-domain-event-catalog.md#evt-prt-006)) → DataErased ([EVT-AUD-003](DATA-003-domain-event-catalog.md#evt-aud-003)).
- **Failure Conditions:** Active Legal Hold suspends erasure.
- **Rollback Strategy:** None — Erased is terminal and irreversible; if a hold exists, the transition is deferred, not partially applied.

**Consumed Events:** ConsentGranted ([EVT-IDN-003](DATA-003-domain-event-catalog.md#evt-idn-003)) → enables Active; ConsentWithdrawn ([EVT-IDN-004](DATA-003-domain-event-catalog.md#evt-idn-004)) → drives erasure; LegalHoldPlaced ([EVT-AUD-004](DATA-003-domain-event-catalog.md#evt-aud-004)) → suspends erasure.
**Terminal States:** Erased.

---

### 4.4 Performance (PRF)

**Owning domain:** Performances. **Aggregate root:** Performance (owns media assets, variants, versions, moderation flags, scan results).

**Lifecycle**
```
Draft ─▶ Uploaded ─▶ Scanning ─▶ Under Moderation ─▶ Accepted ─▶ Archived
                        │              │
                        └──────────────┴──▶ Rejected
Accepted/Under Moderation ─▶ Withdrawn
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Draft | Performance created for accepted application | Media uploaded | Guardian, Teacher, Participant | No |
| Uploaded | Media attached, meets requirements | Scan begins | Guardian, Teacher | No |
| Scanning | Antivirus scan in progress | Scan result available | System | No |
| Under Moderation | Scan clean; moderation review | Moderation decision | System, Administrator | No |
| Accepted | Scan clean + moderation cleared + requirements met | Withdrawal / archival | System | No* |
| Rejected | Scan infected / moderation upheld / non-conforming | — | System, Administrator | **Yes** |
| Withdrawn | Parent application withdrawn | — | Guardian, Teacher | **Yes** |
| Archived | Competition archived | — | System | **Yes** |

\* Accepted may still move to Withdrawn (before judging) or Archived.

**Transitions**

**TRN-PRF-001 · Draft → Uploaded**
- **Trigger:** Submitter uploads media.
- **Actor:** Guardian, Teacher, Participant (supervised).
- **Preconditions:** Parent Application Accepted; media type/size meet nomination requirements.
- **Business Rules:** [PRF-003](DATA-002-business-rules-catalog.md#rule-prf-003), [PRF-004](DATA-002-business-rules-catalog.md#rule-prf-004).
- **Produced Events:** PerformanceUploaded ([EVT-PRF-001](DATA-003-domain-event-catalog.md#evt-prf-001)).
- **Failure Conditions:** Application not accepted; media non-conforming.
- **Rollback Strategy:** Guarded — stays Draft.

**TRN-PRF-002 · Uploaded → Scanning**
- **Trigger:** Media registered for safety scan.
- **Actor:** System.
- **Preconditions:** Media uploaded.
- **Business Rules:** [PRF-001](DATA-002-business-rules-catalog.md#rule-prf-001).
- **Produced Events:** *(scan initiation — internal)*.
- **Failure Conditions:** None.
- **Rollback Strategy:** None (automatic).

**TRN-PRF-003 · Scanning → Under Moderation**
- **Trigger:** Scan result = clean.
- **Actor:** System.
- **Preconditions:** Antivirus scan clean.
- **Business Rules:** [PRF-001](DATA-002-business-rules-catalog.md#rule-prf-001), [PRF-002](DATA-002-business-rules-catalog.md#rule-prf-002).
- **Produced Events:** MediaScanCompleted (clean) ([EVT-PRF-002](DATA-003-domain-event-catalog.md#evt-prf-002)).
- **Failure Conditions:** Scan infected → Rejected instead.
- **Rollback Strategy:** None (result-driven).

**TRN-PRF-004 · Under Moderation → Accepted**
- **Trigger:** Moderation cleared.
- **Actor:** System.
- **Preconditions:** Moderation cleared; requirements met.
- **Business Rules:** [PRF-001](DATA-002-business-rules-catalog.md#rule-prf-001), [PRF-005](DATA-002-business-rules-catalog.md#rule-prf-005).
- **Produced Events:** PerformanceModerationCleared ([EVT-PRF-003](DATA-003-domain-event-catalog.md#evt-prf-003)), PerformanceAccepted ([EVT-PRF-004](DATA-003-domain-event-catalog.md#evt-prf-004)).
- **Failure Conditions:** Moderation flag upheld → Rejected.
- **Rollback Strategy:** Guarded — pending review, remains Under Moderation.

**TRN-PRF-005 · {Scanning|Under Moderation} → Rejected**
- **Trigger:** Scan infected, moderation upheld (high severity), or non-conformance confirmed.
- **Actor:** System, Administrator.
- **Preconditions:** A blocking condition confirmed.
- **Business Rules:** [PRF-002](DATA-002-business-rules-catalog.md#rule-prf-002), [PRF-006](DATA-002-business-rules-catalog.md#rule-prf-006).
- **Produced Events:** PerformanceRejected ([EVT-PRF-005](DATA-003-domain-event-catalog.md#evt-prf-005)).
- **Failure Conditions:** None (terminal).
- **Rollback Strategy:** Compensating — submitter notified to replace (a new Performance/Version if time permits); infected media quarantined.

**TRN-PRF-006 · {Under Moderation|Accepted} → Withdrawn**
- **Trigger:** Parent application withdrawn before judging.
- **Actor:** Guardian, Teacher.
- **Preconditions:** Round not yet scoring the performance.
- **Business Rules:** [APP-005](DATA-002-business-rules-catalog.md#rule-app-005), [PRF-005](DATA-002-business-rules-catalog.md#rule-prf-005).
- **Produced Events:** *(follows ApplicationWithdrawn [EVT-APP-006](DATA-003-domain-event-catalog.md#evt-app-006))*.
- **Failure Conditions:** Already under scoring.
- **Rollback Strategy:** Compensating — excluded from judging pool.

**TRN-PRF-007 · Accepted → Archived**
- **Trigger:** Competition archived.
- **Actor:** System.
- **Preconditions:** Competition Archived.
- **Business Rules:** [CMP-006](DATA-002-business-rules-catalog.md#rule-cmp-006).
- **Produced Events:** *(follows CompetitionArchived [EVT-CMP-008](DATA-003-domain-event-catalog.md#evt-cmp-008))*.
- **Failure Conditions:** None.
- **Rollback Strategy:** None (terminal); retained per policy.

**Consumed Events:** ApplicationAccepted ([EVT-APP-003](DATA-003-domain-event-catalog.md#evt-app-003)) → enables Draft creation; ApplicationWithdrawn ([EVT-APP-006](DATA-003-domain-event-catalog.md#evt-app-006)) → Withdrawn; CompetitionArchived ([EVT-CMP-008](DATA-003-domain-event-catalog.md#evt-cmp-008)) → Archived.
**Terminal States:** Rejected, Withdrawn, Archived.

---

### 4.5 Judge Assignment (JDA)

**Owning domain:** Judging. **Aggregate root treatment:** the unit of judging work linking Jury Member ↔ Performance for a round.

**Lifecycle**
```
Assigned ─▶ In Progress ─▶ Completed
   │             │
   └─────────────┴──▶ Reassigned
   └─────────────┴──▶ Voided
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Assigned | Assignment created (no conflict) | Judge opens scorecard | Organizer, System | No |
| In Progress | Judge began scoring | Scorecard submitted | Jury | No |
| Completed | Scorecard submitted & locked | — | Jury, System | **Yes** |
| Reassigned | Assignment moved to another judge | — | Organizer | **Yes** |
| Voided | Conflict/recusal or performance removed | — | Organizer, System | **Yes** |

**Transitions**

**TRN-JDA-001 · (create) → Assigned**
- **Trigger:** Assignment created for a performance/round.
- **Actor:** Organizer, System.
- **Preconditions:** Judging started; Performance Accepted; **no conflict of interest** (judge is not the participant's teacher).
- **Business Rules:** [JDG-001](DATA-002-business-rules-catalog.md#rule-jdg-001), [JDG-002](DATA-002-business-rules-catalog.md#rule-jdg-002), [JDG-007](DATA-002-business-rules-catalog.md#rule-jdg-007).
- **Produced Events:** JudgeAssigned ([EVT-JDG-002](DATA-003-domain-event-catalog.md#evt-jdg-002)).
- **Failure Conditions:** Conflict exists; performance not accepted; round not open.
- **Rollback Strategy:** Guarded — assignment refused if conflict (own-student rule).

**TRN-JDA-002 · Assigned → In Progress**
- **Trigger:** Judge opens the scorecard.
- **Actor:** Jury.
- **Preconditions:** Scoring window open; assignment active.
- **Business Rules:** [JDG-002](DATA-002-business-rules-catalog.md#rule-jdg-002), [JDG-003](DATA-002-business-rules-catalog.md#rule-jdg-003).
- **Produced Events:** *(scorecard opened — see SCR)*.
- **Failure Conditions:** Window closed.
- **Rollback Strategy:** None.

**TRN-JDA-003 · In Progress → Completed**
- **Trigger:** Scorecard submitted and locked.
- **Actor:** Jury, System.
- **Preconditions:** Valid, complete scorecard submitted within window.
- **Business Rules:** [JDG-004](DATA-002-business-rules-catalog.md#rule-jdg-004), [JDG-008](DATA-002-business-rules-catalog.md#rule-jdg-008).
- **Produced Events:** ScorecardSubmitted ([EVT-JDG-005](DATA-003-domain-event-catalog.md#evt-jdg-005)).
- **Failure Conditions:** Incomplete/out-of-range scores.
- **Rollback Strategy:** Guarded — remains In Progress until a valid scorecard exists.

**TRN-JDA-004 · {Assigned|In Progress} → Reassigned**
- **Trigger:** Organizer reassigns to another judge (e.g., unavailability).
- **Actor:** Organizer.
- **Preconditions:** No completed, locked scorecard yet.
- **Business Rules:** [JDG-002](DATA-002-business-rules-catalog.md#rule-jdg-002).
- **Produced Events:** JudgeAssigned ([EVT-JDG-002](DATA-003-domain-event-catalog.md#evt-jdg-002)) *(for the new judge)*.
- **Failure Conditions:** Scorecard already locked.
- **Rollback Strategy:** Compensating — a fresh Assigned assignment is created for the replacement judge.

**TRN-JDA-005 · {Assigned|In Progress} → Voided**
- **Trigger:** Conflict declared/recusal, or performance rejected/withdrawn.
- **Actor:** Organizer, System.
- **Preconditions:** Accepted conflict, recusal, or removed performance.
- **Business Rules:** [JDG-001](DATA-002-business-rules-catalog.md#rule-jdg-001), [JDG-007](DATA-002-business-rules-catalog.md#rule-jdg-007), [JDG-011](DATA-002-business-rules-catalog.md#rule-jdg-011).
- **Produced Events:** JudgeRecused ([EVT-JDG-004](DATA-003-domain-event-catalog.md#evt-jdg-004)) *(when recusal-driven)*.
- **Failure Conditions:** None (integrity action).
- **Rollback Strategy:** Compensating — any scores voided and excluded from aggregation.

**Consumed Events:** JudgingStarted ([EVT-CMP-006](DATA-003-domain-event-catalog.md#evt-cmp-006)) → activation; ConflictDeclared ([EVT-JDG-003](DATA-003-domain-event-catalog.md#evt-jdg-003)) → Voided; PerformanceRejected ([EVT-PRF-005](DATA-003-domain-event-catalog.md#evt-prf-005)) → Voided.
**Terminal States:** Completed, Reassigned, Voided.

---

### 4.6 Score Sheet / Scorecard (SCR)

**Owning domain:** Judging. **Aggregate root:** Scorecard (a judge's full evaluation of one performance in one round; owns criterion scores and comments).

**Lifecycle**
```
Opened ─▶ In Progress ─▶ Submitted ─▶ Locked
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Opened | Judge opens scorecard for an assignment | Scoring begins | Jury | No |
| In Progress | Criterion scores being entered | All criteria scored | Jury | No |
| Submitted | Complete rubric scored, submitted | Window closes | Jury | No |
| Locked | Window closed / submission finalized | — | System | **Yes** |

**Transitions**

**TRN-SCR-001 · (open) → Opened**
- **Trigger:** Judge opens the scorecard for an active assignment.
- **Actor:** Jury.
- **Preconditions:** Active Judge Assignment; scoring window open; frozen criteria set.
- **Business Rules:** [JDG-002](DATA-002-business-rules-catalog.md#rule-jdg-002), [JDG-003](DATA-002-business-rules-catalog.md#rule-jdg-003), [CMP-005](DATA-002-business-rules-catalog.md#rule-cmp-005).
- **Produced Events:** *(internal — scorecard opened)*.
- **Failure Conditions:** Window closed; no assignment.
- **Rollback Strategy:** Guarded.

**TRN-SCR-002 · Opened → In Progress**
- **Trigger:** First criterion score entered.
- **Actor:** Jury.
- **Preconditions:** Criteria set frozen; scores within scale.
- **Business Rules:** [JDG-005](DATA-002-business-rules-catalog.md#rule-jdg-005).
- **Produced Events:** *(none — draft scoring)*.
- **Failure Conditions:** Out-of-range value rejected.
- **Rollback Strategy:** None (draft edits allowed while In Progress).

**TRN-SCR-003 · In Progress → Submitted**
- **Trigger:** Judge submits a complete scorecard.
- **Actor:** Jury.
- **Preconditions:** Every criterion scored; all values in range; within window.
- **Business Rules:** [JDG-003](DATA-002-business-rules-catalog.md#rule-jdg-003), [JDG-004](DATA-002-business-rules-catalog.md#rule-jdg-004), [JDG-005](DATA-002-business-rules-catalog.md#rule-jdg-005).
- **Produced Events:** ScorecardSubmitted ([EVT-JDG-005](DATA-003-domain-event-catalog.md#evt-jdg-005)).
- **Failure Conditions:** Incomplete rubric; late submission.
- **Rollback Strategy:** Guarded — remains In Progress if invalid/late.

**TRN-SCR-004 · Submitted → Locked**
- **Trigger:** Scoring window closes / submission finalized.
- **Actor:** System.
- **Preconditions:** Scorecard submitted.
- **Business Rules:** [JDG-008](DATA-002-business-rules-catalog.md#rule-jdg-008), [AUD-001](DATA-002-business-rules-catalog.md#rule-aud-001).
- **Produced Events:** ScoringWindowClosed ([EVT-JDG-006](DATA-003-domain-event-catalog.md#evt-jdg-006)) *(at round level)*; ActionRecorded ([EVT-AUD-001](DATA-003-domain-event-catalog.md#evt-aud-001)).
- **Failure Conditions:** None.
- **Rollback Strategy:** None — Locked is terminal and immutable; corrections require a governed, audited correction (not a state reversal).

**Consumed Events:** JudgeAssigned ([EVT-JDG-002](DATA-003-domain-event-catalog.md#evt-jdg-002)); JudgeRecused ([EVT-JDG-004](DATA-003-domain-event-catalog.md#evt-jdg-004)) → voids the scorecard's contribution.
**Terminal States:** Locked.

---

### 4.7 Result (RES)

**Owning domain:** Results. **Aggregate root:** Result (the official outcome for a participant/performance in a competition).

**Lifecycle**
```
Draft ─▶ Under Review ─▶ Published ─▶ Archived
                            │
                            └──▶ Disputed ──▶ Corrected ──▶ Published
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Draft | Derived from finalized aggregation | Review complete | Organizer, System | No |
| Under Review | Result reviewed before publication | Publication decision | Organizer | No |
| Published | Judging finalized; ranking final | Dispute or archival | Organizer, System | No* |
| Disputed | A dispute raised on a published result | Dispute resolved | Organizer, Administrator | No |
| Corrected | Dispute upheld; result corrected | Republication | Organizer, Administrator | No |
| Archived | Competition archived; result final | — | System | **Yes** |

\* Published is non-terminal (may be Disputed or Archived).

**Transitions**

**TRN-RES-001 · Draft → Under Review**
- **Trigger:** Result prepared from finalized ranking.
- **Actor:** Organizer, System.
- **Preconditions:** Ranking finalized.
- **Business Rules:** [RES-003](DATA-002-business-rules-catalog.md#rule-res-003).
- **Produced Events:** RankingFinalized ([EVT-RES-001](DATA-003-domain-event-catalog.md#evt-res-001)).
- **Failure Conditions:** Aggregation/ranking not final.
- **Rollback Strategy:** Guarded.

**TRN-RES-002 · Under Review → Published**
- **Trigger:** Organizer publishes results.
- **Actor:** Organizer.
- **Preconditions:** Judging finalized; ranking final; privacy checks applied.
- **Business Rules:** [RES-001](DATA-002-business-rules-catalog.md#rule-res-001), [RES-002](DATA-002-business-rules-catalog.md#rule-res-002), [RES-006](DATA-002-business-rules-catalog.md#rule-res-006).
- **Produced Events:** ResultPublished ([EVT-RES-002](DATA-003-domain-event-catalog.md#evt-res-002)).
- **Failure Conditions:** Judging not finalized.
- **Rollback Strategy:** Guarded — publication withheld; once published, a Result Snapshot is captured (immutable).

**TRN-RES-003 · Published → Disputed**
- **Trigger:** A dispute is raised within the dispute window.
- **Actor:** Guardian, Teacher, Organizer, Administrator.
- **Preconditions:** Result published; within dispute window.
- **Business Rules:** [RES-002](DATA-002-business-rules-catalog.md#rule-res-002), [RES-007](DATA-002-business-rules-catalog.md#rule-res-007).
- **Produced Events:** ResultDisputed ([EVT-RES-005](DATA-003-domain-event-catalog.md#evt-res-005)).
- **Failure Conditions:** Outside dispute window.
- **Rollback Strategy:** None — the published result stands publicly until a resolution changes it.

**TRN-RES-004 · Disputed → Corrected**
- **Trigger:** Dispute upheld; governed correction applied.
- **Actor:** Organizer, Administrator.
- **Preconditions:** Dispute reviewed and upheld.
- **Business Rules:** [RES-007](DATA-002-business-rules-catalog.md#rule-res-007), [RES-002](DATA-002-business-rules-catalog.md#rule-res-002).
- **Produced Events:** DisputeResolved (upheld) ([EVT-RES-006](DATA-003-domain-event-catalog.md#evt-res-006)).
- **Failure Conditions:** Dispute rejected → returns to Published.
- **Rollback Strategy:** Compensating — affected Diplomas revoked and reissued.

**TRN-RES-005 · Corrected → Published**
- **Trigger:** Corrected result republished.
- **Actor:** Organizer.
- **Preconditions:** Correction finalized.
- **Business Rules:** [RES-002](DATA-002-business-rules-catalog.md#rule-res-002).
- **Produced Events:** ResultPublished ([EVT-RES-002](DATA-003-domain-event-catalog.md#evt-res-002)) *(corrected)*.
- **Failure Conditions:** Correction incomplete.
- **Rollback Strategy:** Guarded.

**TRN-RES-006 · Disputed → Published**
- **Trigger:** Dispute rejected (result confirmed).
- **Actor:** Organizer, Administrator.
- **Preconditions:** Dispute reviewed and rejected.
- **Business Rules:** [RES-007](DATA-002-business-rules-catalog.md#rule-res-007).
- **Produced Events:** DisputeResolved (rejected) ([EVT-RES-006](DATA-003-domain-event-catalog.md#evt-res-006)).
- **Failure Conditions:** None.
- **Rollback Strategy:** None (original result reaffirmed).

**TRN-RES-007 · Published → Archived**
- **Trigger:** Competition archived.
- **Actor:** System.
- **Preconditions:** No open disputes; competition Archived.
- **Business Rules:** [CMP-006](DATA-002-business-rules-catalog.md#rule-cmp-006).
- **Produced Events:** *(follows CompetitionArchived [EVT-CMP-008](DATA-003-domain-event-catalog.md#evt-cmp-008))*.
- **Failure Conditions:** Open dispute.
- **Rollback Strategy:** None (terminal).

**Consumed Events:** ScoreAggregated ([EVT-JDG-007](DATA-003-domain-event-catalog.md#evt-jdg-007)), TieBreakDecided ([EVT-JDG-008](DATA-003-domain-event-catalog.md#evt-jdg-008)) → Draft/Under Review readiness.
**Terminal States:** Archived.

---

### 4.8 Diploma (DIP)

**Owning domain:** Results. **Aggregate root:** Diploma / Certificate.

**Lifecycle**
```
Requested ─▶ Generated ─▶ Issued ─▶ Revoked ─▶ Reissued (─▶ Issued)
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Requested | Requested for a published result | Generation begins | Organizer, System | No |
| Generated | Artifact produced with verification code | Delivered/issued | System | No |
| Issued | Delivered to participant/guardian | Revocation (if needed) | System | No* |
| Revoked | Underlying result corrected/invalidated | Reissuance | Organizer, Administrator | No |
| Reissued | Corrected artifact produced | Becomes the Issued artifact | System | **Yes**† |

\* Issued is the normal end state; †Reissued resolves to a new Issued artifact and the corrected one is terminal for the cycle.

**Transitions**

**TRN-DIP-001 · Requested → Generated**
- **Trigger:** Diploma generation after result publication.
- **Actor:** System.
- **Preconditions:** Result Published.
- **Business Rules:** [RES-004](DATA-002-business-rules-catalog.md#rule-res-004), [RES-005](DATA-002-business-rules-catalog.md#rule-res-005).
- **Produced Events:** DiplomaGenerated ([EVT-RES-003](DATA-003-domain-event-catalog.md#evt-res-003)).
- **Failure Conditions:** Result not published.
- **Rollback Strategy:** Guarded — no artifact without a published result.

**TRN-DIP-002 · Generated → Issued**
- **Trigger:** Diploma delivered to the participant/guardian.
- **Actor:** System.
- **Preconditions:** Artifact generated with a unique verification code.
- **Business Rules:** [RES-005](DATA-002-business-rules-catalog.md#rule-res-005).
- **Produced Events:** *(delivery via NotificationQueued [EVT-NTF-001](DATA-003-domain-event-catalog.md#evt-ntf-001))*.
- **Failure Conditions:** Missing verification code.
- **Rollback Strategy:** None.

**TRN-DIP-003 · Issued → Revoked**
- **Trigger:** Underlying result corrected (dispute upheld) or invalidation.
- **Actor:** Organizer, Administrator.
- **Preconditions:** Result Corrected / invalidated.
- **Business Rules:** [RES-007](DATA-002-business-rules-catalog.md#rule-res-007).
- **Produced Events:** *(follows DisputeResolved [EVT-RES-006](DATA-003-domain-event-catalog.md#evt-res-006))*.
- **Failure Conditions:** No governing correction.
- **Rollback Strategy:** Compensating — verification code invalidated; holder notified.

**TRN-DIP-004 · Revoked → Reissued**
- **Trigger:** Corrected diploma generated.
- **Actor:** System.
- **Preconditions:** Corrected result published.
- **Business Rules:** [RES-005](DATA-002-business-rules-catalog.md#rule-res-005), [RES-007](DATA-002-business-rules-catalog.md#rule-res-007).
- **Produced Events:** DiplomaGenerated ([EVT-RES-003](DATA-003-domain-event-catalog.md#evt-res-003)) *(reissue)*.
- **Failure Conditions:** Corrected result absent.
- **Rollback Strategy:** Guarded.

**Consumed Events:** ResultPublished ([EVT-RES-002](DATA-003-domain-event-catalog.md#evt-res-002)) → Requested; DisputeResolved ([EVT-RES-006](DATA-003-domain-event-catalog.md#evt-res-006)) → Revoked/Reissued.
**Terminal States:** Issued (normal), Reissued (post-correction).

---

### 4.9 Invoice (INV)

**Owning domain:** Finance. **Aggregate root treatment:** the formal statement of amounts for an order.

**Lifecycle**
```
Draft ─▶ Issued ─▶ Paid
            │
            └──▶ Void
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Draft | Derived from an order | Issuance | System, Organizer | No |
| Issued | Formally issued (immutable) | Payment or void | System | No |
| Paid | Payment captured against it | — | System | **Yes** |
| Void | Cancelled/superseded | — | System, Administrator | **Yes** |

**Transitions**

**TRN-INV-001 · Draft → Issued**
- **Trigger:** Invoice issued for a finalized order.
- **Actor:** System, Organizer.
- **Preconditions:** Order finalized; single currency; totals correct.
- **Business Rules:** [FIN-003](DATA-002-business-rules-catalog.md#rule-fin-003), [FIN-005](DATA-002-business-rules-catalog.md#rule-fin-005), [FIN-001](DATA-002-business-rules-catalog.md#rule-fin-001).
- **Produced Events:** InvoiceIssued ([EVT-FIN-003](DATA-003-domain-event-catalog.md#evt-fin-003)).
- **Failure Conditions:** Inconsistent totals/currency.
- **Rollback Strategy:** Guarded — remains Draft on validation failure.

**TRN-INV-002 · Issued → Paid**
- **Trigger:** Payment captured for the order.
- **Actor:** System.
- **Preconditions:** Payment Captured for the exact amount.
- **Business Rules:** [FIN-001](DATA-002-business-rules-catalog.md#rule-fin-001), [FIN-006](DATA-002-business-rules-catalog.md#rule-fin-006).
- **Produced Events:** *(follows PaymentCaptured [EVT-FIN-004](DATA-003-domain-event-catalog.md#evt-fin-004))*.
- **Failure Conditions:** Payment not captured / amount mismatch.
- **Rollback Strategy:** None (a later refund is a separate Payment-side action, not an invoice reversal).

**TRN-INV-003 · Issued → Void**
- **Trigger:** Correction or cancellation (void + reissue).
- **Actor:** System, Administrator.
- **Preconditions:** Not yet Paid, or governed correction/cancellation.
- **Business Rules:** [FIN-005](DATA-002-business-rules-catalog.md#rule-fin-005), [FIN-004](DATA-002-business-rules-catalog.md#rule-fin-004).
- **Produced Events:** *(void recorded; a replacement Invoice may be issued)*.
- **Failure Conditions:** Already paid without refund path.
- **Rollback Strategy:** Compensating — a new corrected Invoice is issued (originals are immutable, never edited).

**Consumed Events:** OrderCreated ([EVT-FIN-001](DATA-003-domain-event-catalog.md#evt-fin-001)) → Draft; PaymentCaptured ([EVT-FIN-004](DATA-003-domain-event-catalog.md#evt-fin-004)) → Paid; CompetitionCancelled ([EVT-CMP-009](DATA-003-domain-event-catalog.md#evt-cmp-009)) → Void.
**Terminal States:** Paid, Void.

---

### 4.10 Payment (PAY)

**Owning domain:** Finance. **Aggregate root:** Payment (money received against an order; owns transactions and refunds).

**Lifecycle**
```
Initiated ─▶ Authorized ─▶ Captured ─▶ Refunded
    │            │
    └────────────┴──▶ Failed
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Initiated | Payment started for an order | Authorization result | Guardian, System | No |
| Authorized | Funds authorized by provider | Capture or failure | Payment Provider, System | No |
| Captured | Funds captured (settled) | Refund (if needed) | Payment Provider, System | No* |
| Refunded | Refund processed (full/partial) | — | System | **Yes**† |
| Failed | Authorization/capture failed | Retry (new Payment) | Payment Provider, System | **Yes** |

\* Captured is the normal success end state; †Refunded is terminal for the refunded portion.

**Transitions**

**TRN-PAY-001 · Initiated → Authorized**
- **Trigger:** Provider authorizes the payment.
- **Actor:** Payment Provider, System.
- **Preconditions:** Valid payment method; exact Money amount.
- **Business Rules:** [FIN-001](DATA-002-business-rules-catalog.md#rule-fin-001).
- **Produced Events:** *(authorization — internal)*.
- **Failure Conditions:** Declined authorization → Failed.
- **Rollback Strategy:** None (provider result-driven).

**TRN-PAY-002 · Authorized → Captured**
- **Trigger:** Provider captures the authorized funds.
- **Actor:** Payment Provider, System.
- **Preconditions:** Authorization valid.
- **Business Rules:** [FIN-001](DATA-002-business-rules-catalog.md#rule-fin-001), [FIN-006](DATA-002-business-rules-catalog.md#rule-fin-006), [APP-003](DATA-002-business-rules-catalog.md#rule-app-003).
- **Produced Events:** PaymentCaptured ([EVT-FIN-004](DATA-003-domain-event-catalog.md#evt-fin-004)).
- **Failure Conditions:** Capture fails → Failed.
- **Rollback Strategy:** Compensating — a captured payment is undone only via Refund, never by state reversal.

**TRN-PAY-003 · {Initiated|Authorized} → Failed**
- **Trigger:** Authorization or capture fails.
- **Actor:** Payment Provider, System.
- **Preconditions:** Provider failure signal.
- **Business Rules:** [FIN-006](DATA-002-business-rules-catalog.md#rule-fin-006), [APP-003](DATA-002-business-rules-catalog.md#rule-app-003).
- **Produced Events:** PaymentFailed ([EVT-FIN-005](DATA-003-domain-event-catalog.md#evt-fin-005)).
- **Failure Conditions:** None (records the failure).
- **Rollback Strategy:** Compensating — user prompted to retry via a **new** Payment; entitlement stays withheld.

**TRN-PAY-004 · Captured → Refunded**
- **Trigger:** Approved refund (withdrawal/cancellation/goodwill).
- **Actor:** System.
- **Preconditions:** Refund total ≤ captured amount.
- **Business Rules:** [FIN-004](DATA-002-business-rules-catalog.md#rule-fin-004), [FIN-006](DATA-002-business-rules-catalog.md#rule-fin-006).
- **Produced Events:** RefundProcessed ([EVT-FIN-006](DATA-003-domain-event-catalog.md#evt-fin-006)).
- **Failure Conditions:** Refund exceeds captured amount.
- **Rollback Strategy:** None — Refunded is terminal for the refunded portion; audited.

**Consumed Events:** OrderCreated ([EVT-FIN-001](DATA-003-domain-event-catalog.md#evt-fin-001)) → Initiated; ApplicationWithdrawn ([EVT-APP-006](DATA-003-domain-event-catalog.md#evt-app-006)), CompetitionCancelled ([EVT-CMP-009](DATA-003-domain-event-catalog.md#evt-cmp-009)) → Refunded.
**Terminal States:** Captured (success), Refunded, Failed.

---

### 4.11 Notification (NTF)

**Owning domain:** Notifications. **Aggregate root:** Notification.

**Lifecycle**
```
Created ─▶ Queued ─▶ Sent ─▶ Delivered ─▶ Read
                        │
                        └──▶ Failed
```

**States**

| State | Entry condition | Exit condition | Allowed actors | Terminal |
|-------|-----------------|----------------|----------------|----------|
| Created | A domain event requires a notice | Preference/consent check passes | System | No |
| Queued | Passed preference & locale checks | Dispatch | System | No |
| Sent | Dispatched on a channel | Delivery/failure signal | System | No |
| Delivered | Delivery confirmed | Read (optional) | System | No* |
| Read | Recipient opened the notice | — | Participant, Guardian, Teacher, etc. | **Yes** |
| Failed | Bounce/failure | Retry / alternative channel | System | **Yes**† |

\* Delivered is a normal end state; †Failed is terminal for that attempt (a new attempt is a new dispatch).

**Transitions**

**TRN-NTF-001 · Created → Queued**
- **Trigger:** Notice prepared from a source event.
- **Actor:** System.
- **Preconditions:** Recipient permitted on a channel; template exists in the primary locale (ru-RU).
- **Business Rules:** [NTF-001](DATA-002-business-rules-catalog.md#rule-ntf-001), [NTF-003](DATA-002-business-rules-catalog.md#rule-ntf-003), [NTF-005](DATA-002-business-rules-catalog.md#rule-ntf-005).
- **Produced Events:** NotificationQueued ([EVT-NTF-001](DATA-003-domain-event-catalog.md#evt-ntf-001)).
- **Failure Conditions:** Recipient opted out (non-critical); no primary-locale template.
- **Rollback Strategy:** Guarded — non-critical notices to opted-out channels are dropped (not queued).

**TRN-NTF-002 · Queued → Sent**
- **Trigger:** Dispatch to a channel (priority-ordered).
- **Actor:** System.
- **Preconditions:** Queued; content privacy-safe.
- **Business Rules:** [NTF-004](DATA-002-business-rules-catalog.md#rule-ntf-004), [NTF-005](DATA-002-business-rules-catalog.md#rule-ntf-005).
- **Produced Events:** NotificationSent ([EVT-NTF-002](DATA-003-domain-event-catalog.md#evt-ntf-002)).
- **Failure Conditions:** Channel unavailable.
- **Rollback Strategy:** None (re-queue on transient failure).

**TRN-NTF-003 · Sent → Delivered**
- **Trigger:** Delivery receipt received.
- **Actor:** System.
- **Preconditions:** Notification sent.
- **Business Rules:** [NTF-001](DATA-002-business-rules-catalog.md#rule-ntf-001).
- **Produced Events:** NotificationDelivered ([EVT-NTF-003](DATA-003-domain-event-catalog.md#evt-ntf-003)).
- **Failure Conditions:** No receipt within window.
- **Rollback Strategy:** None.

**TRN-NTF-004 · Sent → Failed**
- **Trigger:** Bounce/failure signal.
- **Actor:** System.
- **Preconditions:** Notification sent.
- **Business Rules:** [NTF-002](DATA-002-business-rules-catalog.md#rule-ntf-002).
- **Produced Events:** NotificationFailed ([EVT-NTF-004](DATA-003-domain-event-catalog.md#evt-ntf-004)).
- **Failure Conditions:** None (records failure).
- **Rollback Strategy:** Compensating — for **critical** notices, an alternative channel/new dispatch is attempted ([NTF-002](DATA-002-business-rules-catalog.md#rule-ntf-002)).

**TRN-NTF-005 · Delivered → Read**
- **Trigger:** Recipient opens the notice.
- **Actor:** Participant, Guardian, Teacher, Institution Admin, Jury, Organizer, Administrator.
- **Preconditions:** Delivered.
- **Business Rules:** —
- **Produced Events:** *(engagement signal → Analytics)*.
- **Failure Conditions:** None.
- **Rollback Strategy:** None (terminal).

**Consumed Events:** Nearly all milestone events (e.g., ConsentGranted, ApplicationAccepted, ResultPublished, PaymentCaptured) → Created.
**Terminal States:** Read, Failed.

---

## 5. State Transition Matrix

Legal transitions across all aggregate roots (`✔` = a defined transition exists; see the transition IDs above). Rows = source, columns = target, per object.

**Competition**

| From \ To | Published | Open | Submission | Judging | Results | Archived | Cancelled |
|-----------|-----------|------|------------|---------|---------|----------|-----------|
| Draft | ✔ 001 | | | | | | ✔ 007 |
| Published | | ✔ 002 | | | | | ✔ 007 |
| Open | | | ✔ 003 | | | | ✔ 007 |
| Submission | | | | ✔ 004 | | | ✔ 007 |
| Judging | | | | | ✔ 005 | | ✔ 007 |
| Results | | | | | | ✔ 006 | |

**Application**

| From \ To | Submitted | Under Review | Waitlisted | Accepted | Rejected | Withdrawn |
|-----------|-----------|--------------|------------|----------|----------|-----------|
| Draft | ✔ 001 | | | | | |
| Submitted | | ✔ 002 | | | | ✔ 007 |
| Under Review | | | ✔ 004 | ✔ 003 | ✔ 006 | ✔ 007 |
| Waitlisted | | | | ✔ 005 | | ✔ 007 |
| Accepted | | | | | | ✔ 007 |

**Participant**

| From \ To | Verified | Active | Archived | Erased |
|-----------|----------|--------|----------|--------|
| Created | ✔ 001 | | | |
| Verified | | ✔ 002 | | |
| Active | | | ✔ 003 | ✔ 004 |
| Archived | | ✔ (reactivate) | | ✔ 004 |

**Performance**

| From \ To | Uploaded | Scanning | Under Moderation | Accepted | Rejected | Withdrawn | Archived |
|-----------|----------|----------|------------------|----------|----------|-----------|----------|
| Draft | ✔ 001 | | | | | | |
| Uploaded | | ✔ 002 | | | | | |
| Scanning | | | ✔ 003 | | ✔ 005 | | |
| Under Moderation | | | | ✔ 004 | ✔ 005 | ✔ 006 | |
| Accepted | | | | | | ✔ 006 | ✔ 007 |

**Judge Assignment**

| From \ To | In Progress | Completed | Reassigned | Voided |
|-----------|-------------|-----------|------------|--------|
| Assigned | ✔ 002 | | ✔ 004 | ✔ 005 |
| In Progress | | ✔ 003 | ✔ 004 | ✔ 005 |

**Score Sheet / Scorecard**

| From \ To | In Progress | Submitted | Locked |
|-----------|-------------|-----------|--------|
| Opened | ✔ 002 | | |
| In Progress | | ✔ 003 | |
| Submitted | | | ✔ 004 |

**Result**

| From \ To | Under Review | Published | Disputed | Corrected | Archived |
|-----------|--------------|-----------|----------|-----------|----------|
| Draft | ✔ 001 | | | | |
| Under Review | | ✔ 002 | | | |
| Published | | | ✔ 003 | | ✔ 007 |
| Disputed | | ✔ 006 | | ✔ 004 | |
| Corrected | | ✔ 005 | | | |

**Diploma**

| From \ To | Generated | Issued | Revoked | Reissued |
|-----------|-----------|--------|---------|----------|
| Requested | ✔ 001 | | | |
| Generated | | ✔ 002 | | |
| Issued | | | ✔ 003 | |
| Revoked | | | | ✔ 004 |
| Reissued | | ✔ (→Issued) | | |

**Invoice**

| From \ To | Issued | Paid | Void |
|-----------|--------|------|------|
| Draft | ✔ 001 | | |
| Issued | | ✔ 002 | ✔ 003 |

**Payment**

| From \ To | Authorized | Captured | Refunded | Failed |
|-----------|------------|----------|----------|--------|
| Initiated | ✔ 001 | | | ✔ 003 |
| Authorized | | ✔ 002 | | ✔ 003 |
| Captured | | | ✔ 004 | |

**Notification**

| From \ To | Queued | Sent | Delivered | Read | Failed |
|-----------|--------|------|-----------|------|--------|
| Created | ✔ 001 | | | | |
| Queued | | ✔ 002 | | | |
| Sent | | | ✔ 003 | | ✔ 004 |
| Delivered | | | | ✔ 005 | |

---

## 6. Invalid Transition Matrix

Explicitly **forbidden** transitions and the rule that forbids them. These are the moves that fairness, privacy, or integrity require the platform to reject — not merely "undefined," but **prohibited**.

| # | Object | Invalid Transition | Why it is forbidden | Governing rule |
|---|--------|--------------------|--------------------|----------------|
| IVT-01 | Competition | Judging → Submission (reopen) | Cannot reopen submissions after judging begins | [CMP-005](DATA-002-business-rules-catalog.md#rule-cmp-005) |
| IVT-02 | Competition | Archived → any | Archived is terminal & immutable | [CMP-006](DATA-002-business-rules-catalog.md#rule-cmp-006) |
| IVT-03 | Competition | Draft → Judging (skip) | Lifecycle is strictly ordered; no skipping | [CMP-001](DATA-002-business-rules-catalog.md#rule-cmp-001) |
| IVT-04 | Application | Draft → Accepted (skip review) | Must pass eligibility (and payment if paid) | [APP-002](DATA-002-business-rules-catalog.md#rule-app-002), [APP-003](DATA-002-business-rules-catalog.md#rule-app-003) |
| IVT-05 | Application | Draft → Submitted **without consent** | No submission without active matching consent | [APP-001](DATA-002-business-rules-catalog.md#rule-app-001) |
| IVT-06 | Application | Rejected/Withdrawn → any | Terminal states | [APP-005](DATA-002-business-rules-catalog.md#rule-app-005) |
| IVT-07 | Participant | Created → Active (skip verify/consent) | Activation requires guardianship + consent | [PRT-001](DATA-002-business-rules-catalog.md#rule-prt-001) |
| IVT-08 | Participant | Erased → any | Erasure is terminal & irreversible | [PRT-007](DATA-002-business-rules-catalog.md#rule-prt-007) |
| IVT-09 | Participant | Active → Erased **under Legal Hold** | Legal hold suspends erasure | [AUD-004](DATA-002-business-rules-catalog.md#rule-aud-004) |
| IVT-10 | Performance | Scanning → Accepted (skip moderation) | Must be scan-clean **and** moderation-cleared | [PRF-001](DATA-002-business-rules-catalog.md#rule-prf-001) |
| IVT-11 | Performance | Uploaded → Accepted (skip scan) | No judging-readiness without a clean scan | [PRF-001](DATA-002-business-rules-catalog.md#rule-prf-001), [PRF-002](DATA-002-business-rules-catalog.md#rule-prf-002) |
| IVT-12 | Judge Assignment | (create) → Assigned **with own student** | Judge cannot be assigned their own student | [JDG-001](DATA-002-business-rules-catalog.md#rule-jdg-001) |
| IVT-13 | Score Sheet | Locked → In Progress / Submitted | Locked scorecards are immutable | [JDG-008](DATA-002-business-rules-catalog.md#rule-jdg-008) |
| IVT-14 | Score Sheet | In Progress → Submitted **incomplete** | Full rubric must be scored | [JDG-004](DATA-002-business-rules-catalog.md#rule-jdg-004) |
| IVT-15 | Score Sheet | any → Submitted **outside window** | No scoring outside the scoring window | [JDG-003](DATA-002-business-rules-catalog.md#rule-jdg-003) |
| IVT-16 | Result | Under Review → Published **before judging final** | Publication requires finalized judging | [RES-001](DATA-002-business-rules-catalog.md#rule-res-001) |
| IVT-17 | Result | Published → Published (edit in place) | Published results immutable except governed correction | [RES-002](DATA-002-business-rules-catalog.md#rule-res-002) |
| IVT-18 | Diploma | Requested → Generated **without published result** | No diploma without a published result | [RES-004](DATA-002-business-rules-catalog.md#rule-res-004) |
| IVT-19 | Invoice | Issued → Issued (edit in place) | Issued invoices immutable; void + reissue only | [FIN-005](DATA-002-business-rules-catalog.md#rule-fin-005) |
| IVT-20 | Payment | Captured → Failed | A captured payment cannot "fail"; only Refund undoes it | [FIN-004](DATA-002-business-rules-catalog.md#rule-fin-004) |
| IVT-21 | Payment | Refunded amount > Captured | Refund cannot exceed captured amount | [FIN-004](DATA-002-business-rules-catalog.md#rule-fin-004) |
| IVT-22 | Notification | Created → Sent **to opted-out channel** (non-critical) | Must respect preferences (except critical notices) | [NTF-001](DATA-002-business-rules-catalog.md#rule-ntf-001) |

---

## 7. Cross-Aggregate State Dependencies

A transition in one aggregate is frequently **gated by the state of another** aggregate. These dependencies are honored **by event and identity** across bounded contexts (ARCH-001 §7.4, §9.2) — never by one aggregate directly reading another's internals.

| Dependent transition | Requires state (in another aggregate) | Mediating event | Cross-domain invariant |
|----------------------|----------------------------------------|-----------------|------------------------|
| Participant `Verified → Active` | Consent = **Active** | ConsentGranted | XDR-01 (Consent-to-Participation) |
| Application `Draft → Submitted` | Participant = **Active**; Competition = **Open** | ParticipantActivated, CompetitionOpened | XDR-01 |
| Application `Under Review → Accepted` | Payment = **Captured** (paid); Eligibility = pass | PaymentCaptured | XDR-04 (Payment-gated entitlement) |
| Performance `Draft` (creation) | Application = **Accepted** | ApplicationAccepted | XDR-05 (Safety-before-judging precondition chain) |
| Judge Assignment `→ Assigned` | Performance = **Accepted**; Competition = **Judging** | PerformanceAccepted, JudgingStarted | XDR-05, XDR-02 |
| Score Sheet `Opened` | Judge Assignment = **Assigned/In Progress**; Round window **Open** | JudgeAssigned | XDR-03 (Judge-to-Result integrity) |
| Score Aggregation (feeds Result) | Score Sheets = **Locked**, non-recused | ScorecardSubmitted, JudgeRecused | XDR-03 |
| Result `Under Review → Published` | Competition = **Results**; Ranking **Finalized** | CompetitionResultsPhaseEntered, RankingFinalized | XDR-03 |
| Diploma `Requested → Generated` | Result = **Published** | ResultPublished | XDR-03 |
| Invoice `Issued → Paid` | Payment = **Captured** | PaymentCaptured | XDR-04 |
| Application `→ Withdrawn` (mass) | Competition = **Cancelled** | CompetitionCancelled | — |
| Payment `Captured → Refunded` | Application = **Withdrawn** or Competition = **Cancelled** | ApplicationWithdrawn, CompetitionCancelled | XDR-04 |
| Performance `→ Withdrawn` | Application = **Withdrawn** | ApplicationWithdrawn | — |
| Performance `→ Archived`; Result `→ Archived` | Competition = **Archived** | CompetitionArchived | XDR-10 (Structural freeze integrity) |
| Participant `→ Erased` | **No** active Legal Hold; DSAR verified | DataSubjectRequestReceived, LegalHoldPlaced | XDR-06 (Erasure with lawful exceptions) |
| Diploma `Issued → Revoked` | Result = **Corrected** (dispute upheld) | DisputeResolved | XDR-03 |

---

## 8. State Ownership Rules

These rules govern **who may change state**, and how state integrity is preserved across the platform.

1. **Single-writer ownership.** Each aggregate root's state is owned and mutated **only** by its owning domain (ARCH-001 §7.1, §9.2). No other domain may write another aggregate's state; it may only *react* to that aggregate's published events. (See the [Event Ownership Matrix](DATA-003-domain-event-catalog.md#8-event-ownership-matrix).)

2. **Transitions are guarded and atomic.** A transition occurs only when its preconditions and governing rules hold, and it completes wholly or not at all within the owning use case's transaction boundary (ARCH-001 §7.4). A failed transition leaves the aggregate in its source state.

3. **Cross-aggregate gating is by event, never by reach-in.** When a transition depends on another aggregate's state (§7), the dependency is satisfied by consuming that aggregate's **event** and holding a reference by **identity** — never by reading or writing the other aggregate's data directly (ARCH-001 §9.2).

4. **Terminal states are final.** No transition may leave a terminal state (Erased, Archived, Cancelled, Rejected, Withdrawn, Locked, Paid, Void, Refunded, Read, Failed, Issued/Reissued as applicable). Undoing an effect requires a **compensating transition on a new or related aggregate**, plus a compensating event — never mutation of the terminal object.

5. **Immutability where declared.** Locked Score Sheets ([JDG-008](DATA-002-business-rules-catalog.md#rule-jdg-008)), Issued Invoices ([FIN-005](DATA-002-business-rules-catalog.md#rule-fin-005)), Published Results ([RES-002](DATA-002-business-rules-catalog.md#rule-res-002)), and Consent Snapshots ([APP-006](DATA-002-business-rules-catalog.md#rule-app-006)) never change in place; corrections use governed void/reissue or correction workflows.

6. **Every state change is auditable.** Any fairness-, money-, access-, or privacy-significant transition produces an audit record ([RULE-AUD-001](DATA-002-business-rules-catalog.md#rule-aud-001); event ActionRecorded [EVT-AUD-001](DATA-003-domain-event-catalog.md#evt-aud-001)). Competition and Application also keep explicit status-history records (Competition Status History, Application Status History).

7. **System vs. human transitions are explicit.** Time-driven transitions (window open/close, scheduled phase changes) are performed by **System** and are idempotent; human transitions require an authorized actor per [ARCH-001 §12](../architecture/ARCH-001-vt-platform-architecture.md#12-authorization-rbac) and are scope-checked (e.g., only the assigned Organizer may publish a competition's results).

8. **Legal holds and lawful bases override routine lifecycle.** Erasure/terminal-cleanup transitions yield to an active Legal Hold ([AUD-004](DATA-002-business-rules-catalog.md#rule-aud-004)) and to independent lawful retention bases such as financial records ([FIN-008](DATA-002-business-rules-catalog.md#rule-fin-008)).

9. **Privacy-preserving state exposure.** A judge-facing view of a Performance's state must not reveal participant identity ([JDG-006](DATA-002-business-rules-catalog.md#rule-jdg-006)); state exposed publicly (e.g., Result) respects participant-privacy rules ([RES-006](DATA-002-business-rules-catalog.md#rule-res-006)).

---

## 9. Summary Statistics

### 9.1 Coverage

| Aggregate Root | States | Transitions | Terminal States |
|----------------|--------|-------------|-----------------|
| Competition | 8 | 7 | 2 (Archived, Cancelled) |
| Application | 7 | 7 | 2 (Rejected, Withdrawn) |
| Participant | 5 | 4 (+reactivate) | 1 (Erased) |
| Performance | 8 | 7 | 3 (Rejected, Withdrawn, Archived) |
| Judge Assignment | 5 | 5 | 3 (Completed, Reassigned, Voided) |
| Score Sheet / Scorecard | 4 | 4 | 1 (Locked) |
| Result | 6 | 7 | 1 (Archived) |
| Diploma | 5 | 4 | 2 (Issued, Reissued) |
| Invoice | 4 | 3 | 2 (Paid, Void) |
| Payment | 5 | 4 | 3 (Captured, Refunded, Failed) |
| Notification | 6 | 5 | 2 (Read, Failed) |
| **Total** | **58** | **57** | **22** |

### 9.2 Matrices

- **State Transition Matrix:** 11 per-object matrices (§5).
- **Invalid Transition Matrix:** 22 explicitly forbidden transitions (§6).
- **Cross-Aggregate State Dependencies:** 16 gating relationships (§7).
- **State Ownership Rules:** 9 governing rules (§8).

---

*End of document — DATA-004 State Machine Catalog v1.0. Business-language only; no implementation. Defers to [ARCH-001](../architecture/ARCH-001-vt-platform-architecture.md), [DATA-001](DATA-001-business-data-model.md), [DATA-002](DATA-002-business-rules-catalog.md), and [DATA-003](DATA-003-domain-event-catalog.md).*
