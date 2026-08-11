# Legal Documentation

Published legal documents and the internal notes about them. The documents themselves are public and carry no internal commentary — everything an engineer or the operator needs to know about them lives here instead.

## Documents

| ID | Title | Published at | Rendered by | Revision in force |
|----|-------|--------------|-------------|-------------------|
| LEGAL-001 | [Политика в отношении обработки персональных данных](LEGAL-001-privacy-policy.md) | `/privacy-policy` | `frontend/src/pages/legal/privacy-policy.tsx` | 1.1, since 11 Aug 2026 |
| LEGAL-002 | [Политика использования файлов cookie](LEGAL-002-cookies-policy.md) | `/cookies` | `frontend/src/pages/legal/cookies-policy.tsx` | 1.0, since 6 Aug 2026 |
| LEGAL-003 | [Пользовательское соглашение](LEGAL-003-terms-of-service.md) | `/terms` | `frontend/src/pages/legal/terms-of-service.tsx` | 1.0, since 11 Aug 2026 |

All three are approved by the operator. Governing law: **Law of the Republic of Belarus No. 99-З of 7 May 2021** for the personal-data documents, the **Civil Code of the Republic of Belarus** for the agreement; supervisory authority: НЦЗПД. Written in Russian — unlike the rest of `docs/` — because they are the text published to users and read by the regulator, in the formal register and section order НЦЗПД recommends for such a policy.

## What the account's data rests on

This is the one thing to understand before touching registration or the consent catalogue.

**The account is not held on consent.** LEGAL-003 is a real contract, entered when the person ticks the box at registration, and the data the account is made of — name, email, phone, institution, session records — is processed **to perform that contract**, which art. 6 of the Law makes a legal basis in its own right (LEGAL-001 §4.1 rows 1, 2, 8 and §4.4). So registration asks for an *acceptance*, not a consent. Two consequences worth stating plainly:

- **Do not re-add a required consent to registration.** A consent that must be given for the service to work is not freely given (§13.1), and it hands the person a withdrawal button that could only ever be refused. `frontend/src/shared/consents/definitions.ts` marks each entry `kind: "consent" | "acceptance"`, and `consents.test.ts` asserts that no required entry is a consent.
- **The newsletter is untouched and stays a consent.** It is not needed to perform the agreement, so nothing but consent can carry it, and refusing it costs nothing (§4.3). Same for the participant, teacher, distribution and cookie consents — all of those are about somebody else's data or about a purpose outside the contract.

Revision 1.1 of LEGAL-001 is the revision that made this change; §16.5 of the published text says so, and says that nothing else about the processing changed. Before 1.1, registration also collected a `data_processing` consent. **That code is deliberately still in `apps.identity` `ConsentType` and in the DB check constraint** — rows granted under it exist and are evidence; the catalogue simply no longer offers it, so it is not shown in the cabinet and is never granted again. Do not write a migration that removes the value.

### Consent-text versions and document revisions

`consent_version` on a stored row is the version of the *text the person saw*, which is not the same number as the document's revision:

| Journal `consentType` | Version stored | Text / document |
|---|---|---|
| `terms_of_service` | `2.0` | The agreement checkbox wording accepting LEGAL-003 rev. 1.0. Version `1.0` of this code predates LEGAL-003: it accepted «условия использования» that were never published as a document, so the two had to be distinguishable. |
| `marketing` | `1.0` | Unchanged newsletter consent text. |
| `minor_data_processing`, `participant_data_processing`, `work_publication` | `2.0` | Reworded when the pseudonym sentence was removed — see below. |
| `third_party_data_processing`, `personal_data`, `distribution`, `media`, `regulations` | `1.0` | Unchanged. |

A new revision of either document means a new version here, never an edit in place.

