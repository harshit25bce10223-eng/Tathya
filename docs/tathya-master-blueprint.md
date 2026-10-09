Bhai, **ab final lock kar dete hain.** Maine Tathya ke product plan, reuse-first correction plan, aur detailed implementation plan ko merge karke **ek single execution blueprint** bana diya hai. Core idea/scope same rahega; jo conflicts the, unmein main explicit final decisions de raha hoon.

The final product remains **1 shared backend + 1 AI Trust Core + 2 web experiences + 1 thin mobile companion**. The latest reuse plan also correctly separates the reused infrastructure from the original Trust Engine.  

# TATHYA — FINAL 36-HOUR MASTER BUILD BLUEPRINT

## 0. Final product definition

### Name

# **Tathya (तथ्य)**

### One-liner

> **Tathya fact-checks AI-written business documents against their source files, proves important conflicts, helps a human reviewer resolve uncertainty, and issues a tamper-evident Trust Passport.** 

### Final product surfaces

```text
Tathya Submit
    ↓
Business/User Portal

Tathya Control Center
    ↓
Reviewer + Admin Portal

Tathya Scan
    ↓
Thin Mobile Companion

Tathya Passport
    ↓
Signed report + QR verification
```

The user, reviewer and mobile experiences all connect to the same Trust Core. 

---

# 1. The central philosophy

Tathya does **not** say:

> “The AI says this document is 82% trustworthy.”

Instead:

```text
What did AI claim?
        ↓
What evidence supports it?
        ↓
What contradicts it?
        ↓
What important thing was omitted?
        ↓
Which source is authoritative/current?
        ↓
Is there privacy/risk/policy problem?
        ↓
How materially important is the problem?
        ↓
What should the reviewer check?
        ↓
Human decision
        ↓
Auditable result
```

That distinction is the entire product.

---

# 2. Final USPs

## USP 1 — **Judge can attack the document**

The judge can actively inject a lie, change a value, or add a risky promise, and watch Tathya detect it.

So the demo is not:

> “Trust us, it works.”

It is:

> **“Please try to break it.”**

Your Jhooth Chhupao and Injector are specifically designed around this. 

---

## USP 2 — **Proof, not guesswork**

Numbers, dates, durations, checksums and formal constraints are handled by deterministic logic and Z3 rather than trusting an LLM's arithmetic judgment. 

So:

```text
₹41.6 lakh ≠ ₹50 lakh
```

is a calculation.

And:

```text
40% + 30% + 40% ≠ 100%
```

becomes a formal **UNSAT** result.

---

## USP 3 — **Living Trust**

A document isn't “trusted forever.”

If a source changes:

```text
Source v2
   ↓
changes
   ↓
re-audit
   ↓
stale claims
   ↓
score changes
```

The current plan explicitly uses watched sources, stale evidence and re-audit with a manual fallback. 

---

## USP 4 — **Source + Business Policy**

Tathya checks both:

```text
Does the source support it?
```

and:

```text
Is the claim allowed by company policy?
```

Policy Studio therefore makes it more than a generic hallucination checker.  

---

## USP 5 — **Honest uncertainty + tamper-evident accountability**

When fast verifier and judge disagree, Tathya does **not invent confidence**.

It returns:

> **UNCERTAIN → HUMAN REVIEW**

Then reviewer decisions go into the hash-chained audit trail and the Passport can be verified via QR.  

---

# 3. The additional differentiators

These are what take Tathya beyond ordinary grounding.

## A. Materiality Engine

Not every error is equally important.

```text
Name typo            LOW
Wrong date           HIGH
Wrong price          CRITICAL
Unlimited liability  CRITICAL
```

Materiality and blast radius are explicitly part of the architecture. 

---

## B. Source Intelligence

For every source, maintain:

```text
authority
version
mtime
approval status
```

Then:

```text
latest approved source
        >
older draft
```

When sources disagree, preserve the losing source as counter-evidence rather than silently throwing it away. 

---

## C. Omission Detection

Most people ask:

> “What did AI hallucinate?”

Tathya also asks:

> **“What important thing did AI leave out?”**

Example:

```text
Source:
Net 45 + 2% late fee

Generated:
Net 45
```

→ **Material omission**

The omission detector is explicitly included in the final plan. 

---

## D. Counter-Evidence

Don't only search:

> “What supports this?”

Also search:

> **“What in the source argues against it?”**

So a claim can have:

```text
supporting evidence
+
counter-evidence
```

That powers a much stronger investigation UI. 

---

## E. What-to-Check

Instead of dumping 15 flags:

```text
1. Verify contract value
2. Verify payment term
3. Verify guarantee
```

