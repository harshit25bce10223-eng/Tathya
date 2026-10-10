import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import { auditApi, isAdmin, isReviewer } from "@/api/audits"
import { fields, operators, policyApi, type BusinessCondition, type PolicyDraft, type PolicyEvaluation, type PolicyRecord } from "@/api/policies"
import useAuth from "@/hooks/useAuth"
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges"
import { QueryState, StatusPill } from "./shared"

const labels: Record<string, string> = {contract_value: "Contract value", payment_terms_days: "Payment terms (days)", warranty_months: "Warranty (months)", delivery_date: "Delivery date", currency: "Contract currency", eq: "Equals", ne: "Does not equal", gt: "Greater than", gte: "At least", lt: "Less than", lte: "At most", exists: "Must be recorded"}
const defaultCondition = (): BusinessCondition => ({variable: "warranty_months", operator: "gte", value: 12, currency: null, reason: ""})
function newDraft(): PolicyDraft {return {name: "", description: "", is_active: false, change_note: "", rules: {target: "claim", audit_id: null, severity: "HIGH", conditions: [defaultCondition()]}}}
export function PolicyDetails({result}: {result: PolicyEvaluation}) {
  return <div className="policy-evaluation"><StatusPill status={result.state} />{result.conditions.map((c, index) => <article className="source-fact-record" key={index}><h4>{labels[c.variable] || c.variable}</h4><p>{c.explanation}</p>{c.reason && <p>Rule reason: {c.reason}</p>}<StatusPill status={c.state} />{c.evidence.map((e, evidenceIndex) => <blockquote key={`${e.document_id}-${evidenceIndex}`}>{e.quote}</blockquote>)}{c.evidence_count > c.evidence.length && <small>{c.evidence_count} evidence records contributed; the first {c.evidence.length} are shown.</small>}</article>)}</div>
}

