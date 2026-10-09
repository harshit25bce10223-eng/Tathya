import { apiFetch } from "@/api/transport"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { auditApi, formatDate } from "@/api/audits"
import { QueryState, StatusPill } from "./shared"

function Heading({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="product-heading">
      <div>
        <span className="eyebrow">TATHYA CONTROL</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </div>
  )
}
export function SourcesPage() {
  const audits = useQuery({ queryKey: ["audits"], queryFn: auditApi.list })
  const [selected, setSelected] = useState("")
  const [search, setSearch] = useState("")
  const [openDocument, setOpenDocument] = useState("")
  const preview = useQuery({ queryKey: ["document-text", selected, openDocument], queryFn: () => auditApi.documentText(selected || audits.data?.data[0]?.id || "", openDocument), enabled: !!openDocument })
  const id = selected || audits.data?.data[0]?.id || ""
  const documents = useQuery({
    queryKey: ["audit-documents", id],
    queryFn: () => auditApi.documents(id),
    enabled: !!id,
  })
  const visible =
    documents.data?.data.filter((d) =>
      d.filename.toLowerCase().includes(search.toLowerCase()),
    ) ?? []
  return (
    <div className="product-page">
      <Heading
        title="Sources & truth"
        description="Trace each check to the exact document version supplied."
      />
      <section className="product-panel">
        <div className="panel-heading">
          <div>
            <h2>Document library</h2>
            <p>Choose a document set to inspect its source records.</p>
          </div>
        </div>
        <div className="table-toolbar">
          <label className="filter-control">
            Document set
            <select
              aria-label="Document set"
              value={id}
              onChange={(e) => { setSelected(e.target.value); setOpenDocument("") }}
            >
              <option disabled value="">
                Select an audit
              </option>
              {audits.data?.data.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title}
                </option>
              ))}
            </select>
          </label>
          <input
            className="library-search"
            aria-label="Search documents"
            placeholder="Search documents…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <QueryState
          loading={audits.isPending || (!!id && documents.isPending)}
          error={audits.error || documents.error}
          retry={() => {
            audits.refetch()
            if (id) documents.refetch()
          }}
        />
        {documents.data &&
          visible.map((d) => (
            <article className="source-record" key={d.id}>
              <div>
                <h3><button type="button" aria-expanded={openDocument === d.id} onClick={() => setOpenDocument(openDocument === d.id ? "" : d.id)}>{d.filename}</button></h3>
                <p>
                  Version {d.version_no} · {d.kind}
                </p>
              </div>
              <StatusPill
                status={d.is_current ? "current" : "previous version"}
              />
              <dl>
                <dt>Document ID</dt>
                <dd>{d.id}</dd>
                <dt>Canonical text hash</dt>
                <dd>{d.text_hash || "Not available"}</dd>
              </dl>
              {openDocument === d.id && <div><QueryState loading={preview.isPending} error={preview.error} retry={() => preview.refetch()} />{preview.data && <pre className="document-preview">{preview.data.raw_text}</pre>}</div>}
            </article>
          ))}
        {audits.data && !audits.data.data.length && (
          <div className="panel-state">
            <h3>No source documents yet</h3>
            <p>Create your first audit to build this library.</p>
          </div>
        )}
        {documents.data && !visible.length && (
          <div className="panel-state">
            <h3>No matching documents</h3>
            <p>Try another search or document set.</p>
          </div>
        )}
      </section>
      <aside className="control-note">
        <span className="eyebrow">SOURCE CONTEXT</span>
        <p>
          Select a filename to read the extracted source text. Uploaded documents
          do not automatically establish independent source authority.
        </p>
      </aside>
    </div>
  )
}
export function PoliciesPage() {
  return (
    <div className="product-page">
      <Heading
        title="Trust policies"
        description="Understand how findings and reviewer decisions affect a published score."
      />
      <section className="product-panel">
        <div className="panel-heading">
          <div>
            <h2>Score calculation</h2>
            <p>
              The current service starts at 100 and deducts active finding
              impacts.
            </p>
          </div>
          <StatusPill status="read only" />
        </div>
        <div className="policy-formula">
          max(0, 100 − active finding impacts)
        </div>
        <div className="policy-grid">
          {[
            ["Pending", "Impact counts until a reviewer resolves the finding."],
            ["Accepted", "Confirmed findings continue to reduce the score."],
            ["Dismissed", "Impact is excluded when the score is recalculated."],
            [
              "Fixed",
              "Resolved findings are excluded when the score is recalculated.",
            ],
          ].map(([title, detail]) => (
            <article key={title}>
              <StatusPill status={title} />
              <p>{detail}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="product-panel">
        <div className="panel-heading">
          <div>
            <h2>Review safeguards</h2>
            <p>Every decision needs context.</p>
          </div>
        </div>
        <div className="policy-grid">
          <article>
            <h3>Reviewer access</h3>
            <p>
              Only authorised reviewers and administrators can save decisions
              and recalculate scores.
            </p>
          </article>
          <article>
            <h3>Required notes</h3>
            <p>Explain each decision. Recalculate explicitly after review.</p>
          </article>
        </div>
      </section>
      <aside className="control-note">
        <span className="eyebrow">POLICY CONFIGURATION</span>
        <p>
          Custom policy editing is not connected in this service. This page
          describes current scoring behaviour; it does not publish new rules.
        </p>
      </aside>
    </div>
  )
}
export function MetricsPage() {
  const audits = useQuery({ queryKey: ["audits"], queryFn: auditApi.list })
  const ropeMetrics = useQuery({
    queryKey: ["ropeMetrics"],
    queryFn: async () => {
      const res = await apiFetch("/rope/metrics")
      return res.json()
    },
  })

  const records = audits.data?.data ?? []
  const gating = ropeMetrics.data?.gating_results

  const dayKey = (date: string | null) =>
    date
      ? new Intl.DateTimeFormat("en-CA", {
          timeZone: "Asia/Kolkata",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        }).format(new Date(date))
      : ""
  const days = Array.from(
    new Set(records.map((a) => dayKey(a.created_at)).filter(Boolean)),
  )
    .sort()
    .reverse()
    .slice(0, 7)

  return (
    <div className="product-page">
      <QueryState loading={ropeMetrics.isPending} error={ropeMetrics.error} retry={() => ropeMetrics.refetch()} />
      <Heading
        title="Metrics & RoPE Verification Engine"
        description="Real-time neural verifier metrics, confusion matrix, and audit volumes."
      />
      <QueryState
        loading={audits.isPending}
        error={audits.error}
        retry={() => audits.refetch()}
      />

      {/* 1. Live RoPE Neural Verifier Gating Dashboard */}
      {gating && (
        <section className="product-panel mb-6 border-emerald-500/30">
          <div className="panel-heading">
            <div>
              <div className="flex items-center gap-3">
                <h2>RoPE Cross-Encoder Fact Verifier</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  STATUS: {gating.gate_decision || "Not evaluated"}
                </span>
              </div>
              <p>Calibrated temperature probability scaling & gating benchmark</p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-4">
            <div className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
              <span className="text-xs text-neutral-400">Macro-F1 Score</span>
              <div className="text-2xl font-bold text-emerald-400">{gating.model_summary_f1}%</div>
              <small className="text-neutral-500">Baseline: {gating.baseline_summary_f1}%</small>
            </div>
            <div className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
              <span className="text-xs text-neutral-400">Contradiction Recall</span>
              <div className="text-2xl font-bold text-sky-400">{gating.overall_test_metrics?.contradiction_recall ?? "—"}%</div>
              <small className="text-neutral-500">Measured on the recorded test set</small>
            </div>
            <div className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
              <span className="text-xs text-neutral-400">False-Alarm Rate</span>
              <div className="text-2xl font-bold text-amber-400">{gating.model_false_alarm_rate}%</div>
              <small className="text-neutral-500">Baseline: {gating.baseline_false_alarm_rate}%</small>
            </div>
            <div className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
              <span className="text-xs text-neutral-400">CPU Latency</span>
              <div className="text-2xl font-bold text-purple-400">{gating.latency_cpu_single_ms} ms</div>
              <small className="text-neutral-500">Batch 20: {gating.latency_cpu_batch20_ms} ms</small>
            </div>
          </div>

          {/* Confusion Matrix Breakdown */}
          {gating.overall_test_metrics?.confusion_matrix && (
            <div className="mt-4 pt-4 border-t border-neutral-800">
              <h3 className="text-sm font-semibold text-neutral-300 mb-2">Test Confusion Matrix (Predicted vs Actual)</h3>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2 bg-neutral-800/40 rounded">
                  <span className="text-neutral-400 block">Entailment</span>
                  <strong className="text-emerald-400 font-mono text-sm">{gating.overall_test_metrics.confusion_matrix[0][0]} Correct</strong>
                </div>
                <div className="p-2 bg-neutral-800/40 rounded">
                  <span className="text-neutral-400 block">Contradiction</span>
                  <strong className="text-red-400 font-mono text-sm">{gating.overall_test_metrics.confusion_matrix[1][1]} Correct</strong>
                </div>
                <div className="p-2 bg-neutral-800/40 rounded">
                  <span className="text-neutral-400 block">Neutral/Unsupported</span>
                  <strong className="text-yellow-400 font-mono text-sm">{gating.overall_test_metrics.confusion_matrix[2][2]} Correct</strong>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* 2. Audit Volume & Standard Metrics */}
      {audits.data && (
        <>
          <section className="metric-strip">
            {["completed", "processing", "queued", "failed"].map((status) => (
              <div key={status}>
                <span>{status}</span>
                <strong>
                  {records.filter((a) => a.status === status).length}
                </strong>
                <small>Of {records.length} loaded audits</small>
              </div>
            ))}
          </section>
          <section className="product-panel">
            <div className="panel-heading">
              <div>
                <h2>Audit volume by day</h2>
                <p>Most recent seven active days · India time</p>
              </div>
            </div>
            <div className="volume-chart">
              {days.map((day) => {
                const count = records.filter(
                  (a) => dayKey(a.created_at) === day,
                ).length
                return (
                  <div className="volume-row" key={day}>
                    <span>{formatDate(`${day}T00:00:00+05:30`)}</span>
                    <div>
                      <span
                        style={{
                          width: `${(count / Math.max(1, records.length)) * 100}%`,
                        }}
                      />
                    </div>
                    <strong>{count}</strong>
                  </div>
                )
              })}
              {!days.length && <p>No audit activity yet.</p>}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
