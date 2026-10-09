import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ArrowRight,
  FileText,
  Plus,
  Search,
  SlidersHorizontal,
  Beaker,
  Gavel,
  Shield,
  BarChart3,
} from "lucide-react"
import { useState } from "react"
import { auditApi, formatDate, isRunning } from "@/api/audits"
import { Input } from "@/components/ui/input"
import { QueryState, StatusPill } from "./shared"

export function AuditList({
  queue = false,
  archive = false,
}: {
  queue?: boolean
  archive?: boolean
}) {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState("all")
  const audits = useQuery({
    queryKey: ["audits"],
    queryFn: auditApi.list,
    refetchInterval: 15000,
  })
  const records = audits.data?.data ?? []
  const visible = records.filter(
    (audit) =>
      (filter === "all" ||
        (filter === "active"
          ? isRunning(audit.status)
          : audit.status === filter)) &&
      `${audit.title} ${audit.id}`.toLowerCase().includes(search.toLowerCase()),
  )
  const counts = [
    {
      label: "Document sets",
      value: records.length,
      detail: "In the latest 100 audits",
    },
    {
      label: "In progress",
      value: records.filter((audit) => isRunning(audit.status)).length,
      detail: "Queued or processing now",
    },
    {
      label: "Completed",
      value: records.filter((audit) => audit.status === "completed").length,
      detail: "Open a result for its findings",
    },
    {
      label: "Needs retry",
      value: records.filter((audit) => audit.status === "failed").length,
      detail: "Verification could not finish",
    },
  ]
  return (
    <div className="product-page">
      <div className="product-heading">
        <div>
          <span className="eyebrow">TATHYA CONTROL</span>
          <h1>
            {queue
              ? "Review queue"
              : archive
                ? "Audit archive"
                : "Control center"}
          </h1>
          <p>
            {queue
              ? "Find a document set, inspect its findings, and make a considered decision."
              : "Your document checks, with the context to act."}
          </p>
        </div>
        <Link to="/submit" className="primary-link">
          <Plus size={15} /> New audit
        </Link>
      </div>
      {!queue && !archive && (
        <>
          <section className="metric-strip">
            {counts.map((metric) => (
              <div key={metric.label}>
                <span>{metric.label}</span>
                <strong>{audits.data ? metric.value : "—"}</strong>
                <small>{metric.detail}</small>
              </div>
            ))}
          </section>
        </>
      )}
      <section className="product-panel audit-table-panel">
        <div className="panel-heading">
          <div>
            <h2>{queue ? "Document sets to investigate" : "Audit activity"}</h2>
            <p>
              {queue
                ? "Open an audit to see its outstanding findings."
                : "Latest checks across your accessible document sets."}
            </p>
          </div>
          <span className="quiet-label">{records.length} audits</span>
        </div>
        <div className="table-toolbar">
          <div className="search-field">
            <Search size={15} />
            <Input
              aria-label="Search audits"
              placeholder="Search by name or audit ID…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <label className="filter-control">
            <SlidersHorizontal size={14} />
            <span className="sr-only">Filter by status</span>
            <select
              aria-label="Filter by status"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="active">In progress</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </label>
        </div>
        <QueryState
          loading={audits.isPending}
          error={audits.error}
          retry={() => audits.refetch()}
        />
        {audits.data && (
          <>
            <div className="audit-table-scroll">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>Document set</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>
                      <span className="sr-only">Open audit</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((audit) => (
                    <tr key={audit.id}>
                      <td>
                        <div className="table-document">
                          <FileText size={16} />
                          <div>
                            <Link
                              to={
                                queue
                                  ? "/control/workspace/$auditId"
                                  : "/submit/$auditId"
                              }
                              params={{ auditId: audit.id }}
                            >
                              {audit.title}
                            </Link>
                            <small>{audit.id.slice(0, 8).toUpperCase()}</small>
                          </div>
                        </div>
                      </td>
                      <td>
                        <StatusPill status={audit.status} />
                      </td>
                      <td>{formatDate(audit.created_at)}</td>
                      <td>
                        <div className="audit-actions">
                          <Link
                            aria-label={`Open ${audit.title}`}
                            to={
                              queue
                                ? "/control/workspace/$auditId"
                                : "/submit/$auditId"
                            }
                            params={{ auditId: audit.id }}
                            className="action-btn"
                            title="Open"
                          >
                            <ArrowRight size={14} />
                          </Link>
                          {queue && audit.status === "completed" && (
                            <>
                              <Link
                                to="/control/injector/$auditId"
                                search={{ scenario: "" }}
                                params={{ auditId: audit.id }}
                                className="action-btn"
                                title="Jhooth Injector"
                              >
                                <Beaker size={14} />
                              </Link>
                              <Link
                                to="/control/judge/$auditId"
                                params={{ auditId: audit.id }}
                                className="action-btn"
                                title="Judge WOW"
                              >
                                <Gavel size={14} />
                              </Link>
                              <Link
                                to="/control/proof/$auditId"
                                params={{ auditId: audit.id }}
                                className="action-btn"
                                title="Proof Sandbox"
                              >
                                <Shield size={14} />
                              </Link>
                              <Link
                                to="/control/results/$auditId"
                                params={{ auditId: audit.id }}
                                className="action-btn"
                                title="Challenge Results"
                              >
                                <BarChart3 size={14} />
                              </Link>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!visible.length && (
              <div className="panel-state">
                <FileText size={24} />
                <h3>
                  {records.length
                    ? "No matching audits"
                    : "Your first audit starts here"}
                </h3>
                <p>
                  {records.length
                    ? "Try another search or clear the status filter."
                    : "Upload a document set to see results in this workspace."}
                </p>
                {!records.length && (
                  <Link to="/submit" className="primary-link">
                    Create an audit <Plus size={15} />
                  </Link>
                )}
              </div>
            )}
          </>
        )}
        <div className="table-footer">
          <span>
            Showing {visible.length} of {records.length} audits
          </span>
          <span>Updates every 15 seconds</span>
        </div>
      </section>
      {!queue && !archive && (
        <aside className="control-note">
          <ShieldNote />
        </aside>
      )}
    </div>
  )
}
function ShieldNote() {
  return (
    <>
      <span className="eyebrow">CONTEXT BEFORE CONCLUSIONS</span>
      <p>
        Completed means the check has finished. Open the result to understand
        its score, evidence and outstanding findings.
      </p>
    </>
  )
}
