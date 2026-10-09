import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { Link } from "@tanstack/react-router"
import {
  Search,
  Info,
  Swords,
  ArrowUpRight,
  Play,
} from "lucide-react"
import { challengeApi } from "@/api/phase6"
import { auditApi } from "@/api/audits"
import { QueryState } from "@/components/Audits/shared"
import { Input } from "@/components/ui/input"

const SEVERITY_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: "bg-red-500/10 dark:bg-red-500/20", text: "text-red-600 dark:text-red-400", border: "border-red-500/30" },
  HIGH: { bg: "bg-orange-500/10 dark:bg-orange-500/20", text: "text-orange-600 dark:text-orange-400", border: "border-orange-500/30" },
  MEDIUM: { bg: "bg-amber-500/10 dark:bg-amber-500/20", text: "text-amber-600 dark:text-amber-400", border: "border-amber-500/30" },
  LOW: { bg: "bg-emerald-500/10 dark:bg-emerald-500/20", text: "text-emerald-600 dark:text-emerald-400", border: "border-emerald-500/30" },
  NEGLIGIBLE: { bg: "bg-muted", text: "text-muted-foreground", border: "border-border" },
}

const PATTERN_LABELS: Record<string, string> = {
  claim_negation: "Claim Negation",
  numeric_manipulation: "Numeric Manipulation",
  date_manipulation: "Date Manipulation",
  entity_swap: "Entity Swap",
  logic_inversion: "Logic Inversion",
  omission_induction: "Omission Induction",
  evidence_tampering: "Evidence Tampering",
  policy_violation: "Policy Violation",
  materiality_masking: "Materiality Masking",
}

