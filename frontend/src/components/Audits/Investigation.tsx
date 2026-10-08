import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  FileText,
  ShieldCheck,
} from "lucide-react"
import { useState } from "react"
import { auditApi } from "@/api/audits"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { QueryState, StatusPill, useAudit } from "./shared"

export function Investigation({ auditId }: { auditId: string }) {
  const { summary, flags, documents } = useAudit(auditId)
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [note, setNote] = useState("")
  const [saved, setSaved] = useState("")
  const selected =
    flags.data?.data.find((flag) => flag.id === selectedId) ??
    flags.data?.data[0]
  const document = documents.data?.data.find(
    (doc) => doc.id === selected?.document_id,
  )
  const decision = useMutation({
    mutationFn: (action: string) =>
      auditApi.decision(auditId, selected!.id, action, note.trim()),
    onSuccess: () => {
      setSaved(
        "Decision saved. Recalculate the score when your review is complete.",
      )
      queryClient.invalidateQueries({ queryKey: ["audit-flags", auditId] })
      queryClient.invalidateQueries({ queryKey: ["audit", auditId] })
    },
  })
  const rescore = useMutation({
    mutationFn: () => auditApi.rescore(auditId),
    onSuccess: () => {
      setSaved("Score recalculated.")
      queryClient.invalidateQueries({ queryKey: ["audit", auditId] })
    },
  })
  if (!summary.data)
    return (
      <QueryState
        loading={summary.isPending}
        error={summary.error}
        retry={() => summary.refetch()}
      />
    )
  const data = summary.data
  let location: Record<string, unknown> = {}
  try {
    const parsed = JSON.parse(selected?.location_json ?? "{}")
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed))
      location = parsed
  } catch {
    /* Never invent a citation. */
  }
  return (
    <div className="product-page investigation-page">
      <Link to="/control/queue" className="back-link">
        <ArrowLeft size={14} /> Review queue
      </Link>
      <div className="product-heading">
        <div>
          <span className="eyebrow">INVESTIGATION WORKSPACE</span>
          <h1>{data.audit.title}</h1>
          <p>
            {data.flag_count} findings · {data.open_flag_count} awaiting a
            decision
          </p>
        </div>
        <Link
          to="/submit/$auditId"
          params={{ auditId }}
          className="secondary-link"
        >
          View result <ArrowUpRight size={14} />
        </Link>
      </div>
      <div className="workspace-topline">
        <span>
          <ShieldCheck size={15} /> Score{" "}
          <strong>{data.passport?.trust_score ?? "—"}</strong>
          <span className="text-muted-foreground">/ 100</span>
        </span>
        <StatusPill status={data.audit.status} />
        <LoadingButton
          variant="outline"
          loading={rescore.isPending}
          onClick={() => rescore.mutate()}
          disabled={!selected || decision.isPending}
        >
          Recalculate score
        </LoadingButton>
      </div>
      <QueryState
        loading={flags.isPending}
        error={flags.error}
        retry={() => flags.refetch()}
      />
      {flags.data?.data.length === 0 && (
        <div className="product-panel panel-state">
          <ShieldCheck size={24} />
          <h2>No findings to review</h2>
          <p>Open the result to inspect the document set and audit status.</p>
        </div>
      )}
      {selected && (
        <div className="investigation-grid">
          <aside className="product-panel findings-list">
            <div className="panel-heading">
              <h2>Findings</h2>
              <span className="quiet-label">{flags.data?.data.length}</span>
            </div>
            {flags.data?.data.map((flag, index) => (
              <button
                type="button"
                className={`finding-choice ${flag.id === selected.id ? "selected" : ""}`}
                key={flag.id}
                onClick={() => {
                  setSelectedId(flag.id)
                  setNote("")
                  setSaved("")
                  decision.reset()
                }}
                disabled={decision.isPending}
              >
                <span className="quiet-label">
                  {String(index + 1).padStart(2, "0")}{" "}
                  <span
                    className={`severity-dot ${flag.severity.toLowerCase()}`}
                  />
                  {flag.severity}
                </span>
                <strong>{flag.type.replace(/_/g, " ") || "Finding"}</strong>
                <small>{flag.reason}</small>
                <StatusPill status={flag.status} />
              </button>
            ))}
          </aside>
          <section className="product-panel verdict-panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">AI FINDING</span>
                <h2 className="mt-2">
                  {selected.type.replace(/_/g, " ") || "Finding"}
                </h2>
              </div>
              <StatusPill status={selected.severity} />
            </div>
            <div className="verdict-facts">
              <div>
                <span>Materiality</span>
                <strong>{selected.materiality}</strong>
              </div>
              <div>
                <span>Score impact</span>
                <strong>−{Math.max(0, selected.impact_score)} points</strong>
              </div>
            </div>
            <h3 className="field-label mt-6">Explanation</h3>
            <p className="verdict-explanation">
              {selected.reason ||
                "No explanation was returned for this finding."}
            </p>
            <div className="verdict-recommendation">
              <span className="eyebrow">SUGGESTED NEXT STEP</span>
              <p>
                {selected.suggested_fix ||
                  "Inspect the document reference and record your decision."}
              </p>
            </div>
            <div className="field-checks">
              <span>
                <Check size={13} /> Finding ID present
              </span>
              <span className={!document ? "missing" : ""}>
                {document ? <Check size={13} /> : <FileText size={13} />}{" "}
                {document
                  ? "Document version matched"
                  : "Document reference unavailable"}
              </span>
            </div>
            <details className="structured-output">
              <summary>Structured finding · JSON</summary>
              <pre>
                {JSON.stringify(
                  {
                    finding_id: selected.id,
                    document_version_id: selected.document_id,
                    claim_id: selected.claim_id,
                    severity: selected.severity,
                    materiality: selected.materiality,
                    explanation: selected.reason,
                    suggested_fix: selected.suggested_fix,
                    impact_score: selected.impact_score,
                    location,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
            <div className="review-decision">
              <h3>Reviewer decision</h3>
              <p>
                Record your judgement with a note before resolving the finding.
              </p>
              <label htmlFor="review-note" className="sr-only">
                Reviewer note
              </label>
              <textarea
                id="review-note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="What did you check, and why is this the right decision?"
                rows={3}
                maxLength={4000}
                disabled={decision.isPending}
              />
              <div className="decision-actions">
                <LoadingButton
                  loading={decision.isPending}
                  disabled={!note.trim() || rescore.isPending}
                  onClick={() => decision.mutate("accept")}
                >
                  Accept finding
                </LoadingButton>
                <Button
                  variant="outline"
                  disabled={
                    !note.trim() || decision.isPending || rescore.isPending
                  }
                  onClick={() => decision.mutate("dismiss")}
                >
                  Dismiss
                </Button>
                <Button
                  variant="outline"
                  disabled={
                    !note.trim() || decision.isPending || rescore.isPending
                  }
                  onClick={() => decision.mutate("fix")}
                >
                  Mark fixed
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Accept keeps the finding’s score deduction. Dismiss or fixed
                removes it after recalculation.
              </p>
              {decision.error && (
                <p className="form-error" role="alert">
                  {decision.error.message}
                </p>
              )}
            </div>
          </section>
          <aside className="product-panel evidence-panel">
            <div className="panel-heading">
              <div>
                <h2>Document reference</h2>
                <p>Trace this finding to its source version.</p>
              </div>
            </div>
            <QueryState
              loading={documents.isPending}
              error={documents.error}
              retry={() => documents.refetch()}
            />
            {document && (
              <>
                <div className="evidence-document">
                  <FileText size={22} />
                  <strong>{document.filename}</strong>
                  <span>
                    Version {document.version_no} ·{" "}
                    {document.is_current ? "Current" : "Previous"}
                  </span>
                </div>
                <dl className="evidence-fields">
                  <dt>Document version ID</dt>
                  <dd>{document.id}</dd>
                  <dt>Text fingerprint</dt>
                  <dd>{document.text_hash}</dd>
                  <dt>Location</dt>
                  <dd>
                    {Object.keys(location).length
                      ? Object.entries(location)
                          .map(([key, value]) => `${key}: ${String(value)}`)
                          .join(" · ")
                      : "No location returned"}
                  </dd>
                </dl>
              </>
            )}
            <div className="evidence-unavailable">
              <span className="eyebrow">EVIDENCE QUOTE</span>
              <p>
                The audit service does not currently return source excerpts.
                Check the original document before making a decision.
              </p>
            </div>
            {selected.reviewer_note && (
              <div className="existing-note">
                <span className="field-label">Previous reviewer note</span>
                <p>{selected.reviewer_note}</p>
              </div>
            )}
          </aside>
        </div>
      )}
      {saved && (
        <p className="save-message" role="status">
          <Check size={16} />
          {saved}
        </p>
      )}
      {rescore.error && (
        <p className="form-error" role="alert">
          {rescore.error.message}
        </p>
      )}
    </div>
  )
}