export function PolicyStudio() {
  const {user, userError, retryUser} = useAuth()
  const queryClient = useQueryClient()
  const canRead = isReviewer(user), canEdit = isAdmin(user)
  const policies = useQuery({queryKey: ["business-policies"], queryFn: policyApi.list, enabled: !!canRead})
  const audits = useQuery({queryKey: ["audits"], queryFn: auditApi.list, enabled: !!canRead})
  const [draft, setDraft] = useState<PolicyDraft | null>(null)
  const [baseline, setBaseline] = useState("")
  const [previewAudit, setPreviewAudit] = useState("")
  const [notice, setNotice] = useState("")
  const dirty = !!draft && JSON.stringify(draft) !== baseline
  useUnsavedChanges(dirty)
  const save = useMutation({mutationFn: (body: PolicyDraft) => policyApi.save(body), onSuccess: async result => {
    setNotice(`Saved ${result.name}, version ${result.version}. Re-audit affected documents to apply this version.`)
    setDraft(null); setBaseline("")
    await Promise.all([queryClient.invalidateQueries({queryKey: ["business-policies"]}), queryClient.invalidateQueries({queryKey: ["policy-results"]}), queryClient.invalidateQueries({queryKey: ["audit-score"]}), queryClient.invalidateQueries({queryKey: ["verify"]})])
  }})
  const preview = useMutation({mutationFn: () => {
    if (!draft || !previewAudit) throw new Error("Choose an audit to preview this rule.")
    return policyApi.preview(previewAudit, draft.rules)
  }})
  const previewSignature = JSON.stringify([draft?.rules, previewAudit])
  const previousPreviewSignature = useRef(previewSignature)
  useEffect(() => {
    if (previousPreviewSignature.current !== previewSignature) preview.reset()
    previousPreviewSignature.current = previewSignature
  }, [previewSignature, preview.reset])
  const pending = save.isPending || preview.isPending
  const open = (record?: PolicyRecord) => {
    if (pending || (dirty && !window.confirm("Discard your unsaved policy changes?"))) return
    const next = record ? {...newDraft(), id: record.id, expected_version: record.version, name: record.name, description: record.description || "", is_active: record.is_active, rules: record.rules || newDraft().rules} : newDraft()
    setDraft(next); setBaseline(JSON.stringify(next)); save.reset(); preview.reset(); setNotice("")
  }
  const close = () => {if (!pending && (!dirty || window.confirm("Discard your unsaved policy changes?"))) {setDraft(null); save.reset(); preview.reset()}}
  const setCondition = (index: number, patch: Partial<BusinessCondition>) => {
    if (!draft) return
    setDraft({...draft, rules: {...draft.rules, conditions: draft.rules.conditions.map((c, i) => i === index ? {...c, ...patch} : c)}})
  }
  return <section className="product-panel policy-studio">
    <div className="panel-heading"><div><h2>Policy Studio</h2><p>Set business requirements for AI claims or source records. Rules apply when an audit runs.</p></div>{canEdit && <button type="button" className="primary-link" disabled={pending} onClick={() => open()}>Create policy</button>}</div>
    <QueryState loading={canRead && policies.isPending} error={userError || policies.error || audits.error} retry={() => {retryUser(); policies.refetch(); audits.refetch()}} />
    {notice && <p role="status" className="control-note">{notice}</p>}
    {user && !canRead && <p>Reviewer access is required to inspect business rules. Administrators can create and change policies.</p>}
    {canRead && !canEdit && <p>You can read policy rules and their version history. Policy editing requires administrator access.</p>}
    {draft && <form className="policy-editor" onSubmit={event => {event.preventDefault(); save.mutate(draft)}}><fieldset disabled={pending}><legend>{draft.id ? `Edit policy · version ${draft.expected_version}` : "New policy"}</legend>
      <label>Policy name<input required maxLength={255} value={draft.name} onChange={e => setDraft({...draft, name: e.target.value})} /></label>
      <label>Description<textarea maxLength={2000} value={draft.description} onChange={e => setDraft({...draft, description: e.target.value})} /></label>
      <div className="policy-editor-grid"><label>Check values in<select value={draft.rules.target} onChange={e => setDraft({...draft, rules: {...draft.rules, target: e.target.value as "claim" | "source"}})}><option value="claim">AI document claims</option><option value="source">Source records</option></select></label>
      <label>Applies to<select value={draft.rules.audit_id || ""} onChange={e => setDraft({...draft, rules: {...draft.rules, audit_id: e.target.value || null}})}><option value="">All audits</option>{audits.data?.data.map(a => <option key={a.id} value={a.id}>{a.title}</option>)}</select></label>
      <label>Violation severity<select value={draft.rules.severity} onChange={e => setDraft({...draft, rules: {...draft.rules, severity: e.target.value as PolicyDraft["rules"]["severity"]}})}>{["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"].map(s => <option key={s}>{s}</option>)}</select></label></div>
      <h3>Requirements</h3><p>Every requirement must pass. Missing, conflicting or incompatible values remain uncertain.</p>
      {draft.rules.conditions.map((c, index) => <div className="policy-condition" key={index}><h4>Requirement {index + 1}</h4><div className="policy-editor-grid"><label>Business field<select aria-label={`Business field ${index + 1}`} value={c.variable} onChange={e => {const variable = e.target.value as BusinessCondition["variable"]; setCondition(index, {variable, operator: variable === "currency" ? "eq" : c.operator, value: variable === "currency" ? "INR" : variable === "delivery_date" ? "" : c.operator === "exists" ? null : 0, currency: variable === "contract_value" ? "INR" : null})}}>{fields.map(f => <option key={f} value={f}>{labels[f]}</option>)}</select></label>
      <label>Requirement<select aria-label={`Requirement operator ${index + 1}`} value={c.operator} onChange={e => {const operator = e.target.value as BusinessCondition["operator"]; setCondition(index, {operator, value: operator === "exists" ? null : c.value ?? (c.variable === "currency" ? "INR" : c.variable === "delivery_date" ? "" : 0)})}}>{operators.filter(op => c.variable !== "currency" || ["eq", "ne", "exists"].includes(op)).map(op => <option key={op} value={op}>{labels[op]}</option>)}</select></label>
      {c.operator !== "exists" && <label>Required value<input aria-label={`Required value ${index + 1}`} type={c.variable === "delivery_date" ? "date" : c.variable === "currency" ? "text" : "number"} required min={0} step="any" maxLength={c.variable === "currency" ? 3 : undefined} value={c.value ?? ""} onChange={e => setCondition(index, {value: c.variable === "delivery_date" || c.variable === "currency" ? e.target.value.toUpperCase() : e.target.value === "" ? null : Number(e.target.value)})} /></label>}
      {c.variable === "contract_value" && <label>Currency<input aria-label={`Currency ${index + 1}`} required={c.operator !== "exists"} maxLength={3} pattern="[A-Z]{3}" placeholder="INR" value={c.currency || ""} onChange={e => setCondition(index, {currency: e.target.value.toUpperCase() || null})} /></label>}</div>
      <label>Why is this required?<input maxLength={500} value={c.reason} onChange={e => setCondition(index, {reason: e.target.value})} /></label><button type="button" className="secondary-button" disabled={draft.rules.conditions.length === 1} aria-label={`Remove requirement ${index + 1}`} onClick={() => setDraft({...draft, rules: {...draft.rules, conditions: draft.rules.conditions.filter((_, i) => i !== index)}})}>Remove requirement</button></div>)}
      <button type="button" className="secondary-button" disabled={draft.rules.conditions.length >= 20} onClick={() => setDraft({...draft, rules: {...draft.rules, conditions: [...draft.rules.conditions, defaultCondition()]}})}>Add requirement</button>
      <label className="policy-checkbox"><input type="checkbox" checked={draft.is_active} onChange={e => setDraft({...draft, is_active: e.target.checked})} />Enable this policy for future audit runs</label>
      <label>Reason for this version<textarea required minLength={3} maxLength={2000} value={draft.change_note} onChange={e => setDraft({...draft, change_note: e.target.value})} /></label>
      <div className="policy-preview-controls"><label>Preview on audit<select aria-label="Preview on audit" value={previewAudit} onChange={e => setPreviewAudit(e.target.value)}><option value="">Choose an audit</option>{audits.data?.data.map(a => <option key={a.id} value={a.id}>{a.title}</option>)}</select></label><button type="button" className="secondary-button" disabled={!previewAudit} onClick={() => preview.mutate()}>{preview.isPending ? "Checking…" : "Preview without saving"}</button></div>
      <div className="policy-actions"><button type="submit" className="primary-link" disabled={!dirty || draft.change_note.trim().length < 3 || !draft.name.trim()} aria-busy={save.isPending}>{save.isPending ? "Saving…" : "Save policy version"}</button><button type="button" className="secondary-button" onClick={close}>Cancel</button></div>
    </fieldset>{(save.error || preview.error) && <div role="alert" className="panel-state"><p>{(save.error || preview.error)?.message}</p><button type="button" className="secondary-button" onClick={() => {save.reset(); preview.reset(); policies.refetch()}}>Clear error and refresh policies</button></div>}{save.error && <p>For a version conflict, close this editor and reopen the current policy before saving.</p>}{preview.data && <div><h3>Draft preview — nothing saved</h3><PolicyDetails result={preview.data} /></div>}</form>}
    {policies.data && !policies.data.data.length && <div className="panel-state"><h3>No business policies yet</h3><p>Create a requirement, preview it on an audit, then enable it when ready.</p></div>}
    {policies.data?.data.map(p => <article className="source-fact-record" key={p.id}><div><h3>{p.name} · v{p.version}</h3><StatusPill status={p.is_active ? "Enabled" : "Disabled"} /></div><p>{p.description}</p>{p.rules ? <><p>Checks {p.rules.target === "claim" ? "AI document claims" : "source records"} · {p.rules.audit_id ? `Audit: ${audits.data?.data.find(a => a.id === p.rules?.audit_id)?.title || p.rules.audit_id}` : "All audits"} · {p.rules.severity}</p><ul>{p.rules.conditions.map((c, index) => <li key={index}>{labels[c.variable]}: {labels[c.operator]} {c.value} {c.currency}{c.reason ? ` — ${c.reason}` : ""}</li>)}</ul></> : <p role="status">This legacy rule is not connected to the typed audit policy engine. An administrator must migrate it before it can be enforced.</p>}{canEdit && <button type="button" className="secondary-button" disabled={pending} onClick={() => open(p)}>Edit {p.name}</button>}<details><summary>Version history</summary>{p.history.length ? p.history.slice().reverse().map(h => <div key={h.version}><strong>Version {h.version} · {h.is_active ? "enabled" : "disabled"}</strong><p>{h.change_note}</p><small>{h.changed_at || "Original timestamp not recorded"}</small></div>) : <p>No stored revision history for this legacy record.</p>}</details></article>)}
  </section>
}
