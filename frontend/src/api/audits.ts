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
export interface AuditFlag {
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
export interface AuditSummary {
  audit: AuditRecord
  document_count: number
  flag_count: number
  open_flag_count: number
  claim_count: number
  passport: { trust_score: number; status: string; verify_token: string } | null
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
})
const documentSchema = z.object({
  id: z.string().min(1),
  filename: z.string(),
  kind: z.string(),
  version_no: z.number().int().positive(),
  text_hash: z.string(),
  is_current: z.boolean(),
})
const summarySchema = z.object({
  audit: auditSchema,
  document_count: z.number().int().nonnegative(),
  flag_count: z.number().int().nonnegative(),
  open_flag_count: z.number().int().nonnegative(),
  claim_count: z.number().int().nonnegative(),
  passport: z
    .object({
      trust_score: z.number().min(0).max(100),
      status: z.string(),
      verify_token: z.string(),
    })
    .nullable(),
})
export class AuditApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}
async function request<T>(
  path: string,
  init: RequestInit = {},
  schema?: z.ZodType<T>,
): Promise<T> {
  const token = localStorage.getItem("access_token")
  const headers = new Headers(init.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const response = await fetch(
    `${(import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "")}/api/v1/audits${path}`,
    { ...init, headers },
  )
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new AuditApiError(
      response.status,
      typeof body?.detail === "string"
        ? body.detail
        : `Request failed (${response.status}). Please try again.`,
    )
  }
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
export const auditApi = {
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
  create: (title: string, files: File[]) => {
    const body = new FormData()
    body.append("title", title)
    for (const file of files) body.append("files", file)
    return request<AuditRecord>("", { method: "POST", body }, auditSchema)
  },
  decision: (id: string, flagId: string, action: string, note: string) =>
    request(
      `/${encodeURIComponent(id)}/flags/${encodeURIComponent(flagId)}/decision`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, note }),
      },
    ),
  rescore: (id: string) =>
    request(`/${encodeURIComponent(id)}/rescore`, { method: "POST" }),
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
