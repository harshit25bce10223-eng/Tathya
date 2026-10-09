import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { sourceFactsApi,type SourceFactSheetData } from "@/api/sourceFacts"
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges"
import { StatusPill } from "./shared"

export function SourceResolution({auditId,data,canReview,onDirtyChange}:{auditId:string;data:SourceFactSheetData;canReview:boolean;onDirtyChange:(dirty:boolean)=>void}) {
 const client=useQueryClient(),[field,setField]=useState(""),[document,setDocument]=useState(""),[note,setNote]=useState(""),[revision,setRevision]=useState<string|null>(null)
 const fields=Array.from(new Set([...data.conflicts.map(c=>c.field),...data.resolutions.map(r=>r.field)]))
 useUnsavedChanges(!!field&&!!note.trim())
 useEffect(()=>{onDirtyChange(!!field&&!!note.trim());return()=>onDirtyChange(false)},[field,note,onDirtyChange])
 const save=useMutation({mutationFn:()=>sourceFactsApi.resolve(auditId,field,document||null,revision,note),onSuccess:async()=>{setField("");setNote("");await Promise.all(["source-facts","audit-score","policy-results","audit-flags","claim-graph","verify"].map(key=>client.invalidateQueries({queryKey:key==="verify"?[key]:[key,auditId]})))}})
 if(!fields.length)return null
 return <section><h3>Reviewer source resolution</h3><p>Choose an exact source version for a business field and explain why. This records a reviewer decision; it does not independently authenticate the source. Re-audit after changes.</p>{fields.map(key=>{const selected=data.resolutions.find(r=>r.field===key);return <article className="source-fact-record" key={key}><h4>{key.replace(/_/g," ")}</h4><StatusPill status={selected?.state||"Unresolved"}/>{selected&&<p>{data.sources.find(s=>s.document_id===selected.document_id)?.filename||"Previous source version"} · {selected.note}</p>}{canReview&&<button type="button" className="secondary-button" disabled={save.isPending} onClick={()=>{if(field&&note.trim()&&!window.confirm("Discard your unsaved source selection?"))return;setField(key);setDocument(selected?.active?selected.document_id||"":"");setRevision(selected?.revision||null);setNote("");save.reset()}}>Resolve {key.replace(/_/g," ")}</button>}</article>})}
 {field&&<form className="source-context-form" onSubmit={e=>{e.preventDefault();save.mutate()}}><fieldset disabled={save.isPending}><legend>Resolve {field.replace(/_/g," ")}</legend><label>Source version<select value={document} onChange={e=>setDocument(e.target.value)}><option value="">Clear selection — keep all source evidence</option>{data.sources.filter(s=>data.facts.some(f=>f.document_id===s.document_id&&f.field===field&&f.grounded)).map(s=><option key={s.document_id} value={s.document_id}>{s.filename} · version {s.version_no}</option>)}</select></label><label>Reason for choosing this source<textarea required minLength={3} maxLength={2000} value={note} onChange={e=>setNote(e.target.value)}/></label><button type="submit" className="primary-link" disabled={note.trim().length<3}>Save source resolution</button><button type="button" className="secondary-button" onClick={()=>{if(!note.trim()||window.confirm("Discard your unsaved source selection?"))setField("")}}>Cancel</button></fieldset>{save.error&&<p role="alert">{save.error.message} Refresh the source facts before retrying a version conflict.</p>}</form>}
 </section>
}
