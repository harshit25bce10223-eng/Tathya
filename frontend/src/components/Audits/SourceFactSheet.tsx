import { SourceResolution } from "./SourceResolution"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { useEffect, useState } from "react"
import { isReviewer, formatDate } from "@/api/audits"
import { sourceFactsApi } from "@/api/sourceFacts"
import useAuth from "@/hooks/useAuth"
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges"
import { QueryState, StatusPill } from "./shared"

const label = (field: string) => ({contract_value: "Contract value", payment_terms_days: "Payment terms", warranty_months: "Warranty", delivery_date: "Delivery date"}[field] || field.replace(/_/g, " "))
function displayValue(value: string | number | null, unit: string | null) {
  if (typeof value !== "number") return value ?? "Not recorded"
  if (unit && /^[A-Z]{3}$/.test(unit)) {
    try { return new Intl.NumberFormat("en-IN", {style: "currency", currency: unit, maximumFractionDigits: 2}).format(value) } catch { /* Preserve an unfamiliar currency code. */ }
  }
  return `${new Intl.NumberFormat("en-IN").format(value)}${unit ? ` ${unit}${value === 1 ? "" : "s"}` : ""}`
}
export function SourceFactSheet({auditId, onPreview, onDirtyChange}: {auditId: string; onPreview: (id: string) => void; onDirtyChange: (dirty: boolean) => void}) {
  const queryClient = useQueryClient()
  const {user} = useAuth()
  const [resolutionDirty,setResolutionDirty]=useState(false)
  const [editing, setEditing] = useState("")
  const [authority, setAuthority] = useState("unspecified")
  const [note, setNote] = useState("")
  const facts = useQuery({queryKey: ["source-facts", auditId], queryFn: () => sourceFactsApi.get(auditId), enabled: !!auditId})
  const source = facts.data?.sources.find(s => s.document_id === editing)
  const dirty = !!source && (authority !== source.authority || note !== source.note)
  useUnsavedChanges(dirty)
  useEffect(() => {onDirtyChange(dirty||resolutionDirty); return () => onDirtyChange(false)}, [dirty, resolutionDirty, onDirtyChange])
  const save = useMutation({mutationFn: () => sourceFactsApi.updateContext(auditId, editing, authority, note), onSuccess: async () => {
    setEditing("")
    await Promise.all([queryClient.invalidateQueries({queryKey: ["source-facts", auditId]}), queryClient.invalidateQueries({queryKey: ["audit", auditId]}), queryClient.invalidateQueries({queryKey: ["audit-score", auditId]})])
  }})
  const close = () => {if (!save.isPending && (!dirty || window.confirm("Discard your unsaved source context?"))) {setEditing(""); save.reset()}}
  return <section className="product-panel source-fact-sheet">
    <div className="panel-heading"><div><h2>Source Fact Sheet</h2><p>Values extracted from current source versions, with their exact quotes.</p></div>{facts.data && <StatusPill status={`${facts.data.grounded_count} grounded facts`} />}</div>
    <QueryState loading={!!auditId && facts.isPending} error={facts.error} retry={() => facts.refetch()} />
    {!auditId && <p>Select a document set to inspect source facts.</p>}
    {facts.data && <>
      {!facts.data.source_count && <div className="panel-state"><h3>No separate source evidence</h3><p>Add a source document to this audit. The AI document cannot serve as its own source.</p></div>}
      {facts.data.fact_count > 0 && facts.data.grounded_count === 0 && <div className="panel-state"><h3>Source quotes need refreshing</h3><p>Earlier extraction records may lack quote provenance. Re-run this audit to refresh the facts.</p><Link to="/submit/$auditId" params={{auditId}} className="primary-link">Open audit</Link></div>}
      <SourceResolution auditId={auditId} data={facts.data} canReview={!!user&&!!isReviewer(user)} onDirtyChange={setResolutionDirty} />
      {facts.data.conflicts.map(conflict => <article className="source-fact-conflict" role="status" key={conflict.field}><h3>Conflicting {label(conflict.field)}</h3><p>{conflict.reason}</p></article>)}
      {!!Object.keys(facts.data.canonical).length && <div className="policy-grid">{Object.entries(facts.data.canonical).map(([field, item]) => <article key={field}><h3>{label(field)}</h3><p>{displayValue(item.value, item.unit)}</p><small>{item.reviewer_selected?"Reviewer-selected value · ":""}{item.fact_ids.length} source fact{item.fact_ids.length === 1 ? " agrees" : "s agree"}</small></article>)}</div>}
      {facts.data.sources.map(s => <article className="source-record" key={s.document_id}><div><h3>{s.filename}</h3><p>Version {s.version_no} · Uploaded {formatDate(s.uploaded_at)}</p></div><StatusPill status={`Authority: ${s.authority}`} /><p>{s.note || "No source authority note has been recorded."}</p>
        {user && isReviewer(user) && <button type="button" className="secondary-button" disabled={save.isPending} onClick={() => {if (dirty && !window.confirm("Discard your unsaved source context?")) return; setEditing(s.document_id); setAuthority(s.authority); setNote(s.note); save.reset()}}>Edit source context</button>}
        {editing === s.document_id && <form className="source-context-form" onSubmit={event => {event.preventDefault(); save.mutate()}}><fieldset disabled={save.isPending}><legend>Source authority context</legend><label>Reviewer-declared authority<select value={authority} onChange={event => setAuthority(event.target.value)}><option value="unspecified">Unspecified</option><option value="reference">Reference material</option><option value="approved">Approved business record</option><option value="official">Official record</option></select></label><label>Why should this source be used?<textarea required minLength={3} maxLength={2000} value={note} onChange={event => setNote(event.target.value)} /></label><p>This records reviewer context. It does not automatically verify the source or resolve conflicting values.</p><button type="submit" className="primary-link" disabled={!dirty || note.trim().length < 3} aria-busy={save.isPending}>{save.isPending ? "Saving…" : "Save source context"}</button><button type="button" className="secondary-button" onClick={close}>Cancel</button></fieldset><QueryState loading={false} error={save.error} retry={() => save.mutate()} /></form>}
      </article>)}
      {facts.data.source_count > 0 && !facts.data.fact_count && <div className="panel-state"><h3>No source facts extracted yet</h3><p>Run the audit to extract facts. Empty or unsupported source text may need a clearer document.</p></div>}
      <div className="source-facts-list">{facts.data.facts.map(f => <article className="source-fact-record" key={f.id}><div><h3>{label(f.field || f.subject)}: {displayValue(f.value, f.unit)}</h3><StatusPill status={f.grounded ? "Quote grounded" : "Needs grounding"} /></div><blockquote>{f.context_quote || f.quote || "A source quote was not recorded."}</blockquote><p>{f.filename} · Version {f.version_no} · {f.authority}</p><details><summary>Exact quote and location</summary><p>{f.quote || "Not available"}</p><pre>{JSON.stringify(f.location, null, 2)}</pre><small>Text hash: {f.text_hash}</small></details><button type="button" className="secondary-button" onClick={() => onPreview(f.document_id)}>Open source document</button></article>)}</div>
      {facts.data.source_count > 0 && <p className="control-note">Authority is reviewer-declared. Uploaded dates describe this system’s receipt of each file; original file modification dates are not supplied by browser uploads.</p>}
    </>}
  </section>
}
