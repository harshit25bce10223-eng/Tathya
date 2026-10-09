import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ArrowLeft,
} from "lucide-react"
import { challengeApi } from "@/api/phase6"
import { QueryState } from "@/components/Audits/shared"

const CATEGORY_LABELS: Record<string, string> = {
  claim_injection: "Claim Injection",
  evidence_tampering: "Evidence Tampering",
  document_replacement: "Document Replacement",
  numeric_manipulation: "Numeric Manipulation",
  date_manipulation: "Date Manipulation",
  entity_swap: "Entity Swap",
  logic_inversion: "Logic Inversion",
  omission_induction: "Omission Induction",
  policy_violation_injection: "Policy Violation Injection",
  materiality_masking: "Materiality Masking",
}

export function ChallengeResultsDashboard({ auditId: _auditId }: { auditId?: string }) {
  const { data: resultsData, isPending, error, refetch } = useQuery({
    queryKey: ["challenge-results"],
    queryFn: challengeApi.getResults,
  })

  const metrics = resultsData?.metrics
  const trials = resultsData?.results ?? []

  return (
    <div className="product-page phase6-page">
      <div className="flex items-center gap-2 mb-4">
        <Link to="/control/challenges" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft size={14} /> Back to Jhooth Chhupao
        </Link>
      </div>

      <div className="product-heading">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="eyebrow">PHASE 6 ADVERSARIAL TELEMETRY</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 font-semibold">
              EVALUATION HISTORY
            </span>
          </div>
          <h1>Adversarial Evaluation Dashboard</h1>
          <p>
            Measured detection accuracy against hidden ground truth vectors. Zero synthetic bias — all rates include explicit denominators.
          </p>
        </div>
      </div>

      <QueryState loading={isPending} error={error} retry={refetch} />

      {!isPending && !error && trials.length === 0 && <div className="panel-state" role="status"><h2>No recorded evaluations yet</h2><p>Accuracy is not available until actual trials have been recorded.</p></div>}
      {metrics && trials.length > 0 && (
        <div className="space-y-6">
          {/* Top KPI Metrics Strip */}
          <section className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
              <span className="text-xs text-muted-foreground font-medium block mb-1">Precision (TP / TP+FP)</span>
              <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                {(metrics.precision * 100).toFixed(1)}%
              </div>
              <div className="mt-2 w-full bg-muted rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${metrics.precision * 100}%` }} />
              </div>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
              <span className="text-xs text-muted-foreground font-medium block mb-1">Recall (True Positive Rate)</span>
              <div className="text-2xl font-bold font-mono text-primary">
                {(metrics.true_positive_rate * 100).toFixed(1)}%
              </div>
              <div className="mt-2 w-full bg-muted rounded-full h-1.5 overflow-hidden">
                <div className="bg-primary h-full rounded-full" style={{ width: `${metrics.true_positive_rate * 100}%` }} />
              </div>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
              <span className="text-xs text-muted-foreground font-medium block mb-1">F1 Score</span>
              <div className="text-2xl font-bold font-mono text-foreground">
                {(metrics.f1_score * 100).toFixed(1)}%
              </div>
              <div className="mt-2 w-full bg-muted rounded-full h-1.5 overflow-hidden">
                <div className="bg-foreground h-full rounded-full" style={{ width: `${metrics.f1_score * 100}%` }} />
              </div>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
              <span className="text-xs text-muted-foreground font-medium block mb-1">Total Evaluated Trials</span>
              <div className="text-2xl font-bold font-mono text-foreground">
                {metrics.total_trials}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">Across 6 attack categories</p>
            </div>
          </section>

          {/* Breakdown by Category Table */}
          <section className="product-panel p-5 rounded-xl border border-border bg-card">
            <div className="panel-heading mb-4">
              <div>
                <h2>Adversarial Category Breakdown</h2>
                <p>Detection performance per specific attack vector</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="pb-2 font-medium">Attack Category</th>
                    <th className="pb-2 font-medium text-center">Total Trials</th>
                    <th className="pb-2 font-medium text-center">True Positives</th>
                    <th className="pb-2 font-medium text-center">False Negatives</th>
                    <th className="pb-2 font-medium text-right">Detection Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {Object.entries(metrics.by_category).map(([cat, c]) => {
                    const rate = c.total > 0 ? ((c.true_positives / c.total) * 100).toFixed(1) : "0.0"
                    return (
                      <tr key={cat} className="hover:bg-muted/40">
                        <td className="py-2.5 font-semibold text-foreground">
                          {CATEGORY_LABELS[cat] || cat}
                        </td>
                        <td className="py-2.5 text-center font-mono">{c.total}</td>
                        <td className="py-2.5 text-center font-mono text-emerald-600 font-bold">{c.true_positives}</td>
                        <td className="py-2.5 text-center font-mono text-red-600">{c.false_negatives}</td>
                        <td className="py-2.5 text-right font-mono font-bold text-foreground">{rate}%</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {/* Individual Trials Log */}
          <section className="product-panel p-5 rounded-xl border border-border bg-card">
            <div className="panel-heading mb-4">
              <div>
                <h2>Evaluation Trial Log</h2>
                <p>Verified outcomes against isolated ground truth</p>
              </div>
              <span className="text-xs font-mono text-muted-foreground">{trials.length} trials logged</span>
            </div>

            <div className="space-y-2">
              {trials.map((t, idx) => (
                <div key={t.trial_id || idx} className="p-3 rounded-lg bg-muted/40 border border-border flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-3">
                    <div className="size-6 rounded-full bg-emerald-500/10 text-emerald-600 flex items-center justify-center font-mono font-bold text-[10px]">
                      ✓
                    </div>
                    <div>
                      <span className="font-semibold text-foreground">{CATEGORY_LABELS[t.category] || t.category}</span>
                      <p className="text-[11px] text-muted-foreground">{t.notes}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-right">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 font-bold uppercase">
                      {t.actual_outcome}
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground">{t.detection_latency_ms}ms</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}