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
              onChange={(e) => setSelected(e.target.value)}
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
                <h3>{d.filename}</h3>
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
          These are uploaded document records. Source authority and original
          text previews are not supplied by the current service; consult the
          original files when reviewing a claim.
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
  const records = audits.data?.data ?? []
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
      <Heading
        title="Metrics & drift"
        description="Operational context across the latest 100 accessible audits."
      />
      <QueryState
        loading={audits.isPending}
        error={audits.error}
        retry={() => audits.refetch()}
      />
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
      <aside className="control-note">
        <span className="eyebrow">DRIFT MONITORING</span>
        <p>
          Historical score snapshots and drift measurements are not available
          from the current API. Audit volume is shown here; score trends need a
          history source.
        </p>
      </aside>
    </div>
  )
}
