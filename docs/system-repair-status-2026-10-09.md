# Tathya repair status — 9 October 2026

The original 146 findings remain in system-error-audit-2026-10-09.md as a historical snapshot. This delivery repairs the core audit flow and evidence scoring; it does not certify every recommendation or implement the complete master blueprint.

## Implemented and verified

- Atomic bounded uploads, rollback and cleanup on failure, distinct stored file versions, duplicate-batch protection, asynchronous parser work, readable API errors and upload cancellation.
- Scoring methodology schema migration, safe failed-session recovery, deduplicated jobs and interrupted-job recovery.
- Real source-to-claim checks for comparable monetary values, dates and durations; currency-aware normalization; separate source documents; literal source quotes; conflicting evidence remains uncertain.
- Current document versions determine retrieval, findings and coverage. Source amendments supersede old grounding findings instead of leaving contradictions active forever.
- Scoring 6.2 separates evidence coverage from verification attempts. Zero claims, missing sources or no conclusive source-backed checks produce Not assessed. Partial coverage caps the score at 79; an unresolved critical finding caps it at 49. These are deterministic decision-support rules, not calibrated probabilities of truth.
- Score breakdown exposes supported, contradicted, unsupported and uncertain claims, real deductions and measured coverage. Missing evidence cannot yield a clean 100/100.
- Passport revision updates preserve verification links. Version 2 signatures cover the issued audit identity, source hash, chain head, score, band, findings summary and review state. Tampering invalidates verification.
- Safe bounded proof expressions replace arbitrary evaluation and contradictory boolean assertions now fail correctly.
- Challenge results use actual recorded executions; unavailable models return explicit errors. Status endpoints no longer invent model uptime or latency.
- Auth boundaries, invalid UUID responses, reviewer error recovery, health degradation and API-safe SPA navigation.
- Evidence preview and text highlighting, source/primary upload roles, persistent workspace drafts, unsaved-change prompts, stale-result clearing, keyboard and focus improvements, reduced-motion splash and mobile proof layout.

## Validation

- Full backend suite: 193 passed, zero skipped, against a temporary isolated PostgreSQL database. The database is removed afterward; production data is not used by the test suite.
- TypeScript build check: passed.
- Frontend production build: passed and bundled with the backend.
- Live browser upload of a synthetic contract and source approval produced four extracted claims, four contradictions and four findings, including a critical mismatch. The UI showed the real score and evidence coverage.
- Regression verifies that replacing the source with a matching new version supersedes the old contradictions and produces fully supported claims.
- Regression verifies passport score tampering, unsupported proof inputs, atomic upload rollback and missing model checkpoint behavior.
- Existing default-superuser-password configuration still emits a development warning. Deployment configuration needs its own review.

## Work still outstanding

The complete blueprint is substantially broader than this repair. Source authority resolution rules, source watchers, the claim graph, production evaluation datasets and ablations, full adversarial execution orchestration, mobile release and production deployment are not certified complete here.

Full live keyboard, screen-reader, contrast and all viewport conformance checks are not certified. Historical UI observations and design recommendations in the original audit require current visual validation. Parser resource limits reduce risk but are not a full sandbox or an exhaustive malformed-document assessment. Response-body timeouts, concurrent model loading and numeric-only proof draft detection have now been hardened. Broad network failure and accessibility coverage still needs further validation.

Generated model weights, training corpora, databases, runtime credentials, local test artifacts and unrelated mobile changes are excluded from this delivery. The master blueprint is retained separately as the desired product specification.

## Continuation: Source Fact Sheet and follow-up fixes

- Added a current-source-only fact sheet with canonical contract value, delivery date, payment days and warranty months, plus exact quotes, document versions, text hashes, upload timestamps and source locations. Canonical fields are withheld when sources disagree.
- Re-extraction validates that each displayed grounded value actually occurs in its literal source quote. Forged payload values and source-location spans are rejected; sentence context must contain the fact span before a canonical business field is assigned. Earlier fact records without quote provenance are shown as needing refresh; re-running the audit populates provenance.
- Reviewer-declared source authority and required notes persist through a permission-scoped endpoint and an audit-chain event. An existing passport refreshes its signature and revision while retaining the verification link. Authority labels do not automatically resolve conflicts or certify authenticity. Browser uploads do not supply original file modification timestamps; upload timestamps are labelled accordingly.
- Live synthetic audit refresh produced four grounded source facts. The reviewer note and reference authority saved successfully in the actual browser. The 390-pixel viewport showed no horizontal overflow; keyboard Tab correctly focused the labelled note field. These checks are not full accessibility certification.
- Source previews clear search filters and move focus to the opened document. Source editor drafts trigger unsaved-change prompts. Score and source-fact queries invalidate after a completed re-audit.
- Passport summaries now exclude obsolete and superseded findings. Added regression for a source amendment that clears all findings and publishes total=0/open=0.
- Request timeouts remain active through response-body receipt. Pre-cancelled requests respect their signal. Concurrent verifier loading uses a shared lock and a regression confirms that eight requests construct one model. Numeric-only proof drafts now trigger unsaved-change protection.
- Updated the scoring explanation page to describe evidence gates and actual coverage caps. Typed business policy configuration and enforcement are implemented in the following continuation.