export function ChallengeLibrary() {
  const [search, setSearch] = useState("")
  const [patternFilter, setPatternFilter] = useState("all")
  const [severityFilter, setSeverityFilter] = useState("all")
  const [selectedAuditId, setSelectedAuditId] = useState<string>("")

  const scenarios = useQuery({
    queryKey: ["challenge-scenarios"],
    queryFn: challengeApi.listScenarios,
  })

  const audits = useQuery({
    queryKey: ["audits"],
    queryFn: auditApi.list,
  })

  const allAudits = audits.data?.data ?? []
  const currentAuditId = selectedAuditId || allAudits[0]?.id || ""

  const allPatterns = ["all", ...new Set(scenarios.data?.data.map(s => s.pattern_type) ?? [])]
  const allSeverities = ["all", "CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"]

  const filtered = scenarios.data?.data.filter(s => {
    const matchesSearch =
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase()) ||
      s.pattern_type.toLowerCase().includes(search.toLowerCase())
    const matchesPattern = patternFilter === "all" || s.pattern_type === patternFilter
    const matchesSeverity = severityFilter === "all" || s.severity === severityFilter
    return matchesSearch && matchesPattern && matchesSeverity
  }) ?? []

  return (
    <div className="product-page phase6-page">
      <div className="product-heading">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="eyebrow">PHASE 6 ADVERSARIAL VERIFICATION</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold">
              JHOOTH CHHUPAO
            </span>
          </div>
          <h1>Adversarial Challenge Library</h1>
          <p>
            Curated, versioned adversarial scenarios for attacking and stress-testing document trust.
            Select a scenario to inject into an active audit document.
          </p>
        </div>

        {/* Global Quick Action Strip */}
        <div className="flex flex-wrap items-center gap-2">
          {currentAuditId && (
            <Link
              to="/control/results/$auditId"
              params={{ auditId: currentAuditId }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-background hover:bg-accent transition-colors"
            >
              <span>Evaluation Dashboard</span>
              <ArrowUpRight size={13} />
            </Link>
          )}
        </div>
      </div>

      {/* Target Audit Selection Bar */}
      <section className="product-panel mb-6 p-4 rounded-xl border border-primary/20 bg-primary/5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="size-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
              <Swords size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">Target Audit for Adversarial Injection</h2>
              <p className="text-xs text-muted-foreground">Choose which document set to attack with selected scenarios</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              aria-label="Select target audit"
              value={currentAuditId}
              onChange={e => setSelectedAuditId(e.target.value)}
              className="px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-background text-foreground shadow-sm focus:ring-1 focus:ring-primary"
            >
              {allAudits.map(a => (
                <option key={a.id} value={a.id}>
                  {a.title.length > 40 ? `${a.title.slice(0, 40)}…` : a.title} ({a.status})
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <section className="product-panel">
        <div className="panel-heading">
          <div>
            <h2>Scenario Catalogue</h2>
            <p>{scenarios.data?.count ?? 0} deterministic templates available for testing</p>
          </div>
          <span className="text-xs font-mono text-muted-foreground bg-muted px-2.5 py-1 rounded-md">
            v6.0 Adversarial Mesh
          </span>
        </div>

        {/* Filter & Search Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 mb-6">
          <div className="sm:col-span-6 relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9 text-xs"
              placeholder="Search by name, pattern, or keyword…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="sm:col-span-3">
            <select
              aria-label="Filter by pattern"
              value={patternFilter}
              onChange={e => setPatternFilter(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-md border border-border bg-background text-foreground shadow-sm focus:ring-1 focus:ring-primary"
            >
              <option value="all">All patterns</option>
              {allPatterns.filter(p => p !== "all").map(p => (
                <option key={p} value={p}>{PATTERN_LABELS[p] || p}</option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-3">
            <select
              aria-label="Filter by severity"
              value={severityFilter}
              onChange={e => setSeverityFilter(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-md border border-border bg-background text-foreground shadow-sm focus:ring-1 focus:ring-primary"
            >
              <option value="all">All severities</option>
              {allSeverities.filter(s => s !== "all").map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>

        <QueryState
          loading={scenarios.isPending}
          error={scenarios.error}
          retry={() => scenarios.refetch()}
        />

        {scenarios.data?.data.length === 0 && <p role="status">No scenarios are available yet.</p>}
        {scenarios.data && filtered.length === 0 && scenarios.data.data.length > 0 && (
          <div className="p-8 text-center border border-dashed rounded-lg">
            <Info size={24} className="mx-auto text-muted-foreground mb-2" />
            <h3 className="text-sm font-semibold">No matching scenarios</h3>
            <p className="text-xs text-muted-foreground mt-1">Try another search keyword or clear your filters.</p>
          </div>
        )}

        {/* Scenario Grid */}
        {scenarios.data && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map(scenario => {
              const sev = SEVERITY_BADGES[scenario.severity] || SEVERITY_BADGES.MEDIUM
              return (
                <article
                  key={scenario.version}
                  className="flex flex-col justify-between p-4 rounded-xl border border-border bg-card hover:border-primary/50 transition-all hover:shadow-md"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${sev.bg} ${sev.text} ${sev.border}`}>
                        {scenario.severity}
                      </span>
                      <span className="text-[11px] font-mono text-muted-foreground">
                        {scenario.version}
                      </span>
                    </div>

                    <h3 className="text-sm font-semibold text-foreground leading-snug mb-1">
                      {scenario.name}
                    </h3>
                    <p className="text-xs text-muted-foreground line-clamp-2 mb-4">
                      {scenario.description}
                    </p>

                    <div className="space-y-1.5 pt-3 border-t border-border/60 text-xs">
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Pattern Type:</span>
                        <span className="font-medium text-foreground font-mono text-[11px]">
                          {PATTERN_LABELS[scenario.pattern_type] || scenario.pattern_type}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Claim Mod:</span>
                        <span className="font-mono text-[11px] text-foreground">{scenario.claim_modification}</span>
                      </div>
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Injection Method:</span>
                        <span className="font-mono text-[11px] text-foreground">{scenario.injection_method}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-border/60 flex items-center justify-between gap-2">
                    {currentAuditId ? <Link
                      to="/control/injector/$auditId"
                      params={{ auditId: currentAuditId }}
                      search={{ scenario: scenario.version }}
                      className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
                    >
                      <Play size={12} className="fill-current" />
                      <span>Test this scenario</span>
                    </Link> : <Link to="/submit" className="primary-link">Create an audit first</Link>}
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>

      <aside className="control-note mt-6 p-4 rounded-xl border border-border bg-muted/40 text-xs leading-relaxed">
        <span className="eyebrow block font-semibold text-primary mb-1">DETERMINISTIC ADVERSARIAL ASSURANCE</span>
        <p className="text-muted-foreground">
          Each scenario in Jhooth Chhupao represents an immutable formal test vector. When executed through the Injector workspace,
          a candidate document is produced in memory without altering base document records in PostgreSQL, so you can inspect the changes before review.
        </p>
      </aside>
    </div>
  )
}