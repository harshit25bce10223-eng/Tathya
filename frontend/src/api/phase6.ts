import { apiFetch } from "./transport"
import { z } from "zod"

/**
 * Phase 6 — Adversarial Verification Types
 * Jhooth Chhupao (Challenge Library), Injector, Judge WOW, Proof Sandbox, Challenge Results
 */

// --- Jhooth Chhupao (Challenge Library) ---

export interface AdversarialScenario {
  id: string
  version: string
  name: string
  pattern_type: string
  claim_modification: string
  evidence_undermine: string
  injection_method: string
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NEGLIGIBLE"
  description: string
  meta?: Record<string, unknown>
}

export interface AdversarialScenarioCatalogue {
  scenarios: Record<string, AdversarialScenario>
  patterns: Record<string, {
    pattern_id: string
    name: string
    claim_modifications: string[]
    evidence_undermine_strategies: string[]
    injection_methods: string[]
    severity_distribution: string[]
  }>
  version_counter: number
}

export interface ChallengeScenarioListResponse {
  data: AdversarialScenario[]
  count: number
}

// --- Injector ---

export interface InjectionCandidate {
  candidate_id: string
  base_document_id: string | null
  original_hash: string
  candidate_hash: string
  injected_text: string
  location: Record<string, unknown>
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NEGLIGIBLE"
  pattern: string
  rationale: string
  diff: string[]
  created_at: string
  meta: Record<string, unknown>
}

export interface InjectionRequest {
  original_text: string
  injected_text: string
  pattern: string
  severity?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NEGLIGIBLE"
  base_document_id?: string
  location?: Record<string, unknown>
  rationale?: string
  meta?: Record<string, unknown>
}

export interface InjectionResult {
  candidate: InjectionCandidate
  changed: boolean
}

// --- Judge WOW ---

export interface AdversarialReview {
  review_id: string
  claim_text: string
  claim_category: string
  status: "verified" | "rejected" | "uncertain" | "error"
  confidence: number
  reason: string
  primary_evidence_id: string | null
  referenced_evidence_ids: string[]
  evidence_integrity_verified: boolean
  instruction_injection_detected: boolean
  injection_patterns: string[]
  judge_result?: {
    status: string
    confidence: number
    reason: string
    primary_evidence_id: string | null
    referenced_evidence_ids: string[]
    uncertainty_reason: string | null
    provider: string | null
    model: string | null
    cached: boolean
    validated: boolean
  }
  uncertainty_reason: string | null
  provider: string | null
  model: string | null
  created_at: string
  meta: Record<string, unknown>
}

export interface JudgeWowRequest {
  claim_text: string
  claim_category: string
  evidence_list: Array<{
    id: string
    quote: string
    location: string
    support_type: string
    score: number
  }>
  judge_result?: {
    status: string
    confidence: number
    reason: string
    primary_evidence_id: string | null
    referenced_evidence_ids: string[]
    uncertainty_reason: string | null
  }
  strict_injection_check?: boolean
}

export interface JudgeWowResponse {
  review: AdversarialReview
}

// --- Proof Sandbox ---

export interface ProofSolveRequest {
  goals?: string[]
  assumptions?: string[]
  numeric_constraints?: Array<Record<string, unknown>>
  max_timeout_seconds?: number
}

export interface ProofSolveResult {
  satisfiable: boolean | null
  model?: Record<string, string> | null
  proof?: string | null
  timed_out: boolean
  error?: string | null
}

// --- Challenge Results ---

export type ChallengeCategory =
  | "claim_injection"
  | "evidence_tampering"
  | "document_replacement"
  | "numeric_manipulation"
  | "date_manipulation"
  | "entity_swap"
  | "logic_inversion"
  | "omission_induction"
  | "policy_violation_injection"
  | "materiality_masking"

export type ChallengeOutcome = "detected" | "missed" | "false_positive" | "error"

export interface ChallengeResult {
  trial_id: string
  challenge_id: string
  category: ChallengeCategory
  expected_outcome: ChallengeOutcome
  actual_outcome: ChallengeOutcome
  system_score: number | null
  detection_latency_ms: number | null
  notes: string
  created_at: string
  meta: Record<string, unknown>
}

export function isChallengeCorrect(result: ChallengeResult): boolean {
  if (result.expected_outcome === "detected") {
    return result.actual_outcome === "detected"
  }
  if (result.expected_outcome === "missed") {
    return result.actual_outcome === "missed"
  }
  return false
}

export interface ChallengeMetrics {
  total_trials: number
  true_positives: number
  false_negatives: number
  false_positives: number
  errors: number
  true_positive_rate: number
  false_positive_rate: number
  precision: number
  f1_score: number
  accuracy: number
  by_category: Record<string, {
    total: number
    true_positives: number
    false_negatives: number
    false_positives: number
    expected_detected: number
    expected_missed: number
    true_negatives: number
  }>
}

export interface ChallengeResultsResponse {
  metrics: ChallengeMetrics
  quality_report: {
    sufficient_trials: boolean
    categories_tested: string[]
    trials_per_category: Record<string, number>
  }
  results: ChallengeResult[]
}

// --- API Schemas ---

const scenarioSchema = z.object({
  id: z.string().uuid(),
  version: z.string(),
  name: z.string(),
  pattern_type: z.string(),
  claim_modification: z.string(),
  evidence_undermine: z.string(),
  injection_method: z.string(),
  severity: z.enum(["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"]),
  description: z.string(),
  meta: z.record(z.string(), z.unknown()).optional(),
})

const scenarioListSchema = z.object({
  data: z.array(scenarioSchema),
  count: z.number().int().nonnegative(),
})