**Registration writes one row, not two.** The box accepts the agreement and states nothing about having read the policies, because LEGAL-003 §1.5 already makes both of them part of it — accepting the agreement accepts the set, which LEGAL-001 §13.7 says in the published text. There is deliberately no `privacy_policy` acknowledgement row: a second statement would need a version kept in step with the policy's own revisions, and recording an acknowledgement the wording never asked for would be recording something the person did not say. Which policy revision applied to a given acceptance is answered by the acceptance date plus the retained revision history (§16.2), not by a second row.

## The pseudonym that was promised and never applied

Revision 1.0 of LEGAL-001 §6.6 said a creative work reaches a jury member «с указанием псевдонима Участника, без фамилии, имени и иных сведений, позволяющих установить личность», and three consent texts repeated it. Nothing of the kind happens: `apps.judging` has domain and application layers but **no API at all**, so no work has ever been handed to a jury under a pseudonym or under a name. Revision 1.1 replaces §6.6 with the scope actually intended for evaluation, adds the jury to §6.5 and §9.1 (§6.6 was the reason they were absent), and records the correction in §16.6.

This is not the same case as the analytics counters, and the distinction is the one to carry forward:

- **Disclosing processing that is planned but not yet live is safe.** The text then says more happens than does, consent is collected either way, and going live breaks nothing. That is why both policies describe Yandex Metrica and Google Analytics in the present tense before the counters exist.
- **Promising a safeguard that is not implemented is the opposite.** It tells a parent their child's work is de-identified when nothing de-identifies it. There is no version of going live that makes such a clause become true, and it is exactly the kind of statement НЦЗПД would read as a commitment.

An alias **is** stored for every participant — `display_alias` on `ParticipantRegistryModel`, unique among active rows, with `PseudonymizationPolicy` guarding against the real name leaking into it — which is what makes the sentence easy to re-add in good faith. It stays out until the handover it describes exists in code. When the jury flow is built: amend §6.6 first, bump the three consent texts again, and honour §16.6, which promises subjects will be informed **before** evaluation by a jury begins. `consents.test.ts` fails on the word `псевдоним` in any consent text, so the promise cannot creep back silently.

## Two editorial rules for these documents

1. **Formal legal register.** Third person, «Оператор» and «субъект персональных данных», not «мы» and «вы». Terms carry the meaning art. 1 of the Law gives them.
2. **The documents describe what is processed, not what is not.** No inventories of data the platform never collects, no assurances about absent practices. Where a clause has to bound the scope of something, it does so affirmatively — «предоставляются исключительно сведения, перечисленные в пункте 4.2», never «иные сведения не предоставляются». The corollary is the one above: a clause that reads as a *protective guarantee* must describe a mechanism that exists.

## Operator details, as published

| Fact | Value | Where it lives |
|------|-------|----------------|
| Operator | Скорик Илья Андреевич, плательщик налога на профессиональный доход, УНП AE9395951 | LEGAL-001 header and §2.1, LEGAL-003 header and §1.1; `legal-facts.ts` |
| Postal address for written requests | 220047, г. Минск, ул. Нестерова, 70-127 | LEGAL-001 header and §2.2, LEGAL-003 §16.2; `legal-facts.ts` |
| Email for personal-data requests | support@vzlettalantov.by | all three documents; `SUPPORT_EMAIL` |
| Effective dates | LEGAL-002 v1.0: 6 Aug 2026 · LEGAL-001 v1.1 and LEGAL-003 v1.0: 11 Aug 2026 | document headers; `effectiveDate` in `legal-facts.ts` |

Changing any of these changes the published documents. `legal-facts.ts` is the single source for the pages; the Markdown carries the same values in prose.

## Still open

