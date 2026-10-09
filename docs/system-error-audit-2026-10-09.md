# Tathya consolidated system and UI/UX audit

Reviewed 9 October 2026. Findings from code inspection, executed tests, and explicitly historical screenshots. This is the original findings snapshot, before repairs. See system-repair-status-2026-10-09.md for the verified repair status; the historical counts below describe the original run.

## Evidence and limits

- **T**: reproduced by execution. **C**: confirmed implementation defect or missing behavior. **R**: risk or design recommendation requiring live validation. **H**: observed in a historical screenshot, not proof of the current interface.
- Full backend suite on a newly created isolated PostgreSQL database: **128 passed, 2 failed, 1 teardown error, 0 skipped**. Temporary database removed afterward.
- Failing tests: `test_audit_job_completes_and_persists_chain`, `test_api_audit_lifecycle_serialization`. Both encounter scoring methodology exceeding database column width.
- Teardown error: users deleted while `audit_log.actor_id` still references them.
- TypeScript check fails on unused `metrics` in `frontend/src/components/Audits/ControlPages.tsx`.
- Ruff F checks: 114 findings; many are maintenance issues rather than runtime failures. Do not add 114 to the issue count below.
- In-memory API probes reproduced metrics 500, invalid judge UUID 500, and a contradictory natural-language proof incorrectly returning satisfiable. Database proof call reproduced undefined `Real`.
- Current live browser review was attempted, but browser webview attachment timed out. No current viewport, contrast, keyboard, screen-reader or touch conformance certification is claimed.
- Findings are separately actionable but not necessarily independent root causes. Recommendations and risks are not counted as reproduced bugs.

## Previous findings, consolidated