with a reason and source.

This is the reviewer decision-support layer.

---

# 4. Final platform architecture

## User side

# **Tathya Submit**

```text
Login
 ↓
Dashboard
 ↓
New Audit
 ↓
Upload AI document + sources
 ↓
Choose type/language
 ↓
Run audit
 ↓
Result
 ↓
Details
 ↓
Trust Passport
```

The user's view is intentionally simplified: score, sub-scores, top risks, recommendations and report. Internal reviewer notes and full internal reasoning stay hidden. 

---

# 5. Reviewer side

# **Tathya Control Center**

This is the **hero platform**.

### Dashboard

```text
Audits Today
Critical
High Risk
Pending Review
Average Score
```

### Review Queue

Sorted by:

```text
critical
↓
high
↓
medium
↓
low
```

### Investigation Workspace

Left:

**Document**

Right:

**Claim + Evidence + Risk + Action**

This exact split-view is already in the current implementation plan. 

---

# 6. Main Investigation Workspace

Example:

```text
┌──────────────────────────────┬─────────────────────────────┐
│                              │                             │
│       DOCUMENT               │       CLAIM #17             │
│                              │                             │
│ "Contract value is ₹50L" 🔴 │ STATUS: CONTRADICTED        │
│                              │                             │
│ Delivery: 15 Dec 🔴         │ Generated: ₹50L             │
│                              │ Source: ₹41.6L              │
│ Payment: 30 days 🔴         │                             │
│                              │ Evidence: Finance Approval  │
│ Warranty: 5 years 🔴        │ Authority: 5/5              │
│                              │                             │
│                              │ Business Impact: CRITICAL   │
│                              │ Score Impact: -15/...       │
│                              │                             │
│                              │ WHAT TO CHECK               │
│                              │ Verify latest approval      │
│                              │                             │
│                              │ [ACCEPT] [DISMISS] [FIX]    │
└──────────────────────────────┴─────────────────────────────┘
```

Every flag has a defined structured record including evidence, source location, confidence, materiality and suggested fix. 

---

# 7. Mobile

# **Tathya Scan**

Do **not** make it a second full application.

It is a companion.

### Five perfect flows:

```text
Login
Scan / upload
Score
Swipe review
QR verify
```

Plus notifications where stable.

The mobile plan intentionally keeps heavy processing on the backend and has PWA fallback if native integration becomes unstable. 

---

# 8. Public Passport verification

No login:

```text
/verify/:id
```

Scan QR:

```text
Passport
   ↓
Hash
Signature
Chain
Reviewer summary
   ↓
VERIFIED / TAMPER DETECTED
```

The plan explicitly uses a public verify page and hash-chain verification. 

---

# 9. FINAL AI TRUST CORE

This is the heart.

```text
                 INPUTS
            AI DOCUMENT
                 +
              SOURCES
                 ↓
              PARSER
                 ↓
          SOURCE FACT SHEET
                 ↓
           CLAIM EXTRACTION
                 ↓
      ┌──────────┴───────────┐
      ↓                      ↓
  RULE ENGINE            RETRIEVAL
      │                      │
 numbers/date/name       BM25+BGE
      │                      ↓
      │                   reranker
      │                      ↓
      │                  top evidence
      └──────────┬───────────┘
                 ↓
             VERIFY
        rule / NLI / judge
                 ↓
     SUPPORT / CONTRADICT /
     UNSUPPORTED / UNCERTAIN
                 ↓
        COUNTER-EVIDENCE
                 ↓
        OMISSION DETECTOR
                 ↓
          POLICY ENGINE
                 ↓
            RISK SCAN
                 ↓
          PROVENANCE
                 ↓
           MATERIALITY
                 ↓
           BUSINESS IMPACT
                 ↓
             TRUST SCORE
                 ↓
        REVIEWER / PASSPORT
```

The current detailed plan defines essentially this exact sequence. 

---

# 10. Source Fact Sheet

This is **very important**.

Instead of directly doing:

```text
AI document → source search
```

we first build:

```text
SOURCE FILES
    ↓
CANONICAL FACT SHEET
```

Example:

```json
{
  "contract_value": 4160000,
  "currency": "INR",
  "delivery_date": "2026-12-22",
  "payment_terms_days": 45,
  "warranty_months": 12
}
```

Every fact contains:

```text
value
quote
source
location
authority
mtime
```

And grounding guard rejects an extracted fact when the value isn't actually contained in its cited quote. 

---

# 11. Retrieval architecture

### Layer 1 — exact retrieval

**BM25**

Good for:

```text
PO-2026-001
₹41,60,000
99.5%
Net 45
```

