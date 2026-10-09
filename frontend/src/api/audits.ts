import { apiFetch, ServiceError, uploadAudit } from "./transport"
import { z } from "zod"

export interface AuditRecord {
  id: string
  title: string
  status: string
  created_at: string | null
  updated_at: string | null
  error_message?: string | null
  failed_stage?: string | null
}
export interface AuditEvidence { id: string; quote: string; location_json: string; support_type: string; score: number }
export interface ScoreBreakdown {
  scoring_version: string; ai_score: number; reviewed_score: number;
  score_status: "assessed" | "partial_verification" | "insufficient_verification";
  score_limit_reason: string | null;
  coverage: {total_claims: number; checked_claims: number; grounded_claims: number; supported: number; contradicted: number; unsupported: number; uncertain: number; extracted: number; source_count: number; checked_percent: number | null; evidence_percent: number | null};
  sub_scores: Record<string, number | null>;
  finding_contributions: Array<{flag_id: string; severity: string; penalty: number; included_in_reviewed: boolean; reason: string}>;
}
export interface AuditFlag {
  claim_text?: string | null
  evidence?: AuditEvidence[]
  id: string
  audit_id: string
  document_id: string
  claim_id: string | null
  type: string
  severity: string
  materiality: string
  reason: string
  suggested_fix: string
  status: string
  reviewer_note: string | null
  impact_score: number
  location_json: string
}
export interface AuditDocument {
  id: string
  filename: string
  kind: string
  version_no: number
  text_hash: string
  is_current: boolean
}
export interface AuditPassport {
  id: string
  audit_id: string
  verify_token: string
  document_hash: string
  chain_head: string
  signature: string
  trust_score: number
  status: string
  ai_score: number
  reviewed_score: number
  score_band: string
  critical_risk: boolean
  finding_summary: string
  review_status: string
  revision: number
  issued_at: string | null
  created_at: string | null
}
export interface AuditSummary {
  audit: AuditRecord
  document_count: number
  flag_count: number
  open_flag_count: number
  claim_count: number
  fact_count: number
  passport: AuditPassport | null
  verify_token: string | null
}
const auditSchema = z.object({
  id: z.string().min(1),
  title: z.string(),
  status: z.string().min(1),
  created_at: z.iso.datetime({ offset: true }).nullable(),
  updated_at: z.iso.datetime({ offset: true }).nullable(),
  error_message: z.string().nullable().optional(),
  failed_stage: z.string().nullable().optional(),
})
const flagSchema = z.object({
  id: z.string().min(1),
  audit_id: z.string().min(1),
  document_id: z.string().min(1),
  claim_id: z.string().nullable(),
  type: z.string(),
  severity: z.string().min(1),
  materiality: z.string(),
  reason: z.string(),
  suggested_fix: z.string(),
  status: z.string().min(1),
  reviewer_note: z.string().nullable(),
  impact_score: z.number().finite(),
  location_json: z.string(),
  claim_text: z.string().nullable().optional(),
  evidence: z.array(z.object({ id: z.string(), quote: z.string(), location_json: z.string(), support_type: z.string(), score: z.number() })).default([]),
})
const documentSchema = z.object({
  id: z.string().min(1),
  filename: z.string(),
  kind: z.string(),
  version_no: z.number().int().positive(),
  text_hash: z.string(),
  is_current: z.boolean(),
})
const passportSchema = z.object({
  id: z.string().uuid(),
  audit_id: z.string().uuid(),
  verify_token: z.string().min(1),
  document_hash: z.string(),
  chain_head: z.string(),
  signature: z.string(),
  trust_score: z.number().min(0).max(100),
  status: z.string().min(1),
  ai_score: z.number().min(0).max(100),
  reviewed_score: z.number().min(0).max(100),
  score_band: z.string().min(1),
  critical_risk: z.boolean(),
  finding_summary: z.string(),
  review_status: z.string().min(1),
  revision: z.number().int().nonnegative(),
  issued_at: z.iso.datetime({ offset: true }).nullable(),
  created_at: z.iso.datetime({ offset: true }).nullable(),
})
const summarySchema = z.object({
  audit: auditSchema,
  document_count: z.number().int().nonnegative(),
  flag_count: z.number().int().nonnegative(),
  open_flag_count: z.number().int().nonnegative(),
  claim_count: z.number().int().nonnegative(),
  fact_count: z.number().int().nonnegative().default(0),
  passport: passportSchema.nullable(),
  verify_token: z.string().nullable(),
})
export class AuditApiError extends ServiceError {}
async function request<T>(
  path: string,
  init: RequestInit = {},
  schema?: z.ZodType<T>,
): Promise<T> {
  const response = await apiFetch(`/audits${path}`, init)
  const body = await response.json()
  if (!schema) return body
  const result = schema.safeParse(body)
  if (!result.success)
    throw new AuditApiError(
      502,
      "The audit service returned incomplete data. Please refresh or try again later.",
    )
  return result.data
}

async function requestRoot<T>(
  path: string,
  init: RequestInit = {},
  schema?: z.ZodType<T>,
): Promise<T> {
  const response = await apiFetch(path, init)
  const body = await response.json()
  if (!schema) return body
  const result = schema.safeParse(body)
  if (!result.success)
    throw new AuditApiError(
      502,
      "The audit service returned incomplete data. Please refresh or try again later.",
    )
  return result.data
}