| ID | Evidence | Finding and consequence | Source |
|---|---|---|---|
| 1 | T | Scoring methodology is 46 characters; database column allows 32. Valid uploaded audit fails at scoring/passport stage. | models.py; trust_score.py |
| 2 | T | Passport exception handler accesses expired audit before rollback, causing PendingRollbackError and obscuring original failure. | core/pipeline.py |
| 3 | T | RoPE metrics endpoint uses missing Path import and returns 500. | routes/rope.py |
| 4 | T | Database proof function uses undefined Real and crashes. | core/z3_engine.py |
| 5 | C | Same function has undefined Int, Bool and exception-path unknown. | core/z3_engine.py |
| 6 | T | Goal A plus assumption not A returns satisfiable; text assertions are encoded as unrelated true variables. | core/z3_engine.py |
| 7 | T/C | Challenge results return six hardcoded successful trials rather than actual executions. | routes/challenges.py |
| 8 | C | Dashboard calls hardcoded results measured accuracy and zero synthetic bias. | Phase6/ChallengeResults.tsx |
| 9 | C | Missing/corrupt checkpoint permits initialized random model weights without an unavailable/untrained response. | core/rope_inference.py |
| 10 | C | Model training endpoint has no authentication dependency. | routes/rope.py |
| 11 | C | Global platform statistics endpoint has no authentication dependency. | routes/challenges.py |
| 12 | T | Unused metrics variable blocks frontend TypeScript production check. | Audits/ControlPages.tsx |
| 13 | C/R | Fixed frontend IP differs from local proxy host; unreachable address can cause fetch errors. Exact user's browser failure is not traced yet. | frontend/.env; vite.config.ts |
| 14 | C | Parser StageError is not translated into a handled upload HTTP error. | routes/audits.py |
| 15 | C | Audit commits before uploads validate; rejection can leave queued audit with no queued worker. | routes/audits.py |
| 16 | C | Multi-file ingest commits per document; later rejection leaves a partially saved set. | routes/audits.py; core/pipeline.py |
| 17 | C | Stored file remains after parsing fails; no failure cleanup. | routes/audits.py |
| 18 | C | Same filename overwrites stored bytes of previous document versions. | core/pipeline.py |
| 19 | C | Incoming names reduced to basenames can collide. | core/pipeline.py |
| 20 | C | Entire upload is read before the 50 MB limit is checked. | routes/audits.py |
| 21 | C | Upload route has no file-count or aggregate-byte cap. | routes/audits.py |
| 22 | C/R | Synchronous parsing in async upload route can block event-loop responsiveness. | routes/audits.py |
| 23 | C/R | No overall parsing/OCR time budget. | core/parsers.py |
| 24 | C/R | Extracted-text limit checked after extraction; oversized input already consumes resources. | core/parsers.py |
| 25 | C | Backend accepts audit without documents; worker later fails. | routes/audits.py; core/pipeline.py |
| 26 | C/R | Additional uploads permitted during processing, risking inconsistent worker snapshot. | routes/audits.py |
| 27 | C | Additional uploads enqueue work without immediately resetting completed audit to queued. | routes/audits.py |
| 28 | C | Processing queries include previous versions; no current-version filter. | core/pipeline.py |
| 29 | C | Source-set hash includes previous versions too; current-set meaning is unclear. | routes/audits.py |
| 30 | C | DOCX paragraphs extracted before all tables, losing original interleaving. | core/parsers.py |
| 31 | C | Backend image OCR supported, but submit UI rejects images. | core/parsers.py; routes/_layout/submit.tsx |
| 32 | C | Standard upload pipeline does not create claims; grounding depends on existing claims. | core/pipeline.py; grounding.py |
| 33 | C | Evidence helper fetches existing rows; actual retrieval remains a placeholder there. | core/grounding.py |
| 34 | C | Saved score breakdown uses undefined fields import. | core/trust_score.py |
| 35 | C | Counter-evidence imports uuid as _uuid but invokes uuid.UUID. | core/counter_evidence_engine.py |
| 36 | C | Policy loop iterates pol but references undefined policy.id. | core/policy_engine.py |
| 37 | C | Manual passport signs different message format than public verification expects. | routes/audits.py; core/pipeline.py |
| 38 | C | Manual passport hash derives from audit ID and scores rather than source-set hash. | routes/audits.py |
| 39 | C | Manual passport stores zero chain head instead of actual chain head. | routes/audits.py |
| 40 | C | Pipeline returns existing passport without refreshing after reruns/new sources. | core/pipeline.py |
| 41 | C | Rescore updates reviewed_score but not passport trust_score. | routes/audits.py |
| 42 | C | Open count differs: summary counts pending/open, rescore pending/accepted. | routes/audits.py |
| 43 | C | Challenge results page ignores audit ID and shows global results. | Phase6/ChallengeResults.tsx |
| 44 | C | Global auth handling recognizes Axios errors, not custom audit fetch errors. | main.tsx; api/audits.ts |
| 45 | C | Every Axios 403 logs user out, including permission denial with valid credentials. | main.tsx |
| 46 | C/R | Logout does not clear query cache; account switching can briefly reuse cached data. | hooks/useAuth.ts |
| 47 | C | Route login guard checks token presence only. | hooks/useAuth.ts |
| 48 | C | Fetch network failures are not normalized into actionable user messages. | api/audits.ts; phase6.ts |
| 49 | C/R | No explicit timeout for custom fetch requests. | api/audits.ts; phase6.ts |
| 50 | C | Structured validation details are replaced by generic request-failed message. | api/audits.ts; phase6.ts |
| 51 | C | Metrics fetch uses relative URL while other requests use configured API host. | Audits/ControlPages.tsx |
| 52 | C | Metrics non-OK response silently becomes null. | Audits/ControlPages.tsx |
| 53 | C | Passport helper uses a different API environment variable convention. | api/passports.ts; config/index.ts |
| 54 | C | Protected passport getter sends no bearer authorization header. | api/passports.ts |
| 55 | C | Audit helper exposes challenge/resolve/inject/backfill methods without matching audit routes found. | api/audits.ts; routes/audits.py |
| 56 | C/R | In-memory job queue has no restart recovery mechanism. | core/jobs.py |
| 57 | C/R | Queue does not deduplicate jobs for same audit. | core/jobs.py |
| 58 | C | Worker initial DB lookup/status commit occurs outside protected job try block. | core/jobs.py |
| 59 | C/R | Training check and active-state update are not atomic; duplicate requests can enqueue jobs. | routes/rope.py |
| 60 | C/R | Training lock held throughout training; extra queued tasks can wait then train again. | routes/rope.py |
| 61 | C | Inference model cache lacks training-completion reload/invalidation. | core/rope_inference.py; routes/rope.py |
| 62 | C | Null scores excluded from numerator but included in average denominator. | routes/challenges.py |
| 63 | C | Empty dataset average defaults to 100. | routes/challenges.py |
| 64 | C | Verification view count hardcoded to zero. | routes/challenges.py |
| 65 | C | Challenge count is catalogue size, not executed challenges. | routes/challenges.py |
| 66 | C | Missing score band defaults to trustworthy in aggregate metrics. | routes/challenges.py |
| 67 | C/R | Degraded health returns HTTP 200; status-only monitoring misses degradation. | routes/health.py |
| 68 | C/R | Wildcard CORS with credentials; intended origins are not restricted. | app/main.py |
| 69 | C/R | Development default admin password remains configured; unsafe if publicly exposed. | core/config.py; test warnings |
| 70 | C | Backend static frontend mount disabled; backend alone does not serve built UI. | app/main.py |
| 71 | T | Invalid evidence UUID returns 500 instead of client validation error. | routes/challenges.py |
| 72 | C | judge_result accepted in request but unused. | routes/challenges.py |
| 73 | C/R | RoPE claim/evidence lack nonempty and maximum-length validation. | routes/rope.py |
| 74 | C/R | Proof timeout lacks positive and maximum bounds. | routes/challenges.py |
| 75 | C | Frontend proof model schema rejects backend model:null for UNSAT. | api/phase6.ts; core/z3_engine.py |
| 76 | C | Empty proof response omits fields required by frontend schema. | core/z3_engine.py; api/phase6.ts |
| 77 | T | Test teardown fails on audit-log user foreign key. | tests/conftest.py |
| 78 | C | Test fixture deletes all users in configured DB; no isolated database enforcement. | tests/conftest.py |
| 79 | C | End-to-end walkthrough calls port 8000; startup script uses 8001. | tests/e2e-user-walkthrough.spec.ts |
| 80 | C | Auth setup URL regex can match login page without proving successful navigation. | tests/auth.setup.ts |
| 81 | C | Duration extraction test does not assert a duration was found. | tests/test_phase3_grounding.py |
| 82 | C | Version test validates IDs but not preservation of old stored bytes. | tests/test_phase1_db.py |
| 83 | C | Unresolved Tuple/Claim/uuid annotations can break annotation introspection; not all are immediate runtime crashes. | real_document_auditor.py; policy_engine.py; z3_engine.py |
| 84 | C | Numerous unused/duplicate imports and unused variables; maintenance burden. 114 static findings are not 114 runtime bugs. | Ruff F output |