### Layer 2 — semantic retrieval

**BGE-M3**

Good for:

```text
"payment must be completed within 45 days"
```

matching:

```text
"Net 45"
```

BGE-M3 supports multilingual retrieval, and the BGE reranker is designed for lightweight multilingual reranking. ([GitHub][1])

### Layer 3 — reranking

```text
Top 20
 ↓
BGE reranker
 ↓
Top 3
```

This is exactly the hybrid retrieval path in the plan. 

---

# 12. Verification hierarchy

For every claim:

## Level 1 — deterministic rule

If the claim maps to:

```text
contract_value
delivery_date
payment_terms
warranty
```

compare directly against fact sheet.

Fastest and strongest.

---

## Level 2 — fast verifier

Only claims rules can't settle.

---

## Level 3 — judge LLM

Only ambiguous claims.

And judge must return evidence quote.

If quote doesn't actually appear in retrieved evidence:

# **UNCERTAIN**

The plan explicitly uses this quote-verification safeguard. 

---

# 13. Z3 Proof Sandbox

Don't ask LLM to write solver code.

Use only fixed templates:

```text
T1 → milestones sum = 100
T2 → milestones amount = contract value
T3 → start < delivery <= end
T4 → liability <= policy cap
T5 → warranty >= minimum
T6 → payment days >= minimum
```

Then:

```text
Judge changes slider
       ↓
Z3
       ↓
SAT / UNSAT
       ↓
Conflict core
       ↓
Highlighted clauses
```

This exact fixed-template philosophy is already locked. 

---

# 14. Risk Engine

## PII

Use:

```text
Presidio
+
custom Indian recognizers
```

Check:

```text
Aadhaar
PAN
GSTIN
Card
UPI
IFSC
Email
Phone
API keys
```

Indian checksums:

```text
Aadhaar → Verhoeff
Card → Luhn
PAN → format
GSTIN → check
```

The plan specifically limits this to synthetic identifiers. 

---

## Risky commitments

Patterns:

```text
guarantee
100%
unlimited liability
full refund
without any condition
```

Then LLM confirmation.

---

## Suspicious links

Detect:

```text
lookalike domains
IP URLs
shorteners
source-vs-document mismatch
```

---

# 15. Provenance

Not a “truth” signal.

Just an informational layer:

```text
AI metadata present?
Visible AI label?
Producer/custom properties?
```

The current plan intentionally makes provenance **informational rather than punitive**. 

---

# 16. Materiality engine

Example:

```text
Wrong name              0.1
Wrong date              0.6
Wrong price             1.0
Wrong liability clause  1.0
```

Then relative value gap contributes.

Also:

```text
Contract Value
      ↓
Payment milestones
      ↓
Penalty
      ↓
Tax
```

This becomes the **blast radius**.

The current plan deliberately keeps blast radius rule-based to make it predictable. 

---

# 17. Trust score

Final model:

```text
penalty =
severity_weight
× materiality
× confidence
```

Then:

```text
AI Score = 100 - all unresolved penalties
Reviewed Score = 100 - only accepted/remaining penalties
```

The current implementation specifies this scoring model and weights. 

### I would add one final safety rule:

**Unresolved critical business risk should cap the score below “trustworthy”.**

Example:

```text
Critical unresolved clause
        ↓
maximum trust = 49
```

That isn't a scientific claim; it's a product policy that prevents one catastrophic issue from being diluted by many small correct claims.

---

# 18. Score UI

Never display just one number.

Display:

```text
                 43
           REVIEW REQUIRED

Factual Support       61
Numerical             48
Dates                 72
Privacy               91
Commitment Risk       32
Evidence Coverage     68
```

Then:

# Trust Waterfall

```text
100
 ↓ financial mismatch
 80
 ↓ date mismatch
 72
 ↓ payment mismatch
 60
 ↓ commitment
 43
```

---

# 19. Judge Experience Zone

This should be one of the **most polished screens**.

## A. Jhooth Chhupao

Judge edits:

> “Contract value is ₹50 lakh.”

to:

> “Contract value is ₹75 lakh.”

System:

```text
Detected
Evidence
Severity
Business impact
```

And the exact changed sentence gets highlighted.

The challenge logic uses sentence diff and considers a modified sentence caught if a flag overlaps that changed region. 

---

# 20. B. Jhooth Injector

One click:

# `INJECT 10 LIES`

Mutation bank:

```text
number
date
name
invented claim
promise
PII leak
unit trap
```

Then:

```text
Caught: X
Missed: Y
False alarms: Z
```

**X/Y/Z must be actual runtime results**, never hard-coded. 

---

# 21. C. Trust Simulator

