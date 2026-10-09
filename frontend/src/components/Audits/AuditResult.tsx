import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ArrowLeft, ArrowRight, FileText, ShieldCheck } from "lucide-react"
import { useState } from "react"
import { auditApi, type AuditDocument, isRunning } from "@/api/audits"
import { QueryState, StatusPill, useAudit } from "./shared"

export function AuditResult({ auditId }: { auditId: string }) {
  const { summary, flags, documents } = useAudit(auditId)
  const [selectedDoc, setSelectedDoc] = useState<AuditDocument | null>(null)
  const docViewer = useQuery({
    queryKey: ["document-text", auditId, selectedDoc?.id],
    queryFn: () => auditApi.documentText(auditId, selectedDoc!.id),
    enabled: !!selectedDoc?.id,
  })
  const data = summary.data
  if (!data)
    return (
      <QueryState
        loading={summary.isPending}
        error={summary.error}
        retry={() => summary.refetch()}
      />
    )
  const score = data.passport?.trust_score
  const active =
    flags.data?.data.filter((flag) =>
      ["pending", "accepted", "open"].includes(flag.status),
    ) ?? []
  return (
    <div className="product-page">
      <Link to="/control" className="back-link">
        <ArrowLeft size={14} /> All audits
      </Link>
      <div className="product-heading">
        <div>
          <span className="eyebrow">YOUR AUDIT RESULT</span>
          <h1>{data.audit.title}</h1>
          <p>One view of the findings, their impact and what comes next.</p>
        </div>
        <StatusPill status={data.audit.status} />
      </div>
      {data.passport?.verify_token && (
        <Link
          className="back-link"
          to="/verify/$token"
          params={{ token: data.passport.verify_token }}
        >
          Verify public passport <ArrowRight size={14} />
        </Link>
      )}
      {isRunning(data.audit.status) && (
        <div className="processing-banner" role="status">
          <span className="processing-dot" /> Verification is{" "}
          {data.audit.status}. This page updates automatically.
        </div>
      )}
      {data.audit.status === "failed" && (
        <div className="form-error" role="alert">
          Verification could not finish.{" "}
          {data.audit.error_message ||
            "Please try a new audit with readable documents."}
        </div>
      )}
      <section className="result-summary product-panel">
        <div className="score-area">
          <span className="quiet-label">
            <ShieldCheck size={15} /> TRUST SCORE
          </span>
          <div className="score-number">
            {score === undefined
              ? "—"
              : new Intl.NumberFormat("en-IN", {
                  maximumFractionDigits: 1,
                }).format(score)}
            <span>/ 100</span>
          </div>
          <p>
            {score === undefined
              ? "Score available when a passport is issued."
              : data.open_flag_count
                ? "Review the flagged findings before relying on this document."
                : "Read the evidence and findings alongside this score."}
          </p>
        </div>
        <div className="score-context">
          <div>
            <span>Claims extracted</span>
            <strong>{data.claim_count}</strong>
            <small>Extracted for this audit</small>
          </div>
          <div>
            <span>Open findings</span>
            <strong>{data.open_flag_count}</strong>
            <small>Awaiting a reviewer decision</small>
          </div>
          <div>
            <span>Documents</span>
            <strong>{data.document_count}</strong>
            <small>Included in this document set</small>
          </div>
        </div>
      </section>
      <div className="result-grid">
        <section className="product-panel">
          <div className="panel-heading">
            <div>
              <h2>Understand the score</h2>
              <p>Point deductions from unresolved or accepted findings.</p>
            </div>
          </div>
          <QueryState
            loading={flags.isPending}
            error={flags.error}
            retry={() => flags.refetch()}
          />
          {flags.data && (
            <>
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((severity) => {
                const matches = active.filter(
                  (flag) => flag.severity.toUpperCase() === severity,
                )
                const penalty = matches.reduce(
                  (sum, flag) => sum + Math.max(0, flag.impact_score),
                  0,
                )
                return (
                  <div className="breakdown-row" key={severity}>
                    <div>
                      <span
                        className={`severity-dot ${severity.toLowerCase()}`}
                      />
                      <strong>
                        {severity.charAt(0) + severity.slice(1).toLowerCase()}
                      </strong>
                      <small>
                        {matches.length} finding
                        {matches.length === 1 ? "" : "s"}
                      </small>
                    </div>
                    <span>{penalty > 0 ? `−${penalty}` : "0"} pts</span>
                    <div className="breakdown-track">
                      <span style={{ width: `${Math.min(100, penalty)}%` }} />
                    </div>
                  </div>
                )
              })}
              <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-emerald-500" />
                  Verified via <strong>Gemini 3.5 Flash</strong> & <strong>BGE-M3</strong>
                </span>
                <span className="font-mono text-[11px] bg-muted px-2 py-0.5 rounded">v4.0 Deterministic</span>
              </div>
              <p className="panel-footnote">
                Deductions provide context for the overall score. Independent
                accuracy and coverage sub-scores are not yet available.
              </p>
            </>
          )}
        </section>
        <section className="product-panel">
          <div className="panel-heading">
            <div>
              <h2>Document set</h2>
              <p>The exact versions checked in this audit.</p>
            </div>
          </div>
          <QueryState
            loading={documents.isPending}
            error={documents.error}
            retry={() => documents.refetch()}
          />
          {documents.data?.data.map((doc) => (
            <div
              className="document-row cursor-pointer hover:bg-accent/40 rounded-md p-2 transition-colors"
              key={doc.id}
              onClick={() => setSelectedDoc(selectedDoc?.id === doc.id ? null : doc)}
              title="Click to view full document text"
            >
              <FileText size={17} className="text-primary mt-1 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm font-medium hover:underline truncate">{doc.filename}</strong>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                    {selectedDoc?.id === doc.id ? "Close file" : "Open file"}
                  </span>
                </div>
                <small className="text-xs text-muted-foreground">
                  Version {doc.version_no} · {doc.is_current ? "Current" : "Previous"} · SHA256: {doc.text_hash.slice(0, 16)}…
                </small>
                {selectedDoc?.id === doc.id && (
                  <div className="mt-3 p-3 bg-muted/60 border border-border rounded text-xs font-mono whitespace-pre-wrap max-h-72 overflow-y-auto select-text">
                    <div className="text-[10px] text-muted-foreground pb-2 mb-2 border-b border-border/50 uppercase tracking-wider flex justify-between">
                      <span>Full Document Source Text</span>
                      <span>Hash: {doc.text_hash}</span>
                    </div>
                    {docViewer.data?.raw_text || (docViewer.isPending ? "Loading file content…" : "Unable to load document content.")}
                  </div>
                )}
              </div>
            </div>
          ))}
          {documents.data?.data.length === 0 && (
            <p className="panel-footnote">
              No documents were returned for this audit.
            </p>
          )}
        </section>
      </div>
      <section className="product-panel">
        <div className="panel-heading">
          <div>
            <h2>What needs attention</h2>
            <p>Clear findings, with a practical next step.</p>
          </div>
          <span className="quiet-label">{data.flag_count} findings</span>
        </div>
        {flags.data?.data.length === 0 && (
          <div className="panel-state">
            <ShieldCheck size={24} />
            <h3>
              {isRunning(data.audit.status)
                ? "Findings will appear as the audit runs."
                : "No findings returned"}
            </h3>
            <p>
              {isRunning(data.audit.status)
                ? "You can leave this page open."
                : "A clean result should still be considered alongside your source material."}
            </p>
          </div>
        )}
        {flags.data?.data.map((flag) => (
          <article className="finding-row" key={flag.id}>
            <StatusPill status={flag.severity} />
            <div>
              <h3>{flag.type.replace(/_/g, " ") || "Finding"}</h3>
              <p>{flag.reason}</p>
              {flag.suggested_fix && (
                <div className="suggested-action">
                  <strong>Next step</strong> {flag.suggested_fix}
                </div>
              )}
            </div>
            <StatusPill status={flag.status} />
          </article>
        ))}
      </section>
      <div className="result-bottom">
        <p>
          <ShieldCheck size={15} /> A trust score supports a decision; it
          doesn’t replace your judgement.
        </p>
        <Link
          to="/submit"
          className="inline-flex gap-2 items-center text-sm text-primary font-medium"
        >
          Start another audit <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  )
}
