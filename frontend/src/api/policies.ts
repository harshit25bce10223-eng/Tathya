import { z } from "zod"
import { apiFetch, ServiceError } from "./transport"

export const fields = ["contract_value", "payment_terms_days", "warranty_months", "delivery_date", "currency"] as const
export const operators = ["eq", "ne", "gt", "gte", "lt", "lte", "exists"] as const
const condition = z.object({variable: z.enum(fields), operator: z.enum(operators), value: z.union([z.number().finite(), z.string()]).nullable(), currency: z.string().nullable(), reason: z.string()})
const rules = z.object({target: z.enum(["claim", "source"]), audit_id: z.string().uuid().nullable(), severity: z.enum(["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"]), conditions: z.array(condition)})
const policy = z.object({id: z.string().uuid(), name: z.string(), description: z.string().nullable(), is_active: z.boolean(), version: z.number().int().positive(), supported: z.boolean(), rules: rules.nullable(), updated_at: z.string().nullable(), history: z.array(z.object({version: z.number(), name: z.string(), change_note: z.string(), changed_at: z.string().optional(), is_active: z.boolean()}))})
const evaluation = z.object({state: z.enum(["satisfied", "violation", "uncertain", "not_applicable"]), target: z.enum(["claim", "source"]), severity: z.string(), conditions: z.array(condition.extend({actual_value: z.union([z.string(), z.number()]).nullable(), actual_unit: z.string().nullable(), state: z.string(), explanation: z.string(), evidence_count: z.number(), evidence: z.array(z.object({value: z.union([z.string(), z.number()]), unit: z.string().nullable(), quote: z.string(), document_id: z.string().uuid(), claim_id: z.string().uuid().nullable(), location: z.record(z.string(), z.unknown())}))}))})
export type BusinessRules = z.infer<typeof rules>
export type BusinessCondition = z.infer<typeof condition>
export type PolicyRecord = z.infer<typeof policy>
export type PolicyEvaluation = z.infer<typeof evaluation>
export interface PolicyWrite {name: string; description: string; is_active: boolean; rules: BusinessRules; change_note: string}
export interface PolicyDraft extends PolicyWrite {id?: string; expected_version?: number}
const auditEvaluation = evaluation.extend({policy_id: z.string().uuid(), policy_name: z.string(), policy_version: z.number(), flag_id: z.string().uuid().optional()})
const recorded = z.object({evaluations: z.array(auditEvaluation), stale: z.boolean(), evaluated_at: z.string().nullable(), active_policy_count: z.number()})
async function request<T>(path: string, schema: z.ZodType<T>, body?: unknown, method = "GET") {
  const response = await apiFetch(path, body ? {method, headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)} : {method})
  const parsed = schema.safeParse(await response.json())
  if (!parsed.success) throw new ServiceError(502, "The policy service returned incomplete data. Refresh or try again later.")
  return parsed.data
}
export const policyApi = {
  list: () => request("/policies", z.object({data: z.array(policy), count: z.number()})),
  save: (draft: PolicyDraft) => {
    const {id, ...body} = draft
    return request(`/policies${id ? `/${encodeURIComponent(id)}` : ""}`, policy, body, id ? "PUT" : "POST")
  },
  preview: (auditId: string, businessRules: BusinessRules) => request("/policies/preview", evaluation.extend({preview_only: z.boolean()}), {audit_id: auditId, rules: businessRules}, "POST"),
  results: (auditId: string) => request(`/audits/${encodeURIComponent(auditId)}/policy-results`, recorded),
}
