import { useUnsavedChanges } from "@/hooks/useUnsavedChanges"
import { useState, useEffect, useRef } from "react"
import { useMutation } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  Check,
  Calculator,
  Terminal,
  Play,
  Plus,
  Trash2,
  Cpu,
  Layers,
} from "lucide-react"
import { challengeApi, type ProofSolveResult } from "@/api/phase6"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"

export function ProofSandbox({ auditId: _auditId }: { auditId: string }) {
  const [goals, setGoals] = useState<string[]>([])
  const [assumptions, setAssumptions] = useState<string[]>([])
  const [numericConstraints, setNumericConstraints] = useState<Array<{
    variable: string
    operator: "eq" | "neq" | "lt" | "le" | "gt" | "ge"
    value: string
    reason: string
  }>>([
    { variable: "contract_value", operator: "eq", value: "4160000", reason: "Official Finance Approval" },
    { variable: "contract_value", operator: "eq", value: "5000000", reason: "Claimed contract value" },
    { variable: "contract_value", operator: "neq", value: "5000000", reason: "Deterministic Conflict Assertion" },
  ])
  const [timeout] = useState<number>(10)
  const [result, setResult] = useState<ProofSolveResult | null>(null)

  const solveMutation = useMutation({
    mutationFn: () => challengeApi.solveProof({
      goals: goals.filter(g => g.trim()),
      assumptions: assumptions.filter(a => a.trim()),
      numeric_constraints: numericConstraints.filter(c => c.variable.trim()),
      max_timeout_seconds: timeout,
    }),
    onSuccess: (res) => {
      setResult(res)
    },
  })

  const loadPreset = (type: "unsat_contract" | "sat_gdp" | "unsat_percentage") => {
    if (type === "unsat_contract") {
      setGoals(["contract_approved == true"])
      setAssumptions([])
      setNumericConstraints([
        { variable: "budget_approved", operator: "eq", value: "4160000", reason: "Demand No. 94" },
        { variable: "claim_amount", operator: "eq", value: "5000000", reason: "Contract Claim" },
        { variable: "budget_approved", operator: "eq", value: "5000000", reason: "Enforced Equality Target" },
      ])
    } else if (type === "sat_gdp") {
      setGoals(["target_achieved == true"])
      setAssumptions([])
      setNumericConstraints([
        { variable: "nominal_gdp_fy27", operator: "ge", value: "4270000", reason: "IMF April 2024" },
        { variable: "growth_rate", operator: "gt", value: "6.5", reason: "RBI Projection" },
      ])
    } else if (type === "unsat_percentage") {
      setGoals(["share_infra + share_health + share_defense == 100"])
      setAssumptions([])
      setNumericConstraints([
        { variable: "share_infra", operator: "eq", value: "40", reason: "Infrastructure" },
        { variable: "share_health", operator: "eq", value: "40", reason: "Healthcare" },
        { variable: "share_defense", operator: "eq", value: "30", reason: "Defense (40+40+30=110 != 100)" },
      ])
    }
    setResult(null)
  }

  const addConstraint = () => {
    setNumericConstraints([...numericConstraints, { variable: "", operator: "eq", value: "", reason: "" }])
  }

  const removeConstraint = (idx: number) => {
    setNumericConstraints(numericConstraints.filter((_, i) => i !== idx))
  }

  const solveInputSignature = JSON.stringify([goals, assumptions, numericConstraints])
  const previousSolveInputSignature = useRef(solveInputSignature)
  useEffect(() => {
    if (previousSolveInputSignature.current !== solveInputSignature) {
      setResult(null)
      solveMutation.reset()
    }
    previousSolveInputSignature.current = solveInputSignature
  }, [solveInputSignature, solveMutation.reset])

  useUnsavedChanges(solveMutation.isPending || ((goals.length > 0 || assumptions.length > 0 || numericConstraints.length > 0) && !result))

  return (
    <fieldset disabled={solveMutation.isPending} className="product-page phase6-page workspace-fields">
      <div className="flex items-center gap-2 mb-4">
        <Link to="/control/challenges" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft size={14} /> Back to Jhooth Chhupao
        </Link>
      </div>

      <div className="product-heading">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="eyebrow">DETERMINISTIC PROOF CORE</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold">
              Z3 SMT SOLVER
            </span>
          </div>
          <h1>Z3 Proof Sandbox</h1>
          <p>
            Evaluate formal constraints with mathematical certainty. Numbers, dates, and budget sums are proven SAT / UNSAT
            from the constraints you enter. This sandbox does not verify an audit automatically.
          </p>
        </div>
      </div>

      <section className="product-panel p-4 mb-4">
        <label htmlFor="proof-goals">Additional comparisons (one per line)</label>
        <textarea id="proof-goals" value={goals.join("\n")} onChange={e => setGoals(e.target.value.split("\n"))} placeholder="share_infra + share_health + share_defense == 100" />
        <label htmlFor="proof-assumptions">Boolean assumptions (one per line)</label>
        <textarea id="proof-assumptions" value={assumptions.join("\n")} onChange={e => setAssumptions(e.target.value.split("\n"))} placeholder="approved and not cancelled" />
        <p>Use numbers, comparisons, +, -, *, and boolean and/or/not. Plain-language claims are not executable constraints.</p>
      </section>
      {solveMutation.error && <p className="form-error" role="alert">{solveMutation.error.message}</p>}
      {/* Preset Buttons */}
      <section className="product-panel mb-6 p-4 rounded-xl border border-border bg-card">
        <span className="text-xs font-semibold text-foreground block mb-2">Formal Proof Presets</span>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => loadPreset("unsat_contract")} className="text-xs">
            <Cpu size={13} className="mr-1.5 text-red-500" />
            ₹50L vs ₹41.6L Conflict (UNSAT)
          </Button>
          <Button size="sm" variant="outline" onClick={() => loadPreset("unsat_percentage")} className="text-xs">
            <Calculator size={13} className="mr-1.5 text-orange-500" />
            40% + 40% + 30% != 100% (UNSAT)
          </Button>
          <Button size="sm" variant="outline" onClick={() => loadPreset("sat_gdp")} className="text-xs">
            <Check size={13} className="mr-1.5 text-emerald-500" />
            GDP & Growth Bounds (SAT)
          </Button>
        </div>
      </section>

      {/* Main Grid: Inputs vs Solver Output */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Constraints Input Form */}
        <div className="lg:col-span-7 space-y-6">
          <section className="product-panel p-5 rounded-xl border border-border bg-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Layers size={16} className="text-primary" />
                <span>Formal Constraints List ({numericConstraints.length})</span>
              </h2>
              <Button size="sm" variant="outline" onClick={addConstraint} className="text-xs h-7">
                <Plus size={12} className="mr-1" /> Add
              </Button>
            </div>

            <div className="space-y-3">
              {numericConstraints.map((c, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-border bg-muted/40 space-y-2 text-xs">
                  <div className="proof-input-row grid grid-cols-12 gap-2">
                    <div className="col-span-5">
                      <input
                        type="text"
                        aria-label={`Variable ${idx + 1}`}
                        placeholder="Variable name"
                        value={c.variable}
                        onChange={e => {
                          const val = e.target.value
                          setNumericConstraints(prev => prev.map((item, i) => i === idx ? { ...item, variable: val } : item))
                        }}
                        className="w-full px-2.5 py-1.5 font-mono text-xs rounded border border-border bg-background"
                      />
                    </div>
                    <div className="col-span-3">
                      <select
                        aria-label={`Comparison ${idx + 1}`}
                        value={c.operator}
                        onChange={e => {
                          const val = e.target.value as any
                          setNumericConstraints(prev => prev.map((item, i) => i === idx ? { ...item, operator: val } : item))
                        }}
                        className="w-full px-2 py-1.5 font-mono text-xs rounded border border-border bg-background"
                      >
                        <option value="eq">== (eq)</option>
                        <option value="neq">!= (neq)</option>
                        <option value="gt">&gt; (gt)</option>
                        <option value="ge">&gt;= (ge)</option>
                        <option value="lt">&lt; (lt)</option>
                        <option value="le">&lt;= (le)</option>
                      </select>
                    </div>
                    <div className="col-span-3">
                      <input
                        type="text"
                        aria-label={`Value ${idx + 1}`}
                        inputMode="decimal"
                        placeholder="Value"
                        value={c.value}
                        onChange={e => {
                          const val = e.target.value
                          setNumericConstraints(prev => prev.map((item, i) => i === idx ? { ...item, value: val } : item))
                        }}
                        className="w-full px-2.5 py-1.5 font-mono text-xs rounded border border-border bg-background"
                      />
                    </div>
                    <div className="col-span-1 flex items-center justify-center">
                      <button
                        type="button"
                        aria-label={`Remove constraint ${idx + 1}`}
                        onClick={() => removeConstraint(idx)}
                        className="text-muted-foreground hover:text-red-500 transition-colors p-1"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                  <input
                    type="text"
                    aria-label={`Reason ${idx + 1}`}
                    placeholder="Rationale / citation (e.g. Demand No. 94)"
                    value={c.reason}
                    onChange={e => {
                      const val = e.target.value
                      setNumericConstraints(prev => prev.map((item, i) => i === idx ? { ...item, reason: val } : item))
                    }}
                    className="w-full px-2.5 py-1 text-[11px] rounded border border-border/70 bg-background text-muted-foreground"
                  />
                </div>
              ))}
            </div>

            <div className="mt-5 pt-4 border-t border-border">
              <LoadingButton
                loading={solveMutation.isPending}
                onClick={() => solveMutation.mutate()}
                className="w-full text-xs font-semibold py-2.5"
              >
                <Play size={13} className="mr-1.5 fill-current" />
                Solve via Z3 Theorem Prover
              </LoadingButton>
            </div>
          </section>
        </div>

        {/* Solver Output Panel */}
        <div className="lg:col-span-5 space-y-6">
          {result ? (
            <section aria-live="polite" className={`product-panel p-6 rounded-xl border bg-card shadow-sm space-y-4 ${
              result.satisfiable === true
                ? "border-emerald-500/40"
                : result.satisfiable === false
                ? "border-red-500/40"
                : "border-amber-500/40"
            }`}>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <div className="flex items-center gap-2">
                  <Terminal size={16} className="text-primary" />
                  <h2 className="text-sm font-semibold text-foreground">Z3 Solver Result</h2>
                </div>
                <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded uppercase ${
                  result.satisfiable === true
                    ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
                    : result.satisfiable === false
                    ? "bg-red-500/10 text-red-600 border border-red-500/20"
                    : "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                }`}>
                  {result.satisfiable === true ? "SAT (Consistent)" : result.satisfiable === false ? "UNSAT (Conflict Proved)" : "UNKNOWN"}
                </span>
              </div>

              {result.satisfiable === false && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-700 dark:text-red-300">
                  <strong>Formal Inconsistency Proved:</strong> The supplied constraint set cannot simultaneously hold true under mathematical logic.
                </div>
              )}

              {result.satisfiable === true && (
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-700 dark:text-emerald-300">
                  <strong>Constraint Model Valid:</strong> A mathematical assignment satisfying all constraints was constructed by Z3.
                </div>
              )}

              {result.model && Object.keys(result.model).length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-foreground mb-1.5">Satisfying Variable Model:</h3>
                  <div className="p-3 rounded-lg bg-muted/60 font-mono text-xs space-y-1">
                    {Object.entries(result.model).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-muted-foreground">{k}:</span>
                        <span className="text-foreground font-semibold">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.error && <p role="alert">{result.error}</p>}
              {result.timed_out && <p role="status">The solver reached its time limit. Simplify your constraints and try again.</p>}
              {result.proof && (
                <div>
                  <h3 className="text-xs font-semibold text-foreground mb-1">Proof Output:</h3>
                  <pre className="p-3 rounded-lg bg-muted/40 font-mono text-[11px] text-muted-foreground whitespace-pre-wrap select-text">
                    {result.proof}
                  </pre>
                </div>
              )}
            </section>
          ) : (
            <div className="p-12 text-center border border-dashed rounded-xl flex flex-col items-center justify-center text-muted-foreground">
              <Calculator size={32} className="mb-2 opacity-50" />
              <h3 className="text-sm font-semibold">Solver Idle</h3>
              <p className="text-xs mt-1">Select a preset or enter constraints to execute formal Z3 verification.</p>
            </div>
          )}
        </div>
      </div>
    </fieldset>
  )
}
