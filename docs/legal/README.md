# Legal Documentation

Published legal documents and the internal notes about them. The documents themselves are public and carry no internal commentary — everything an engineer or the operator needs to know about them lives here instead.

## Documents

| ID | Title | Published at | Rendered by |
|----|-------|--------------|-------------|
| LEGAL-001 | [Политика в отношении обработки персональных данных](LEGAL-001-privacy-policy.md) | `/privacy-policy` | `frontend/src/pages/legal/privacy-policy.tsx` |
| LEGAL-002 | [Политика использования файлов cookie](LEGAL-002-cookies-policy.md) | `/cookies` | `frontend/src/pages/legal/cookies-policy.tsx` |

Both are approved by the operator and **in force since 6 August 2026** (v1.0). Governing law: **Law of the Republic of Belarus No. 99-З of 7 May 2021**; supervisory authority: НЦЗПД. Written in Russian — unlike the rest of `docs/` — because they are the text published to users and read by the regulator, in the formal register and section order НЦЗПД recommends for such a policy.

## Two editorial rules for these documents

1. **Formal legal register.** Third person, «Оператор» and «субъект персональных данных», not «мы» and «вы». Terms carry the meaning art. 1 of the Law gives them.
2. **The documents describe what is processed, not what is not.** No inventories of data the platform never collects, no assurances about absent practices. Where a clause has to bound the scope of something, it does so affirmatively — «предоставляются исключительно сведения, перечисленные в пункте 4.2», never «иные сведения не предоставляются».

## Operator details, as published

| Fact | Value | Where it lives |
|------|-------|----------------|
| Operator | Скорик Илья Андреевич, плательщик налога на профессиональный доход, УНП AE9395951 | LEGAL-001 header and §2.1; `legal-facts.ts` |
| Postal address for written requests | 220047, г. Минск, ул. Нестерова, 70-127 | LEGAL-001 header and §2.2; `legal-facts.ts` |
| Email for personal-data requests | support@vzlettalantov.by | both documents; `SUPPORT_EMAIL` |
| Effective date, v1.0 | 6 August 2026 | both headers; `effectiveDate` in `legal-facts.ts` |

Changing any of these changes the published documents. `legal-facts.ts` is the single source for the pages; the Markdown carries the same values in prose.

## Still open

- [ ] **Retention periods** (LEGAL-001 §11) — the values were proposed from how festivals actually run plus the statutory minimum for payment records, and are now published. Make the platform's deletion jobs match them; where they cannot be met, amend §11 rather than let the text be wrong.
- [ ] **Processor details** — LEGAL-001 §9.1 names the hosting, mail and object-storage provider as one row. If they should be named individually (НЦЗПД's recommendations allow either), supply the names and УНП and issue a new revision.
- [ ] **Analytics counter ids and CSP** — see below.

## Analytics and the cookie banner

The operator intends to connect **Yandex Metrica and Google Analytics**. Both documents are written for that, which drives three constraints:

1. **The counters must not load before consent.** `frontend/src/features/cookie-consent` owns the decision; read it with `useAnalyticsConsent()` and mount a counter only when it returns `true`. Loading a counter unconditionally would make LEGAL-002 §2.4 false.
2. **Cross-border transfer is consent-based.** LEGAL-001 §10 states that transfer abroad happens only through these counters and only on consent (art. 9 of the Law). Adding any other third-party service that receives visitor data means updating LEGAL-001 §9, §10 and LEGAL-002 §4 first.
3. **CSP must allow the counter hosts.** The production Nginx sends a `Content-Security-Policy`; `mc.yandex.ru` and `www.googletagmanager.com` need to be allowed there, or the scripts will be blocked with no obvious cause.

The documents describe the counters in the present tense. Publishing them before the counters are live is safe — the text then discloses more than actually happens, and consent is collected either way — but the reverse is not: never enable a counter the published text does not describe.

## Working rules

1. **Markdown is the source; the page is the rendering.** Edit the document here first, then mirror it into the page component. Clause numbering matches between the two, because consent records and support answers cite clauses by number.
2. **A revision's text is append-only.** `legal-facts.ts` holds the version identifier the platform stores in `consent_version` (`apps.identity` `UserConsentModel`), so a stored consent traces back to the exact text in force. New wording gets a new version — never an in-place edit of a version users have already accepted.
3. **These changes in code invalidate the text**: cookies or token lifetimes, browser-storage keys, third-party embeds or scripts, retention jobs, where data is stored, the set of public endpoints. Re-read LEGAL-001 §5–§11 and LEGAL-002 §3–§5 before merging any of them. `frontend/src/pages/legal/legal.test.tsx` and `frontend/src/features/cookie-consent/cookie-consent.test.tsx` catch part of this automatically.
4. **Legal review belongs on every revision.** v1.0 was drafted against the platform's actual behaviour and the text of the law and approved by the operator; a lawyer's or DPO's reading of it, and of anything that follows, is still worth having.

## Known inconsistency elsewhere in the docs

`ARCH-001 §21.6` and `DATA-001 §4.12` cite **152-ФЗ** (Russian Federation law). The operator is registered in Belarus, so 99-З applies. Those references should be corrected; the documents here are authoritative on which law governs.