const injectionCandidateSchema = z.object({
  candidate_id: z.string().uuid(),
  base_document_id: z.string().uuid().nullable(),
  original_hash: z.string(),
  candidate_hash: z.string(),
  injected_text: z.string(),
  location: z.record(z.string(), z.unknown()),
  severity: z.enum(["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"]),
  pattern: z.string(),
  rationale: z.string(),
  diff: z.array(z.string()),
  created_at: z.iso.datetime({ offset: true }),
  meta: z.record(z.string(), z.unknown()),
})

const injectionResultSchema = z.object({
  candidate: injectionCandidateSchema,
  changed: z.boolean(),
})

const judgeWowSchema = z.object({
  review_id: z.string().uuid(),
  claim_text: z.string(),
  claim_category: z.string(),
  status: z.enum(["verified", "rejected", "uncertain", "error"]),
  confidence: z.number().min(0).max(1),
  reason: z.string(),
  primary_evidence_id: z.string().uuid().nullable(),
  referenced_evidence_ids: z.array(z.string().uuid()),
  evidence_integrity_verified: z.boolean(),
  instruction_injection_detected: z.boolean(),
  injection_patterns: z.array(z.string()),
  judge_result: z.object({
    status: z.string(),
    confidence: z.number().min(0).max(1),
    reason: z.string(),
    primary_evidence_id: z.string().uuid().nullable(),
    referenced_evidence_ids: z.array(z.string().uuid()),
    uncertainty_reason: z.string().nullable(),
    provider: z.string().nullable(),
    model: z.string().nullable(),
    cached: z.boolean(),
    validated: z.boolean(),
  }).optional(),
  uncertainty_reason: z.string().nullable(),
  provider: z.string().nullable(),
  model: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  meta: z.record(z.string(), z.unknown()),
})

const judgeWowResponseSchema = z.object({
  review: judgeWowSchema,
})

const proofSolveResultSchema = z.object({
  satisfiable: z.boolean().nullable(),
  model: z.record(z.string(), z.string()).nullable().optional(),
  proof: z.string().nullable(),
  timed_out: z.boolean(),
  error: z.string().nullable(),
})

const challengeCategorySchema = z.enum([
  "claim_injection",
  "evidence_tampering",
  "document_replacement",
  "numeric_manipulation",
  "date_manipulation",
  "entity_swap",
  "logic_inversion",
  "omission_induction",
  "policy_violation_injection",
  "materiality_masking",
])

const challengeOutcomeSchema = z.enum(["detected", "missed", "false_positive", "error"])

const challengeResultSchema = z.object({
  trial_id: z.string().uuid(),
  challenge_id: z.string().uuid(),
  category: challengeCategorySchema,
  expected_outcome: challengeOutcomeSchema,
  actual_outcome: challengeOutcomeSchema,
  system_score: z.number().nullable(),
  detection_latency_ms: z.number().int().nonnegative().nullable(),
  notes: z.string(),
  created_at: z.iso.datetime({ offset: true }),
  meta: z.record(z.string(), z.unknown()),
})

const categoryMetricsSchema = z.object({
  total: z.number().int().nonnegative(),
  true_positives: z.number().int().nonnegative(),
  false_negatives: z.number().int().nonnegative(),
  false_positives: z.number().int().nonnegative(),
  expected_detected: z.number().int().nonnegative(),
  expected_missed: z.number().int().nonnegative(),
  true_negatives: z.number().int().nonnegative(),
})

const challengeMetricsSchema = z.object({
  total_trials: z.number().int().nonnegative(),
  true_positives: z.number().int().nonnegative(),
  false_negatives: z.number().int().nonnegative(),
  false_positives: z.number().int().nonnegative(),
  errors: z.number().int().nonnegative(),
  true_positive_rate: z.number().min(0).max(1),
  false_positive_rate: z.number().min(0).max(1),
  precision: z.number().min(0).max(1),
  f1_score: z.number().min(0).max(1),
  accuracy: z.number().min(0).max(1),
  by_category: z.record(z.string(), categoryMetricsSchema),
})

const challengeResultsSchema = z.object({
  metrics: challengeMetricsSchema,
  quality_report: z.object({
    sufficient_trials: z.boolean(),
    categories_tested: z.array(z.string()),
    trials_per_category: z.record(z.string(), z.number().int().nonnegative()),
  }),
  results: z.array(challengeResultSchema),
})

// --- API Request Helper ---

async function requestRoot<T>(
  path: string,
  init?: RequestInit,
  schema?: z.ZodType<T>,
): Promise<T> {
  const response = await apiFetch(path, init)
  const body = await response.json()
  if (!schema) return body
  const result = schema.safeParse(body)
  if (!result.success)
    throw new Error("The service returned incomplete data. Please refresh or try again later.")
  return result.data
}

// --- Phase 6 API Client ---

export const challengeApi = {
  // Jhooth Chhupao - Challenge Library
  listScenarios: () =>
    requestRoot<ChallengeScenarioListResponse>("/challenges/scenarios", undefined, scenarioListSchema),

  getScenario: (version: string) =>
    requestRoot<AdversarialScenario>(`/challenges/scenarios/${encodeURIComponent(version)}`, undefined, scenarioSchema),

  // Injector
  generateCandidate: (payload: InjectionRequest) =>
    requestRoot<InjectionResult>("/inject/candidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }, injectionResultSchema),

  // Judge WOW
  runAdversarialReview: (payload: JudgeWowRequest) =>
    requestRoot<JudgeWowResponse>("/judge/adversarial", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }, judgeWowResponseSchema),

  // Proof Sandbox
  solveProof: (payload: ProofSolveRequest) =>
    requestRoot<ProofSolveResult>("/proof/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }, proofSolveResultSchema),

  // Challenge Results
  getResults: () =>
    requestRoot<ChallengeResultsResponse>("/challenges/results", undefined, challengeResultsSchema),
}