## New UI, UX, navigation and accessibility findings

| ID | Evidence | Finding and consequence | Source |
|---|---|---|---|
| 85 | C | Scenario card link passes audit ID only; selected scenario is lost on entering Injector. | Phase6/ChallengeLibrary.tsx |
| 86 | C | No-audit scenario link invents demo ID instead of directing user to create/select an audit. | Phase6/ChallengeLibrary.tsx |
| 87 | C | Injector-to-Judge link passes audit ID only; generated candidate is not transferred. Judge opens unrelated default content. | InjectorWorkspace.tsx; JudgeWorkspace.tsx |
| 88 | C | Judge defaults to GDP example even on an actual audit-specific route; current audit content is not automatically loaded. | JudgeWorkspace.tsx |
| 89 | C | Judge converts finding reason into claim and suggested fix into evidence; original claim/source evidence is not used. | JudgeWorkspace.tsx |
| 90 | C | Judge assigns flag ID as evidence ID, misleading evidence identity/provenance. | JudgeWorkspace.tsx |
| 91 | C | User-added evidence automatically receives 0.9 score and supports label without evaluation. | JudgeWorkspace.tsx |
| 92 | C | Judge labels user-entered evidence Authorized Grounding Evidence without a source authorization workflow. | JudgeWorkspace.tsx |
| 93 | C | Evidence Integrity is always displayed Verified Valid for any returned review, not tied to a verification flag. | JudgeWorkspace.tsx |
| 94 | C | Injector mutation errors have no rendered error message. | InjectorWorkspace.tsx |
| 95 | C | Judge mutation errors have no rendered error message, including prompt-injection rejection. | JudgeWorkspace.tsx |
| 96 | C | Proof mutation errors have no rendered error message. | ProofSandbox.tsx |
| 97 | C | Injector audit/doc/text/scenario queries lack dedicated loading/error/retry UI. | InjectorWorkspace.tsx |
| 98 | C | Judge audit/finding queries lack error/retry UI; failure can look like no findings. | JudgeWorkspace.tsx |
| 99 | C | ReviewerGate shows Checking workspace access indefinitely when current-user request fails without returning user. | Audits/ReviewerGate.tsx |
| 100 | C | Editing proof constraints does not invalidate prior displayed result; old verdict can appear to describe new inputs. | ProofSandbox.tsx |
| 101 | C | Editing judge claim/evidence/category does not clear previous verdict. | JudgeWorkspace.tsx |
| 102 | C | Editing injected candidate does not clear old generated diff/hash output. | InjectorWorkspace.tsx |
| 103 | C | Switching source document can preserve modified text from previous document due to conditional population effect. | InjectorWorkspace.tsx |
| 104 | C/R | Edits are not blocked during pending operations; late response can render output for an older input. | Phase6 workspaces |
| 105 | C | Judge added evidence cannot be removed or edited through evidence cards. | JudgeWorkspace.tsx |
| 106 | C | Proof goals/assumptions state is sent but no corresponding edit controls exist; preset data can be hidden from user. | ProofSandbox.tsx |
| 107 | C | Percentage preset advertises sum proof, but introduces duplicate variable equality; no actual sum relation is encoded. | ProofSandbox.tsx |
| 108 | C | Default proof values describe conflict but constrain distinct variables without equality relation; default is consistent. | ProofSandbox.tsx |
| 109 | C | Proof audit ID ignored; audit-specific URL does not bind computation to audit sources. | ProofSandbox.tsx |
| 110 | C | Proof result.error and timeout do not have explicit dedicated user explanations. | ProofSandbox.tsx |
| 111 | C | Document viewer is clickable div without button semantics, tab stop or keyboard handler. | Audits/AuditResult.tsx |
| 112 | C | Clicks inside expanded document text bubble to parent and toggle it closed, disrupting selection/reading. | Audits/AuditResult.tsx |
| 113 | C | Document content error has no retry action or specific error explanation. | Audits/AuditResult.tsx |
| 114 | C | Result claims Gemini 3.5 Flash and BGE-M3 verification regardless of providers actually used. | Audits/AuditResult.tsx |
| 115 | C | Result badge claims scoring v4.0 while backend scoring version is 5.0. | Audits/AuditResult.tsx; core/trust_score.py |
| 116 | C | UI deductions sum raw impact_score instead of using authoritative scoring breakdown; materiality/policy effects can disagree. | Audits/AuditResult.tsx |
| 117 | C | Negligible severity excluded from displayed four-level breakdown. | Audits/AuditResult.tsx |
| 118 | C | Failed result has no rerun button despite backend run endpoint existing. | Audits/AuditResult.tsx; routes/audits.py |
| 119 | C | Raw backend failure strings are shown to end users; DB/internal details can become confusing error copy. | Audits/AuditResult.tsx |
| 120 | C | Reviewer typed note is sent as reason, not note; backend reviewer_note display field therefore may not update. | Investigation.tsx; api/audits.ts; routes/audits.py |
| 121 | C | Rescore only invalidates audit detail cache, not audit-list/metrics caches; other pages can remain stale. | Audits/Investigation.tsx |
| 122 | C | Severity/category/rationale/editor inputs in Phase6 lack properly associated accessible labels. | Phase6 workspaces |
| 123 | C | Proof trash icon buttons have no accessible name. | ProofSandbox.tsx |
| 124 | C | Scenario search relies on placeholder without a persistent accessible label. | ChallengeLibrary.tsx |
| 125 | C/R | Dynamic proof/verdict/diff result panels lack live-region announcements or deliberate result-focus management. | Phase6 workspaces |
| 126 | C | Shared LoadingButton has spinner but no aria-busy state or changing accessible operation status. | ui/loading-button.tsx |
| 127 | C | Sidebar active mapping excludes injector/judge/proof/results subroutes, losing section context. | Sidebar/Main.tsx |
| 128 | C/R | No skip-to-main link in app shell; keyboard users repeatedly traverse navigation. | routes/_layout.tsx |
| 129 | C/R | Phase6 metadata frequently uses 9-11px text; difficult readability, especially mobile. Contrast has not been measured. | Phase6 components; index.css |
| 130 | C/R | Proof fixed 12-column input row does not stack on narrow screens; numeric values/operator controls may be cramped. | ProofSandbox.tsx |
| 131 | C/R | Proof trash target is small icon plus 4px padding; mobile touch usability needs improvement/measurement. | ProofSandbox.tsx |
| 132 | C | Technical Phase6/mesh/SMT/hash jargon dominates explanatory copy without beginner guidance. | Phase6 components |
| 133 | C | Source library shows metadata/hashes but provides no source opening control. | Audits/ControlPages.tsx |
| 134 | C | Scenario empty catalogue has no dedicated empty-state explanation/action. | ChallengeLibrary.tsx |
| 135 | C | Splash runs again on full reload; once-per-tab session persistence described by design review no longer exists. | Common/BrandSplash.tsx; design review README |
| 136 | C/R | Normal splash blocks view for 2.6 seconds and has no skip action. | Common/BrandSplash.tsx |
| 137 | C/R | Splash is overlay with role status; underlying controls are not made inert or focus-contained. Keyboard focus may reach obscured content. | Common/BrandSplash.tsx |
| 138 | C | Historical design documentation claims successful build/session persistence; current implementation/build contradict those claims. | docs/ui-design-review/README.md |
| 139 | H/R | Historical mobile result requires long scrolling before actionable findings; consider summary links/collapsible detail. Not a current live measurement. | artifacts/ui-review/result-mobile-v2.png |
| 140 | H/R | Historical desktop dashboard uses very small metadata/status/date labels relative to available space. Review at actual size and zoom. | docs/ui-design-review/screenshots/control-desktop-v2.png |
| 141 | C/R | Unsaved candidate/review-note/constraint edits have no navigation warning or draft persistence. | Phase6 workspaces; Investigation.tsx |
| 142 | C | Upload UI error may remain the prior mutation error after selecting different files; mutation is not reset on addFiles. | routes/_layout/submit.tsx |
| 143 | C | One invalid file rejects the entire incoming batch rather than accepting valid files and reporting rejected ones. | routes/_layout/submit.tsx |
| 144 | C | Selected-file React key omits size despite dedup identity including size; same name/time with different size can create duplicate keys. | routes/_layout/submit.tsx |
| 145 | C/R | Submit offers only pending spinner, no upload progress/cancel affordance for large files. | routes/_layout/submit.tsx; api/audits.ts |
| 146 | C/R | Selected audits/documents are held in local state rather than URL; refresh/share/back navigation loses selection context. | SourcesPage; Phase6 workspaces |

## Review limits and next verification targets

The list contains 146 numbered findings, risks and recommendations, not 146 independently reproduced crashes. Historical visual observations and code-level accessibility findings must not be represented as current browser-tested conformance failures.

Remaining live targets: current browser upload trace; desktop and 320/390/768px mobile routes; 200% zoom/reflow; measured contrast; keyboard/focus/screen reader; long filenames/large evidence text; offline/slow network; response ordering during concurrent edits; real Android connectivity; PDF scans/encrypted files/spreadsheets; deployed schema migrations; restart recovery; actual model checkpoint and evidence-grounding accuracy.
