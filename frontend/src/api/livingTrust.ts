import { z } from "zod"
import { apiFetch } from "./transport"
const graph = z.object({nodes: z.array(z.object({id:z.string(),kind:z.enum(["document","claim","evidence"]),label:z.string(),document_id:z.string(),version:z.number().optional(),role:z.string().optional(),status:z.string().optional(),location:z.string().optional(),reviewer_selected:z.boolean().optional()})),edges:z.array(z.object({from:z.string(),to:z.string(),relation:z.string()})),offset:z.number(),limit:z.number(),total_claims:z.number(),has_more:z.boolean(),assessment_stale:z.boolean()})
const watch = z.object({enabled:z.boolean(),auto_reaudit:z.boolean(),audit_id:z.string(),inbox_path:z.string(),files:z.array(z.object({filename:z.string(),state:z.string(),raw_sha256:z.string().nullable(),error:z.string().nullable()})),has_more_files:z.boolean(),changed_count:z.number(),poll_seconds:z.number()})
const checked = z.object({imported:z.array(z.object({filename:z.string(),document_id:z.string(),version:z.number()})),errors:z.array(z.object({filename:z.string(),error:z.string()})),busy:z.boolean(),reaudit_queued:z.boolean()})
async function read<T>(path:string,schema:z.ZodType<T>,init?:RequestInit):Promise<T>{return schema.parse(await (await apiFetch(path,init)).json())}
export type ClaimGraphData = z.infer<typeof graph>
export const livingTrustApi = {
 graph:(id:string,offset=0)=>read(`/audits/${id}/claim-graph?offset=${offset}&limit=25`,graph),
 watch:(id:string)=>read(`/sources/${id}/stale`,watch),
 configure:(audit_id:string,enabled:boolean,auto_reaudit:boolean,note:string)=>read("/sources/watch",watch,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({audit_id,enabled,auto_reaudit,note})}),
 check:(id:string)=>read(`/sources/${id}/check`,checked,{method:"POST"}),
 upload:async(id:string,files:File[],signal:AbortSignal)=>{const body=new FormData();body.set("source_only","true");files.forEach(file=>body.append("files",file));await apiFetch(`/audits/${id}/documents`,{method:"POST",body,signal})},
}