- [ ] **Civil Code citations in LEGAL-003** — §1.3 cites art. 398 (договор присоединения) of the Civil Code of the Republic of Belarus. The concepts are right for a contract of adhesion accepted by ticking a box; the article number is worth confirming against the current text of the Code before the agreement is relied on in a dispute. Nothing else in LEGAL-003 cites the Code by number.
- [ ] **LEGAL-003 promises the platform has to keep** — three clauses commit to behaviour that is not enforced by code today: §6.2 (notifying users of planned downtime longer than an hour), §14.4 (at least seven days to fix a problem before access is suspended, with the reason given), §15.2 (a new revision posted at least ten days before it takes effect, announced in the cabinet and by email). Build these, or amend the clauses rather than let the text be wrong.
- [ ] **Retention periods** (LEGAL-001 §11) — the values were proposed from how festivals actually run plus the statutory minimum for payment records, and are now published. Make the platform's deletion jobs match them; where they cannot be met, amend §11 rather than let the text be wrong. Note that the account row now says «до прекращения Пользовательского соглашения», so the deletion job is triggered by account deletion, not by a withdrawal of consent.
- [ ] **Processor details** — LEGAL-001 §9.1 names the hosting, mail and object-storage provider as one row. If they should be named individually (НЦЗПД's recommendations allow either), supply the names and УНП and issue a new revision.
- [ ] **Analytics counter ids and CSP** — see below.

## Analytics and the cookie banner

The operator intends to connect **Yandex Metrica and Google Analytics**. Both documents are written for that, which drives three constraints:

1. **The counters must not load before consent.** `frontend/src/features/cookie-consent` owns the decision; read it with `useAnalyticsConsent()` and mount a counter only when it returns `true`. Loading a counter unconditionally would make LEGAL-002 §2.4 false.
2. **Cross-border transfer is consent-based.** LEGAL-001 §10 states that transfer abroad happens only through these counters and only on consent (art. 9 of the Law). Adding any other third-party service that receives visitor data means updating LEGAL-001 §9, §10 and LEGAL-002 §4 first.
3. **CSP must allow the counter hosts.** The production Nginx sends a `Content-Security-Policy`; `mc.yandex.ru` and `www.googletagmanager.com` need to be allowed there, or the scripts will be blocked with no obvious cause.

The documents describe the counters in the present tense. Publishing them before the counters are live is safe — the text then discloses more than actually happens, and consent is collected either way — but the reverse is not: never enable a counter the published text does not describe.

## Working rules

1. **Markdown is the source; the page is the rendering.** Edit the document here first, then mirror it into the page component. Clause numbering matches between the two, because consent records and support answers cite clauses by number. Clauses are appended, not inserted: LEGAL-001 §4.4 and §13.7 sit at the end of their sections precisely so §13.3 keeps meaning what the consent catalogue says it means.
2. **A revision's text is append-only.** `legal-facts.ts` holds each document's revision, and the catalogue holds the version stored in `consent_version` (`apps.identity` `UserConsentModel`), so a stored row traces back to the exact text in force — see the mapping table above. New wording gets a new version — never an in-place edit of a version users have already accepted.
3. **These changes in code invalidate the text**: cookies or token lifetimes, browser-storage keys, third-party embeds or scripts, retention jobs, where data is stored, the set of public endpoints. Re-read LEGAL-001 §5–§11 and LEGAL-002 §3–§5 before merging any of them. `frontend/src/pages/legal/legal.test.tsx`, `frontend/src/shared/consents/consents.test.ts` and `frontend/src/features/cookie-consent/cookie-consent.test.tsx` catch part of this automatically.
4. **The three documents have to agree.** LEGAL-001 §4.4 names LEGAL-003 as the legal basis and LEGAL-003 §11.2 names art. 6 of the Law as its ground; each is the other's justification. Changing what registration collects, or what the account is used for, means re-reading both before the code.
5. **Legal review belongs on every revision.** These were drafted against the platform's actual behaviour and the text of the law and approved by the operator; a lawyer's or DPO's reading of them, and of anything that follows, is still worth having. LEGAL-003 is a contract rather than a disclosure, so it carries more of that risk than the policies do.

## Known inconsistency elsewhere in the docs

`ARCH-001 §21.6` and `DATA-001 §4.12` cite **152-ФЗ** (Russian Federation law). The operator is registered in Belarus, so 99-З applies. Those references should be corrected; the documents here are authoritative on which law governs.