Toggle flags:

```text
Current: 53

Dismiss price flag
53 → 68

Fix payment
68 → 78

Remove unsupported guarantee
78 → 94
```

Now reviewer sees:

> Which correction matters most?

---

# 22. D. Live Edit Mode

Judge edits:

```text
10,000 → 8,000
```

System reruns.

Then:

```text
Trust: 43 → actual new score
```

This is possibly the **best live interaction** because the number comes from the actual pipeline.

---

# 23. E. Living Trust

Judge drops:

```text
Amendment_v3.pdf
```

System:

```text
New source detected
      ↓
Source conflict
      ↓
3 claims stale
      ↓
Re-audit
      ↓
new score
```

The architecture supports watched-folder detection, affected-audit reruns and stale evidence. 

---

# 24. F. AI Courtroom

Use **only for uncertain claims**.

```text
PROSECUTOR
Why it is wrong

DEFENDER
Why it may be correct

JUDGE
Final verdict + deciding evidence
```

Three tightly constrained prompts, cached results, only ambiguous cases. 

This should never be on the critical path.

---

# 25. Trust Passport

Final report contains:

```text
Audit ID
Document hash
Source set
Scores
Claims checked
Flags
Reviewer decisions
Policy version
Chain head
Provenance
Signature
```

Then:

```text
SHA-256
+
ECDSA P-256
+
QR
```

The plan specifies a tamper-evident hash chain and ECDSA-signed Passport. 

---

# 26. Tamper demo

Judge scans QR:

# ✅ VERIFIED

We secretly modify an audit-log record.

Scan again:

# 🔴 CHAIN BROKEN

And:

> Entry #N no longer matches the recorded hash chain.

Use the wording:

### **TAMPER-EVIDENT**

never:

### “tamper-proof”.

That distinction is already correctly specified. 

---

# 27. FINAL repository structure

```text
tathya/
│
├── README.md
├── LICENSES.md
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   │
│   │   ├── routers/
│   │   │   ├── audits.py
│   │   │   ├── flags.py
│   │   │   ├── proof.py
│   │   │   ├── challenge.py
│   │   │   ├── courtroom.py
│   │   │   ├── sources.py
│   │   │   ├── policies.py
│   │   │   ├── passport.py
│   │   │   ├── verify.py
│   │   │   ├── metrics.py
│   │   │   └── ocr.py
│   │   │
│   │   ├── core/
│   │   │   ├── pipeline.py
│   │   │   ├── parse.py
│   │   │   ├── facts.py
│   │   │   ├── numeric.py
│   │   │   ├── claims.py
│   │   │   ├── retrieve.py
│   │   │   ├── verify.py
│   │   │   ├── proof.py
│   │   │   ├── policy.py
│   │   │   ├── risk.py
│   │   │   ├── provenance.py
│   │   │   ├── materiality.py
│   │   │   ├── score.py
│   │   │   ├── courtroom.py
│   │   │   ├── living.py
│   │   │   ├── private.py
│   │   │   └── llm.py
│   │   │
│   │   ├── trust/
│   │   │   ├── chain.py
│   │   │   └── passport.py
│   │   │
│   │   └── eval/
│   │       ├── generate_pack.py
│   │       ├── mutate.py
│   │       ├── run_eval.py
│   │       └── ablation.py
│   │
│   ├── data/
│   │   ├── packs/
│   │   ├── policies/
│   │   └── cache/
│   │
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── submit/
│   │   │   ├── control/
│   │   │   └── verify/
│   │   ├── api/
│   │   └── components/
│   │
└── mobile/
    ├── app/
    └── src/
```

This matches the final reuse-first separation: **our logic in `core/` and `eval/`, reused components around it.** 

---

# 28. Final reusable GitHub stack

## 1. Base

### FastAPI Full Stack Template

Official repo currently provides FastAPI, React, TypeScript, Vite, Tailwind, shadcn/ui, TanStack tooling, JWT auth, PostgreSQL, Docker Compose and tests, and is MIT licensed. ([GitHub][2])