## Continuation: Policy Studio and enforced business requirements

- Administrators can create, enable, disable and revise typed policies, with required change notes, stored revision history and optimistic version checks. Reviewers can read policies and use the read-only preview endpoint. Unsupported legacy policies are explicitly labelled as not enforced.
- Supported business fields are contract value, currency, delivery date, payment days and warranty months. Rules can apply globally or to one audit, and can inspect AI claims or current source facts. Conditions require literal, validated document evidence; absent or conflicting values remain uncertain and currencies are never silently converted.
- Pipeline policy checks run before scoring and passport signing. Violations create severity-weighted findings; uncertain requirements and changed, unchecked policies prevent a complete rating. Evaluation snapshots record exact policy versions and current document hashes in the audit chain.
- Repeated identical checks preserve review decisions. Revised or disabled rules supersede obsolete findings. Historical findings cannot be resurrected through review actions, and running audits cannot be reviewed or rescored.
- Public verification preserves the issued signed record and marks changed policies, documents or review events as requiring reassessment. The public UI withholds a current numeric grade when reassessment is required or integrity checks fail.
- Actual browser preview found 12 months of source warranty against a 24-month requirement without saving results. Saving an enabled rule scoped only to the synthetic golden audit and re-running it produced five findings (four source contradictions plus one policy violation), policy compliance 0%, and a real score of 0. The mobile policy editor had no horizontal overflow. This synthetic policy does not apply to other audits.
- Final isolated backend suite: 188 passed, zero skipped. TypeScript and production frontend build passed. Additional regressions cover invalid rules, role restrictions, non-mutating preview, currency incompatibility, source conflicts, version races, stale public ratings, pipeline enforcement and superseded/running-audit review guards.
- Policy coverage is limited to these five extracted business fields and supported comparisons. General natural-language policy interpretation, authority precedence, source watchers, claim graph, production evals, mobile release and deployment remain outstanding. Stored policy revision history is controlled through the API; it is not a separate signed configuration ledger.


## Continuation: Current evidence and assessment freshness

- Claims, findings and evidence review endpoints now share a current-evidence filter: same audit, current primary claims, separate current source documents, non-empty literal quotes. Exact duplicate evidence records are collapsed for display; underlying historical rows remain intact.
- The semantic and neural verification paths now receive this filtered evidence too. Forged quotes and cross-audit references cannot bypass deterministic validation by reaching a fallback model. Retrieval persistence rejects invalid source references and duplicate chunks; bulk retrieval excludes superseded primary claims.
- Source amendments invalidate exposed claim grounding when its recorded evidence is obsolete. The current response projects uncertainty with zero confidence and no obsolete citation IDs, without rewriting the historical claim record.
- Scoring 6.2 withdraws previous coverage and sub-scores when the document set changes after the recorded evaluation snapshot, including audits with no active business policies. A fresh audit is required before a new rating is available. Legacy audits without this snapshot should be re-audited to establish this provenance; the previously implemented public passport freshness checks remain in place.
- Evidence loading is batched for claim and finding lists rather than fetching source evidence once per item.
- A fast re-audit can complete between UI polls. The result page now explicitly refreshes score, findings, documents, source facts and policy results after a run request. Numeric ratings and coverage are withheld while a run is refreshing or incomplete; score-load failures also withhold the grade.
- Isolated backend suite: 193 passed, zero skipped. New regressions cover stale and cross-audit evidence, primary self-citations, forged quotes, exact duplicates, historical primary versions, fallback-model input boundaries, stale grounding projection and source changes without any business policy. TypeScript validation passed. No full accessibility or production-deployment certification is implied.

- Live browser validation confirmed the numeric grade disappears during re-audit refresh and updated policy text arrives without reloading the page. The production frontend build passed and is bundled with this delivery.
