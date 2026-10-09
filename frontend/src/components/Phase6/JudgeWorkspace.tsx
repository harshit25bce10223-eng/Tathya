import { useUnsavedChanges } from "@/hooks/useUnsavedChanges"
import { loadCandidate } from "@/api/workspaceDrafts"
import { QueryState } from "@/components/Audits/shared"
import { useState, useEffect } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  Shield,
  Check,
  FileText,
  Gavel,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react"
import { challengeApi, type AdversarialReview } from "@/api/phase6"
import { auditApi } from "@/api/audits"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"

export function JudgeWorkspace({ auditId }: { auditId: string }) {
  const [selectedAuditId, setSelectedAuditId] = useState<string>(auditId || "")
  const [claimText, setClaimText] = useState<string>(loadCandidate(auditId)?.injected_text.slice(0, 10000) ?? "")
  const [claimCategory, setClaimCategory] = useState<string>("economic")
  const [strictCheck, setStrictCheck] = useState<boolean>(true)
  const [evidenceList, setEvidenceList] = useState<Array<{
    id: string
    quote: string
    location: string
    support_type: string
    score: number
  }>>([])
  const [review, setReview] = useState<AdversarialReview | null>(null)
  const [newQuote, setNewQuote] = useState("")

  const audits = useQuery({
    queryKey: ["audits"],
    queryFn: auditApi.list,
  })

  const allAudits = audits.data?.data ?? []
  const activeAuditId = selectedAuditId || allAudits[0]?.id || ""

  const claimsQuery = useQuery({
    queryKey: ["audit-flags", activeAuditId],
    queryFn: () => auditApi.flags(activeAuditId),
    enabled: !!activeAuditId,
  })

  // Load claim presets from active audit
  const selectAuditFlag = (flag: import("@/api/audits").AuditFlag) => {
    setClaimText(flag.claim_text ?? "")
    setEvidenceList((flag.evidence ?? []).map(ev => ({ id: ev.id, quote: ev.quote, location: ev.location_json, support_type: ev.support_type, score: ev.score })))
    setReview(null)
  }

  const runReviewMutation = useMutation({
    mutationFn: () => challengeApi.runAdversarialReview({
      claim_text: claimText,
      claim_category: claimCategory,
      evidence_list: evidenceList,
      strict_injection_check: strictCheck,
    }),
    onSuccess: (result) => {
      setReview(result.review)
    },
  })

  const addEvidence = () => {
    if (!newQuote.trim()) return
    setEvidenceList([
      ...evidenceList,
      {
        id: crypto.randomUUID(),
        quote: newQuote.trim(),
        location: "User supplied quote; source not independently verified",
        support_type: "unclassified",
        score: 0,
      },
    ])
    setNewQuote("")
  }

  useEffect(() => { setReview(null); runReviewMutation.reset() }, [claimText, evidenceList, claimCategory, strictCheck])
  useEffect(() => { setClaimText(loadCandidate(activeAuditId)?.injected_text.slice(0, 10000) ?? ""); setEvidenceList([]); setReview(null) }, [activeAuditId])

  useUnsavedChanges(runReviewMutation.isPending || (!!claimText.trim() && !review))

  return (
    <fieldset disabled={runReviewMutation.isPending} className="product-page phase6-page workspace-fields">
      <div className="flex items-center gap-2 mb-4">
        <Link to="/control/challenges" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft size={14} /> Back to Jhooth Chhupao
        </Link>
      </div>

      <div className="product-heading">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="eyebrow">PHASE 6 ADVERSARIAL WORKSPACE</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold">
              JUDGE WOW
            </span>
          </div>
          <h1>Judge WOW Adversarial Review</h1>
          <p>
            Evidence-integrity validated adversarial evaluation with strict instruction-injection defense.
          </p>
        </div>
      </div>

      <QueryState loading={audits.isPending || claimsQuery.isFetching} error={audits.error || claimsQuery.error}
        retry={() => { audits.refetch(); claimsQuery.refetch() }} />
      {runReviewMutation.error && <p className="form-error" role="alert">{runReviewMutation.error.message}</p>}
      {/* Audit Selector Strip */}
      <section className="product-panel mb-6 p-4 rounded-xl border border-border bg-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">Target Audit Context</label>
            <select
              value={activeAuditId}
              onChange={e => {
                setSelectedAuditId(e.target.value)
                setReview(null)
              }}
              className="px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-background"
            >
              {allAudits.map(a => (
                <option key={a.id} value={a.id}>{a.title}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
              <input
                type="checkbox"
                checked={strictCheck}
                onChange={e => setStrictCheck(e.target.checked)}
                className="rounded border-border"
              />
              <span>Strict Prompt Injection Defense</span>
            </label>
          </div>
        </div>
      </section>

      {/* Main Review Setup */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Claim & Evidence Setup */}
        <div className="lg:col-span-6 space-y-6">
          <section className="product-panel p-5 rounded-xl border border-border bg-card">
            <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <FileText size={16} className="text-primary" />
              <span>Claim Under Review</span>
            </h2>

            <textarea
              rows={3}
              aria-label="Claim to verify"
              value={claimText}
              onChange={e => setClaimText(e.target.value)}
              className="w-full p-3 text-xs rounded-lg border border-border bg-muted/40 font-mono text-foreground"
              placeholder="Enter assertion to verify..."
            />

            <div className="mt-3 flex items-center gap-3">
              <span className="text-xs text-muted-foreground">Category:</span>
              <select
                aria-label="Claim category"
                value={claimCategory}
                onChange={e => setClaimCategory(e.target.value)}
                className="px-2.5 py-1 text-xs rounded border border-border bg-background"
              >
                <option value="economic">Economic</option>
                <option value="financial">Financial / Pricing</option>
                <option value="governance">Governance</option>
                <option value="infrastructure">Infrastructure</option>
                <option value="security">Security</option>
              </select>
            </div>

            {/* Quick Load from Audit Findings */}
            {claimsQuery.data?.data && claimsQuery.data.data.length > 0 && (
              <div className="mt-4 pt-3 border-t border-border">
                <span className="text-[11px] font-semibold text-muted-foreground block mb-2">
                  Load Finding from Active Audit:
                </span>
                <div className="space-y-1.5 max-h-36 overflow-y-auto">
                  {claimsQuery.data.data.map(f => (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => selectAuditFlag(f)}
                      className="w-full text-left px-2.5 py-1.5 rounded bg-muted/50 hover:bg-muted text-[11px] truncate flex items-center justify-between gap-2 transition-colors"
                    >
                      <span className="truncate">{f.type}: {f.reason}</span>
                      <span className="text-[9px] font-mono px-1 rounded bg-background shrink-0">{f.severity}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Evidence List Box */}
          <section className="product-panel p-5 rounded-xl border border-border bg-card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Shield size={16} className="text-muted-foreground" />
                <span>Evidence supplied for review ({evidenceList.length})</span>
              </h2>
            </div>

            <div className="space-y-2 mb-3">
              {evidenceList.map((ev, i) => (
                <div key={ev.id || i} className="p-2.5 rounded-lg bg-muted/60 border border-border text-xs">
                  <button type="button" aria-label={`Remove evidence ${i + 1}`} onClick={() => setEvidenceList(prev => prev.filter((_, idx) => idx !== i))}>Remove</button>
                  <p className="font-mono text-[11px] text-foreground leading-relaxed italic">"{ev.quote}"</p>
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground mt-1 pt-1 border-t border-border/50">
                    <span>{ev.location}</span>
                    <span className="font-mono">Score: {ev.score}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center gap-2 pt-2 border-t border-border">
              <input
                type="text"
                aria-label="New evidence quote"
                value={newQuote}
                onChange={e => setNewQuote(e.target.value)}
                placeholder="Add citation quote to test against..."
                className="flex-1 px-3 py-1.5 text-xs rounded border border-border bg-background"
                onKeyDown={e => e.key === "Enter" && addEvidence()}
              />
              <Button size="sm" variant="outline" onClick={addEvidence} className="text-xs">
                Add
              </Button>
            </div>

            <div className="mt-5">
              <LoadingButton
                disabled={!claimText.trim() || evidenceList.length === 0}
                loading={runReviewMutation.isPending}
                onClick={() => runReviewMutation.mutate()}
                className="w-full text-xs font-semibold py-2.5"
              >
                <Gavel size={13} className="mr-1.5" />
                Run Judge WOW Adversarial Review
              </LoadingButton>
            </div>
          </section>
        </div>

        {/* Right Column: Review Output & Defense Verdict */}
        <div className="lg:col-span-6 space-y-6">
          {review ? (
            <section aria-live="polite" className="product-panel p-6 rounded-xl border border-primary/30 bg-card shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <div className="flex items-center gap-2">
                  <div className="size-2 rounded-full bg-emerald-500" />
                  <h2 className="text-sm font-semibold text-foreground">Judge WOW Verdict</h2>
                </div>
                <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded uppercase ${
                  review.status === "verified"
                    ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
                    : review.status === "rejected"
                    ? "bg-red-500/10 text-red-600 border border-red-500/20"
                    : "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                }`}>
                  {review.status}
                </span>
              </div>

              {/* Status & Integrity Badges */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-muted/60 border border-border">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Confidence</span>
                  <span className="font-mono text-sm font-bold text-foreground">{(review.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="p-3 rounded-lg bg-muted/60 border border-border">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Evidence Integrity</span>
                  <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <Check size={14} /> {review.evidence_integrity_verified ? "References checked" : "Not verified"}
                  </span>
                </div>
              </div>

              {/* Prompt Injection Scanner Check */}
              <div className={`p-3 rounded-lg border text-xs ${
                review.instruction_injection_detected
                  ? "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              }`}>
                <div className="flex items-center gap-2 font-semibold mb-0.5">
                  {review.instruction_injection_detected ? (
                    <><ShieldAlert size={14} /> Prompt Injection Detected!</>
                  ) : (
                    <><ShieldCheck size={14} /> Prompt Injection Scan: Clean</>
                  )}
                </div>
                <p className="text-[11px] opacity-90">
                  {review.instruction_injection_detected
                    ? `Matched patterns: ${review.injection_patterns.join(", ")}`
                    : "No prompt override directives detected in input documents."}
                </p>
              </div>

              {/* Reasoning */}
              <div>
                <h3 className="text-xs font-semibold text-foreground mb-1">Verification Reason</h3>
                <p className="text-xs text-muted-foreground leading-relaxed p-3 rounded-lg bg-muted/40 font-mono">
                  {review.reason}
                </p>
              </div>

              {/* Structured JSON Contract */}
              <details className="text-xs font-mono pt-2 border-t border-border">
                <summary className="cursor-pointer text-primary hover:underline font-sans font-medium text-[11px]">
                  View Structured Output Contract
                </summary>
                <pre className="mt-2 p-3 rounded bg-muted/80 text-[10px] max-h-48 overflow-y-auto select-text">
                  {JSON.stringify(review, null, 2)}
                </pre>
              </details>
            </section>
          ) : (
            <div className="p-12 text-center border border-dashed rounded-xl flex flex-col items-center justify-center text-muted-foreground">
              <Gavel size={32} className="mb-2 opacity-50" />
              <h3 className="text-sm font-semibold">No Review Executed Yet</h3>
              <p className="text-xs mt-1">Configure your claim and click 'Run Judge WOW' to execute adversarial evaluation.</p>
            </div>
          )}
        </div>
      </div>
    </fieldset>
  )
}