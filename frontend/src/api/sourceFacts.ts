import { z } from "zod"
import { apiFetch, ServiceError } from "./transport"

const value = z.union([z.string(), z.number().finite()]).nullable()
const source = z.object({document_id: z.string().uuid(), filename: z.string(), version_no: z.number(), text_hash: z.string(), uploaded_at: z.string().nullable(), authority: z.string(), note: z.string(), context_updated_at: z.string().nullable()})
const fact = z.object({id: z.string().uuid(), document_id: z.string().uuid(), filename: z.string(), version_no: z.number(), text_hash: z.string(), field: z.string().nullable(), subject: z.string(), predicate: z.string(), value, unit: z.string().nullable(), quote: z.string(), context_quote: z.string(), location: z.record(z.string(), z.unknown()), grounded: z.boolean(), authority: z.string(), uploaded_at: z.string().nullable()})
const sheet = z.object({sources: z.array(source), facts: z.array(fact), canonical: z.record(z.string(), z.object({value, unit: z.string().nullable(), fact_ids: z.array(z.string()), reviewer_selected:z.boolean().default(false)})), conflicts: z.array(z.object({field: z.string(), fact_ids: z.array(z.string()), reason: z.string()})), source_count: z.number(), fact_count: z.number(), grounded_count: z.number(), authority_is_reviewer_declared: z.boolean(), resolutions:z.array(z.object({field:z.string(),document_id:z.string().nullable(),revision:z.string(),state:z.string(),active:z.boolean(),note:z.string(),version:z.number().nullable(),recorded_at:z.string().nullable(),actor_id:z.string()})).default([])})
export type SourceFactSheetData = z.infer<typeof sheet>
export const sourceFactsApi = {
  get: async (auditId: string): Promise<SourceFactSheetData> => {
    const response = await apiFetch(`/audits/${encodeURIComponent(auditId)}/source-facts`)
    const result = sheet.safeParse(await response.json())
    if (!result.success) throw new ServiceError(502, "Source facts could not be read. Refresh or try again later.")
    return result.data
  },
  resolve: async (auditId:string,field:string,document_id:string|null,expected_revision:string|null,note:string)=>{const response=await apiFetch(`/sources/${auditId}/resolve`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({field,document_id,expected_revision,note})});return sheet.parse(await response.json())},
  updateContext: async (auditId: string, documentId: string, authority: string, note: string) => {
    const response = await apiFetch(`/audits/${encodeURIComponent(auditId)}/documents/${encodeURIComponent(documentId)}/source-context`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({authority, note})})
    return response.json()
  },
}