[FastAPI Full-Stack Template](https://github.com/fastapi/full-stack-fastapi-template?utm_source=chatgpt.com)

### FINAL DECISION:

**Fork it.**

---

## 2. UI

### shadcn/ui

MIT-licensed and intended to be customized rather than treated as a fixed template. ([GitHub][3])

[shadcn/ui](https://github.com/shadcn-ui/ui?utm_source=chatgpt.com)

### FINAL:

**Use.**

---

## 3. Parser

### Microsoft MarkItDown

Current project supports PDF, DOCX, XLSX and other document types with installable format-specific dependencies. ([GitHub][4])

[MarkItDown](https://github.com/microsoft/markitdown?utm_source=chatgpt.com)

### FINAL:

**Primary parser.**

---

## 4. PDF tables / coordinates

### pdfplumber

Current repo provides text, coordinates and table extraction; current repository metadata shows MIT licensing. ([GitHub][5])

[pdfplumber](https://github.com/jsvine/pdfplumber?utm_source=chatgpt.com)

### FINAL:

**Fallback/table/coordinate parser.**

---

# 29. Important decision: PDF Highlighter

## Don't make `react-pdf-highlighter` critical.

The reuse review correctly spotted the mismatch:

```text
Our flags → character offsets
PDF highlighter → PDF coordinates
```

and DOCX/XLSX make the problem worse. 

### FINAL:

## Plan A

Text document viewer:

```html
<mark>sentence</mark>
```

### Plan B

PDF box highlighting later through pdfplumber word coordinates.

This is one of the most important scope-risk decisions.

---

# 30. Retrieval stack

### BM25

`rank_bm25`

### Dense

`BAAI/bge-m3`

### Reranker

`BAAI/bge-reranker-v2-m3`

FlagEmbedding's current repo explicitly provides BGE-M3 and the multilingual BGE reranker family. ([GitHub][1])

[FlagEmbedding / BGE](https://github.com/FlagOpen/FlagEmbedding?utm_source=chatgpt.com)

### FINAL:

```text
BM25
+
BGE-M3
+
BGE-reranker-v2-m3
```

---

# 31. Vector database decision

## Don't start with pgvector.

For our 6–8 synthetic packs and small chunk counts:

### FINAL:

**NumPy cosine similarity first.**

If there is spare time:

**FAISS**

FAISS is currently MIT licensed and remains a solid optional local vector index. ([GitHub][6])

[FAISS](https://github.com/facebookresearch/faiss?utm_source=chatgpt.com)

Production slide:

> “At scale, replace this with pgvector.”

No need to actually introduce that complexity during the hackathon.

---

# 32. PII

### Microsoft Presidio

[Presidio](https://github.com/microsoft/presidio?utm_source=chatgpt.com)

Then custom:

```text
Aadhaar
PAN
GSTIN
IFSC
UPI
```

---

# 33. NER

### spaCy

Use for:

```text
PERSON
ORG
GPE
DATE
```

But **never let NER become the truth engine**.

---

# 34. Graph

### React Flow

Current project is MIT licensed and is intended for interactive node/edge flows. ([GitHub][7])

[React Flow / xyflow](https://github.com/xyflow/xyflow?utm_source=chatgpt.com)

### FINAL:

Use only for:

```text
Claim
Source
Counter-evidence
Risk
Impact
```

---

# 35. Proof

### Z3

[Z3](https://github.com/Z3Prover/z3?utm_source=chatgpt.com)

Use Python `z3-solver`.

Don't bring solver logic into frontend.

---

# 36. Mobile

### Expo

[Expo](https://github.com/expo/expo?utm_source=chatgpt.com)

Use:

```text
expo-camera
expo-router
expo-notifications
```

Share-menu remains conditional because native share modules can destabilize Expo builds. Your reuse plan already says to kill it by hour 10 if it creates problems. 

---

# 37. OCR

## Final priority

```text
pytesseract first
        ↓
PaddleOCR only if needed
```

Why?

Because the reuse review correctly identifies PaddleOCR's installation weight and makes Tesseract the first path. 

And:

```text
mobile
 ↓
image
 ↓
backend OCR
```

not local heavy processing.

---

# 38. Database final decision

Earlier docs leave:

> PostgreSQL vs SQLite

as an hour-0 decision. 

### I'm locking:

# **PostgreSQL + SQLModel from the FastAPI template**

Reason:

The official template currently already ships with PostgreSQL + SQLModel + Docker Compose. ([GitHub][2])

Don't spend hackathon time converting the base architecture just to use SQLite.

For the demo, keep Postgres local in Docker.

---

# 39. Final dependency philosophy

### Reuse:

```text
FastAPI template
shadcn
MarkItDown
pdfplumber
BM25
BGE-M3
BGE reranker
Presidio
spaCy
React Flow
TanStack Query
Z3
Expo
```

### Build ourselves:

```text
Source Fact Sheet
Grounding Guard
Numeric Engine
Claim Graph
Verification orchestration
Counter-evidence
Omission
Source Authority
Freshness
Conflict resolution
Policy Engine
Materiality
Blast Radius
Scoring
Living Trust
Challenge Mode
Injector
Passport
Hash Chain
```

That original-vs-built boundary is explicitly called out in the reuse plan. 

---

# 40. Runtime modes

Every AI call:

```text
LIVE
```

or:

```text
CACHED
```

or:

```text
OFFLINE
```

### LIVE

Real LLM.

### CACHED

Hero inputs replay cached outputs.

### OFFLINE

Rules + fast verifier + pre-cached hero result.

All calls:

```text
temperature = 0
JSON schema
1 retry
cache key =
hash(prompt + inputs + model)
```

This is explicitly part of the plan.  

---

# 41. Final API surface

```text
POST /auth/login

POST /audits
GET  /audits
GET  /audits/{id}

GET  /audits/{id}/flags

POST /flags/{id}/decision

POST /audits/{id}/rescore

POST /audits/{id}/challenge
POST /audits/{id}/inject

GET  /audits/{id}/proof
POST /proof/solve

POST /claims/{id}/trial

POST /sources/watch
GET  /sources/stale

GET /policies
PUT /policies

GET /settings
PUT /settings

GET /passport/{id}
GET /verify/{id}

GET /audit-log
GET /metrics

POST /ocr
POST /notify/register
```

These endpoints are already mapped in the detailed implementation plan. 

---

# 42. Final database

```text
users
audits
documents
facts
claims
evidence
flags
decisions
policies
proofs
passports
audit_log
challenges
notifications
```

`facts` is the important addition that makes the Source Fact Sheet a first-class object. 

---

# 43. Final data pipeline

## Source side

```text
Source files
 ↓
Parse
 ↓
Chunks
 ↓
Fact extraction
 ↓
Grounding guard
 ↓
Authority + freshness
 ↓
Fact Sheet
```

## AI document side

```text
AI document
 ↓
Parse
 ↓
Sentence offsets
 ↓
Claim extraction
 ↓
Field hints
```

## Comparison

```text
Claim
 ↓
Fact Sheet match
 ↓
Rule check
       OR
Retrieval
       ↓
Verifier
       ↓
Verdict
```

## Risk

```text
PII
+
Secrets
+
Commitments
+
URLs
+
Policy
+
Omission
```

## Final

```text
Materiality
 ↓
Score
 ↓
Reviewer
 ↓
Passport
```

---

# 44. Evaluation

This part **must not become fake theater**.

### Dataset

6–8 synthetic packs:

```text
contract
GST invoice
financial summary
project status
Hinglish summary
```

Each:

```text
1 clean
2–3 flawed
```

Hard negatives:

```text
Rs 1.2 Cr
12 million
1,20,00,000

R. Sharma
Rakesh vs Rajesh

XXXX-1234

valid-looking checksum-fail numbers
```

And three isolated sets:

```text
Tuning
Test
Injector
```

The final plan explicitly requires this separation. 

---

# 45. Metrics

Report:

```text
Precision
Recall
F1
False alarm rate
Latency
```

For:

```text
overall
numbers
dates
names
PII
commitments
```

Plus:

## Ablation

```text
A = retrieval only
B = + rules
C = + judge
D = + Z3 + policy
```

This makes the demo much more scientifically credible. 

---

# 46. Golden test

One hero contract.

Expected planted issues:

```text
₹50L vs ₹41.6L
15 Dec vs 22 Dec
30 days vs 45 days
99.9% guarantee unsupported
5-year warranty vs 12 months
PII leak
unlimited liability
```

The golden regression test should fail if a planted issue disappears.

This is one of the best safeguards in the whole project.

---

# 47. 36-hour final schedule

## H0–3 — FOUNDATION

### Everybody

```text
Fork
Rename
DB
Schemas
API
Hero documents
LICENSES.md
Runtime modes
```

---

## H3–8

### ML

Retrieval

### Backend

Parser + numeric engine

### Web

Dashboard + upload shell

### Mobile

Expo skeleton

### Data

First packs

---

## H8–12

### ML

Claims/fact extraction

### Backend

Fact guard + conflict

### Web

Result + DocViewer

### Mobile

Upload/OCR

### Data

Remaining packs + hard negatives

---

# 🚨 H12–14 CHECKPOINT 1

# **UPLOAD → FLAGS → HIGHLIGHTS**

This is the first non-negotiable milestone. 

---

# H14–18

### ML

Fast verifier + judge

### Backend

Scoring + PII + hash chain + Passport

### Web

Control Center workspace

### Mobile

Score card

### Data

Eval runner

---

# H18–22

### ML

Counter-evidence + omission

### Backend

Z3 + Policy

### Web

Evidence panel + decisions + verify

### Mobile

Swipe + QR

### Data

First actual metrics

---

# 🚨 H22–24 CHECKPOINT 2

# **REVIEWER LOOP + PASSPORT + QR + TAMPER**

The corrected reuse plan moved Passport/hash-chain earlier specifically so this checkpoint is achievable. 

---

# H22–27

Now add wow:

```text
Jhooth Chhupao
Injector
Proof Sandbox
Living Trust
Courtroom
```

---

# H27–30

Polish:

```text
Evidence Graph
Compare
Waterfall
Simulator
Admin
Performance
Deployment
```

---

# 🚨 H30

# **CODE FREEZE**

After this:

## ONLY

```text
bugs
tests
deployment
rehearsal
```

No feature creep. 

---

# H30–34

```text
5 demo rehearsals
slides
report
metrics
screenshots
backup video
```

---

# H34–36

```text
buffer
deployment verification
local backup
phone test
```

---

# 48. Team responsibilities

## Person 1 — ML / Retrieval

```text
BGE
BM25
reranker
claims
fact extraction
verifier
judge
courtroom
```

## Person 2 — Backend / Trust

```text
parser
facts
numeric
PII
policy
Z3
materiality
score
Passport
hash chain
Living Trust
```

## Person 3 — Web

```text
Submit
Control Center
DocViewer
Evidence
Reviewer
Proof
Graph
Simulator
```

## Person 4 — Mobile

```text
Expo
Camera
OCR trigger
Score
Swipe
QR
notifications
```

## Person 5 — Data/Eval/Demo

```text
packs
labels
hard negatives
Injector
metrics
ablation
demo
report
slides
```

The corrected plan uses exactly this five-role division. 

---

# 49. Feature cut order

Since you've said the whole solution is final, I'm **not removing features**. I'm only defining the order in which they can be sacrificed if a dependency fails.

### First sacrifice

```text
Hindi voice
Vision reading
Conformal slider
Graph polish
Blast radius polish
Private Mode
```

### Then

```text
Live source watcher
```

but keep manual:

**Re-audit**

### Never sacrifice

```text
Numeric engine
Evidence
Flags
Reviewer decision
AI vs Reviewed score
Proof Sandbox
Jhooth Chhupao
Injector
Hash chain
Passport
QR verify
```

This matches the current cut policy. 

---

# 50. Final demo sequence

Don't show 20 random features.

## 0–2 min

Problem + Tathya architecture.

## 2–5 min

Master contract:

```text
Upload
↓
Trust Score
↓
Heatmap
↓
Evidence
```

## 5–7 min

Judge edits value/date.

```text
score changes live
```

## 7–9 min

# Jhooth Injector

```text
10 mutations
real caught/missed result
```

## 9–11 min

# Living Trust

```text
new amendment
↓
stale evidence
↓
re-audit
```

## 11–13 min

# Passport

```text
Verified
↓
tamper DB
↓
Tampered
```

## 13–15 min

Metrics + ablation + architecture + honest limitations.

---

# 51. One thing we should NOT do on stage

Don't say:

> “Our model achieved 96% accuracy.”

unless your actual test run produces it.

Your plan already explicitly says every visible number has to come from the real run. 

Instead say:

> “On our labelled synthetic test set, this is the measured result.”

Much stronger.

---

# 52. License / originality story

Create:

# `LICENSES.md`

For each:

```text
package/model
version
license
where used
```

Official current sources confirm, for example, that the FastAPI full-stack template is MIT, shadcn is MIT, pdfplumber is MIT, FAISS is MIT, and React Flow is MIT. ([GitHub][2])

For model weights such as BGE/reranker/HHEM/judge, **verify the exact model card/license before locking the event environment** rather than relying on repo-level assumptions.

And in Q&A:

> **Built on:** open-source infrastructure.

> **Original:** Source Fact Sheet, grounding guard, verification orchestration, materiality, policy, Living Trust, challenge/injection, Passport, hash-chain workflow, evaluation suite.

That exact distinction is already documented in the final reuse plan. 

---

# 53. Final “Definition of Done”

Tathya is considered finished only when:

### Core

```text
Upload works
Parse works
Claims work
Evidence works
Rules work
Flags work
Score works
Reviewer works
```

### Security/audit

```text
Passport works
QR works
Tamper detection works
```

### Judge experience

```text
Edit works
Injector works
Proof works
```

### Quality

```text
Golden tests pass
Test-set metrics generated
Offline fallback works
```

### Presentation

```text
Deployed link works
Local backup works
Phone works
Demo rehearsed
```

---

# 54. Final decision summary

## Product

# **Tathya**

## Platforms

**Tathya Submit — Web**
**Tathya Control Center — Web**
**Tathya Scan — Mobile**
**Tathya Passport — Signed verification layer**

## Backend

**FastAPI**

## Database

# **PostgreSQL + SQLModel**

because the current official FastAPI full-stack template already ships that stack. ([GitHub][2])

## Retrieval

```text
BM25
+
BGE-M3
+
BGE-reranker-v2-m3
```

## Parsing

```text
MarkItDown
+
pdfplumber
```

## Rules

```text
Python
regex
dateparser
rapidfuzz
checksums
```

## PII

```text
Presidio
+
spaCy
+
custom Indian recognizers
```

## Proof

**Z3**

## Graph

**React Flow**

## Web UI

**React + TypeScript + Tailwind + shadcn**

## Mobile

**Expo**

## AI logic

# **Our own orchestration**

---

# 🏆 And finally, the entire project in one picture

```text
                         TATHYA
                            │
                ┌───────────┼───────────┐
                │           │           │
             SUBMIT      CONTROL       SCAN
              WEB        CENTER       MOBILE
                │           │           │
                └───────────┼───────────┘
                            ↓
                       FASTAPI API
                            ↓
                     ┌─────────────┐
                     │ AI TRUST    │
                     │    CORE     │
                     └──────┬──────┘
                            ↓
                    DOCUMENT PARSER
                            ↓
                    SOURCE FACT SHEET
                            ↓
                     CLAIM EXTRACTION
                            ↓
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
           RULES        RETRIEVAL        RISK
              │             │             │
        number/date    BM25+BGE       PII/secrets
        names/GST      reranker       promises
              │             │          URLs
              └─────────────┼─────────────┘
                            ↓
                         VERIFY
                            ↓
            SUPPORT / CONTRADICT / UNKNOWN
                            ↓
                    COUNTER-EVIDENCE
                            ↓
                     OMISSION CHECK
                            ↓
                      POLICY CHECK
                            ↓
                       Z3 PROOF
                            ↓
                     MATERIALITY
                            ↓
                     BUSINESS IMPACT
                            ↓
                       TRUST SCORE
                            ↓
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
           HEATMAP       EVIDENCE      WHAT TO
                         GRAPH          CHECK
              └─────────────┼─────────────┘
                            ↓
                       REVIEWER
                    ACCEPT / DISMISS / FIX
                            ↓
                     REVIEWED SCORE
                            ↓
                    TRUST PASSPORT
                            ↓
                    HASH + ECDSA + QR
                            ↓
                       VERIFY PAGE
```

**Bhai, ab ye genuinely “final” stage hai.** Product scope, USP, platform structure, AI architecture, reusable GitHub stack, original-work boundary, database choice, evaluation, roles, checkpoints and demo sequence all have a defined place. The remaining unresolved items are only **pre-event verification items** such as exact model-card licenses/IDs and whether native Expo features are stable on the actual build machine—not product-design uncertainty. The current plan itself flags those as things to verify before the event. 

And honestly, **ab next step feature discussion nahi hai — ab build sheet banana hai:** exact repos/commands, exact folder creation, exact dependency installation, exact `.env`, exact database schema, and then each person's first task at H0.

[1]: https://github.com/FlagOpen/FlagEmbedding?utm_source=chatgpt.com "GitHub - FlagOpen/FlagEmbedding: Retrieval and Retrieval-augmented LLMs · GitHub"
[2]: https://github.com/fastapi/full-stack-fastapi-template?utm_source=chatgpt.com "GitHub - fastapi/full-stack-fastapi-template: Full-stack web application template with FastAPI, React, SQLModel, PostgreSQL, Vite, Tailwind CSS, shadcn/ui, FastAPI Cloud, and Docker Compose. · GitHub"
[3]: https://github.com/shadcn-ui/ui?utm_source=chatgpt.com "GitHub - shadcn-ui/ui: A set of beautifully-designed, accessible components and a code distribution platform. Works with your favorite frameworks. Open Source. Open Code. · GitHub"
[4]: https://github.com/microsoft/markitdown?ref=sourcesmethods.com&utm_source=chatgpt.com "GitHub - microsoft/markitdown at sourcesmethods.com · GitHub"
[5]: https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt?utm_source=chatgpt.com "pdfplumber/LICENSE.txt at stable · jsvine/pdfplumber · GitHub"
[6]: https://github.com/facebookresearch/faiss/blob/main/LICENSE?utm_source=chatgpt.com "faiss/LICENSE at main · facebookresearch/faiss · GitHub"
[7]: https://github.com/xyflow/xyflow/blob/main/packages/react/README.md?utm_source=chatgpt.com "xyflow/packages/react/README.md at main · xyflow/xyflow · GitHub"