export interface ControlMetricsResponse {
  total_audits: number
  audits_last_7_days: number
  total_findings: number
  pending_review_count: number
  avg_reviewed_score: number
  avg_ai_score: number
  critical_risk_count: number
  passports_issued: number
  verify_token_views_last_7_days: number | null
  challenge_count: number
  users_with_reviewer_role: number
  audits_by_score_band: Record<string, number>
  top_severity_counts: Record<string, number>
  generated_at: string
}

const metricsSchema = z.object({
  total_audits: z.number().int().nonnegative(),
  audits_last_7_days: z.number().int().nonnegative(),
  total_findings: z.number().int().nonnegative(),
  pending_review_count: z.number().int().nonnegative(),
  avg_reviewed_score: z.number().min(0).max(100),
  avg_ai_score: z.number().min(0).max(100),
  critical_risk_count: z.number().int().nonnegative(),
  passports_issued: z.number().int().nonnegative(),
  verify_token_views_last_7_days: z.number().int().nonnegative().nullable(),
  challenge_count: z.number().int().nonnegative(),
  users_with_reviewer_role: z.number().int().nonnegative(),
  audits_by_score_band: z.record(z.string(), z.number().int().nonnegative()),
  top_severity_counts: z.record(z.string(), z.number().int().nonnegative()),
  generated_at: z.iso.datetime({ offset: true }),
})

export interface InjectionPayload {
  inject_claim?: string
  inject_flag?: { reason?: string; suggested_fix?: string; impact_score?: number; materiality?: string }
  severity?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NEGLIGIBLE"
  target_document_id?: string
  target_location?: Record<string, unknown>
  include_grounding_match?: boolean
}

export const auditApi = {
  run: (id: string) => request(`/${encodeURIComponent(id)}/run`, { method: "POST" }),
  scoreBreakdown: (id: string) => request<ScoreBreakdown>(`/${encodeURIComponent(id)}/score-breakdown`, {}, z.object({
    scoring_version: z.string(), ai_score: z.number(), reviewed_score: z.number(),
    score_status: z.enum(["assessed", "partial_verification", "insufficient_verification"]), score_limit_reason: z.string().nullable(),
    coverage: z.object({total_claims: z.number(), checked_claims: z.number(), grounded_claims: z.number(), supported: z.number(), contradicted: z.number(), unsupported: z.number(), uncertain: z.number(), extracted: z.number(), source_count: z.number(), checked_percent: z.number().nullable(), evidence_percent: z.number().nullable()}),
    sub_scores: z.record(z.string(), z.number().nullable()),
    finding_contributions: z.array(z.object({flag_id: z.string(), severity: z.string(), penalty: z.number(), included_in_reviewed: z.boolean(), reason: z.string()})),
  })),
  list: () =>
    request<{ data: AuditRecord[]; count: number }>(
      "?limit=100",
      {},
      z.object({
        data: z.array(auditSchema),
        count: z.number().int().nonnegative(),
      }),
    ),
  summary: (id: string) =>
    request<AuditSummary>(`/${encodeURIComponent(id)}`, {}, summarySchema),
  flags: (id: string) =>
    request<{ data: AuditFlag[]; count: number }>(
      `/${encodeURIComponent(id)}/flags`,
      {},
      z.object({
        data: z.array(flagSchema),
        count: z.number().int().nonnegative(),
      }),
    ),
  documents: (id: string) =>
    request<{ data: AuditDocument[]; count: number }>(
      `/${encodeURIComponent(id)}/documents`,
      {},
      z.object({
        data: z.array(documentSchema),
        count: z.number().int().nonnegative(),
      }),
    ),
  documentText: (auditId: string, documentId: string) =>
    request<{ id: string; filename: string; raw_text: string; normalized_text?: string; text_hash: string }>(
      `/${encodeURIComponent(auditId)}/documents/${encodeURIComponent(documentId)}/text`,
      {},
      z.object({
        id: z.string(),
        filename: z.string(),
        raw_text: z.string(),
        normalized_text: z.string().optional(),
        text_hash: z.string(),
      }),
    ),
  create: async (title: string, files: File[], signal?: AbortSignal, onProgress?: (percent: number) => void) => {
    const body = new FormData()
    body.append("title", title)
    for (const file of files) body.append("files", file)
    return auditSchema.parse(await uploadAudit(body, signal, onProgress))
  },
  decision: (id: string, flagId: string, action: string, reason: string, remediation = "") =>
    request(
      `/${encodeURIComponent(id)}/flags/${encodeURIComponent(flagId)}/decision`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, note: reason, reason, remediation }),
      },
    ),
  rescore: (id: string) =>
    request(`/${encodeURIComponent(id)}/rescore`, { method: "POST" }),
  metrics: () =>
    requestRoot<ControlMetricsResponse>("/metrics", {}, metricsSchema),
  proofSolve: (payload: { goals: string[]; assumptions?: string[]; numeric_constraints?: Array<Record<string, unknown>>; max_timeout_seconds?: number }) =>
    requestRoot(
      "/proof/solve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    ),
}
export const isRunning = (status: string) =>
  ["queued", "processing"].includes(status.toLowerCase())
export const isReviewer = (
  user: { is_superuser?: boolean; role?: string } | null | undefined,
) =>
  !!user &&
  (user.is_superuser || ["reviewer", "admin"].includes(user.role ?? ""))
export const formatDate = (date: string | null) =>
  date
    ? new Intl.DateTimeFormat("en-IN", {
        day: "numeric",
        month: "short",
        timeZone: "Asia/Kolkata",
      }).format(new Date(date))
    : "—"
