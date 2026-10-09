import { useUnsavedChanges } from "@/hooks/useUnsavedChanges"
import { TrialRunner } from "./TrialRunner"
import { saveCandidate } from "@/api/workspaceDrafts"
import { QueryState } from "@/components/Audits/shared"
import { useState, useEffect } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  FileText,
  ChevronRight,
  Play,
  Sparkles,
  Gavel,
} from "lucide-react"
import { challengeApi, type InjectionCandidate } from "@/api/phase6"
import { auditApi } from "@/api/audits"
import { LoadingButton } from "@/components/ui/loading-button"

export function InjectorWorkspace({ auditId }: { auditId: string }) {
  const [selectedAuditId, setSelectedAuditId] = useState<string>(auditId || "")
  const [selectedDocId, setSelectedDocId] = useState<string>("")
  const [scenarioVersion, setScenarioVersion] = useState<string>("")
  const [originalText, setOriginalText] = useState<string>("")
  const [injectedText, setInjectedText] = useState<string>("")
  const [severity, setSeverity] = useState<"CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NEGLIGIBLE">("CRITICAL")
  const [pattern, setPattern] = useState<string>("numeric_manipulation")
  const [rationale, setRationale] = useState<string>("")
  const [candidate, setCandidate] = useState<InjectionCandidate | null>(null)

  // Fetch audits
  const audits = useQuery({
    queryKey: ["audits"],
    queryFn: auditApi.list,
  })

  const allAudits = audits.data?.data ?? []
  const activeAuditId = selectedAuditId || allAudits[0]?.id || ""

  // Fetch documents for selected audit
  const docsQuery = useQuery({
    queryKey: ["audit-documents", activeAuditId],
    queryFn: () => auditApi.documents(activeAuditId),
    enabled: !!activeAuditId,
  })

  const documents = docsQuery.data?.data ?? []
  const activeDocId = selectedDocId || documents[0]?.id || ""

  // Fetch document text
  const docTextQuery = useQuery({
    queryKey: ["document-text", activeAuditId, activeDocId],
    queryFn: () => auditApi.documentText(activeAuditId, activeDocId),
    enabled: !!activeAuditId && !!activeDocId,
  })

  // Fetch scenarios catalogue
  const scenariosQuery = useQuery({
    queryKey: ["challenge-scenarios"],
    queryFn: challengeApi.listScenarios,
  })

  const scenarios = scenariosQuery.data?.data ?? []

  // Keep the editable copy bound to the currently selected document.
  useEffect(() => {
    setOriginalText(docTextQuery.data?.raw_text ?? "")
    setInjectedText(docTextQuery.data?.raw_text ?? "")
    setCandidate(null)
  }, [activeDocId, docTextQuery.data?.raw_text])

  // Apply scenario modification preset
  const applyScenarioPreset = (version: string) => {
    setScenarioVersion(version)
    const sc = scenarios.find(s => s.version === version)
    if (!sc) return

    setPattern(sc.pattern_type)
    setSeverity(sc.severity as any)
    setRationale(sc.description)

    if (originalText) {
      if (sc.pattern_type === "numeric_manipulation") {
        setInjectedText(
          originalText.replace(/(\$5 trillion|\$4\.27 trillion|41\.6|50|15\.6%|17%|1,500|40%)/i, match => {
            if (match.includes("41.6")) return "50.0"
            if (match.includes("5 trillion")) return "$8 trillion"
            if (match.includes("17%")) return "24%"
            return "99.9%"
          })
        )
      } else if (sc.pattern_type === "claim_negation") {
        setInjectedText(`[ADVERSARIAL OVERRIDE: Factual assertions refuted]\n\n${originalText.replace(/has successfully/i, "has NOT")}`)
      } else if (sc.pattern_type === "omission_induction") {
        setInjectedText(originalText.replace(/(Net 45 \+ 2% late fee|subject to statutory verification|penalty clause)/i, "Net 45"))
      } else {
        setInjectedText(`${originalText}\n\n[INJECTED CLAUSE]: Terms apply without prior ministry authorization.`)
      }
    }
  }

  const injectMutation = useMutation({
    mutationFn: () => {
      if (!injectedText.trim()) throw new Error("Injected text cannot be empty")
      return challengeApi.generateCandidate({
        original_text: originalText || "Sample original text",
        injected_text: injectedText,
        pattern: pattern || "adversarial_injection",
        severity,
        base_document_id: activeDocId || undefined,
        rationale: rationale || "Adversarial simulation",
      })
    },
    onSuccess: (res) => {
      setCandidate(res.candidate)
      saveCandidate(activeAuditId, res.candidate)
    },
  })

  useEffect(() => { setCandidate(null); injectMutation.reset() }, [injectedText, severity, pattern, rationale])
  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("scenario")
    if (requested && originalText && scenarios.length && !scenarioVersion) applyScenarioPreset(requested)
  }, [originalText, scenarios.length, scenarioVersion])

  useUnsavedChanges(injectMutation.isPending || (injectedText !== originalText && !candidate))

  return (
    <fieldset disabled={injectMutation.isPending} className="product-page phase6-page workspace-fields">
      <div className="flex items-center gap-2 mb-4">
        <Link to="/control/challenges" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft size={14} /> Back to Jhooth Chhupao
        </Link>
      </div>

      <div className="product-heading">
        <div>
          <span className="eyebrow">INJECTOR WORKSPACE</span>
          <h1>Jhooth Injector</h1>
          <p>
            Safely inject adversarial variations into document copies and inspect deterministic diffs.
            The generated candidate is a separate copy. Your source document is preserved.
          </p>
        </div>
      </div>

      <QueryState loading={audits.isPending || docsQuery.isFetching || docTextQuery.isFetching || scenariosQuery.isPending}
        error={audits.error || docsQuery.error || docTextQuery.error || scenariosQuery.error}
        retry={() => { audits.refetch(); docsQuery.refetch(); docTextQuery.refetch(); scenariosQuery.refetch() }} />
      {!activeAuditId && <p role="status">Create an audit before choosing a source document. <Link to="/submit">Start an audit</Link></p>}
      {injectMutation.error && <p className="form-error" role="alert">{injectMutation.error.message}</p>}
      {/* Target Audit & Document Selectors */}
      <section className="product-panel mb-6 p-4 rounded-xl border border-border bg-card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-foreground block mb-1.5">Target Audit</label>
            <select
              aria-label="Target Audit"
              value={activeAuditId}
              onChange={e => {
                setSelectedAuditId(e.target.value)
                setSelectedDocId("")
                setCandidate(null)
              }}
              className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground shadow-sm focus:ring-1 focus:ring-primary"
            >
              {allAudits.map(a => (
                <option key={a.id} value={a.id}>
                  {a.title} ({a.status})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1.5">Source Document</label>
            <select
              aria-label="Source Document"
              value={activeDocId}
              onChange={e => {
                setSelectedDocId(e.target.value)
                setCandidate(null)
              }}
              className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background text-foreground shadow-sm focus:ring-1 focus:ring-primary"
            >
              {documents.map(d => (
                <option key={d.id} value={d.id}>
                  {d.filename} (v{d.version_no})
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Main Configuration & Editor Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Configuration & Attack Presets */}
        <div className="lg:col-span-5 space-y-6">
          <section className="product-panel p-5 rounded-xl border border-border bg-card">
            <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Sparkles size={16} className="text-primary" />
              <span>Attack Scenario Preset</span>
            </h2>

            <div className="space-y-2 mb-4">
              {scenarios.map(s => (
                <button
                  key={s.version}
                  type="button"
                  onClick={() => applyScenarioPreset(s.version)}
                  className={`w-full text-left p-3 rounded-lg border text-xs transition-all ${
                    scenarioVersion === s.version
                      ? "border-primary bg-primary/5 shadow-sm font-medium"
                      : "border-border hover:bg-muted/60"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-semibold text-foreground">{s.name}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      {s.severity}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground line-clamp-1">{s.description}</p>
                </button>
              ))}
            </div>

            <div className="space-y-3 pt-3 border-t border-border text-xs">
              <div>
                <label className="text-xs font-medium text-foreground block mb-1">Severity Level</label>
                <select
                  aria-label="Severity level"
                  value={severity}
                  onChange={e => setSeverity(e.target.value as any)}
                  className="w-full px-3 py-1.5 rounded-md border border-border bg-background"
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-foreground block mb-1">Attack Rationale</label>
                <input
                  type="text"
                  aria-label="Attack rationale"
                  value={rationale}
                  onChange={e => setRationale(e.target.value)}
                  placeholder="e.g. Alter contract pricing by 20% to test Z3 solver"
                  className="w-full px-3 py-1.5 rounded-md border border-border bg-background"
                />
              </div>
            </div>

            <div className="mt-5">
              <LoadingButton
                loading={injectMutation.isPending}
                onClick={() => injectMutation.mutate()}
                disabled={!activeDocId || docTextQuery.isFetching || !injectedText.trim() || injectedText === originalText}
                className="w-full text-xs font-semibold py-2.5"
              >
                <Play size={13} className="mr-1.5 fill-current" />
                Generate Candidate & Compute Diff
              </LoadingButton>
              {injectedText === originalText && (
                <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-2 text-center">
                  Modify the candidate text on the right to produce an adversarial diff.
                </p>
              )}
            </div>
          </section>
        </div>

        {/* Right: Side-by-Side Text Editor */}
        <div className="lg:col-span-7 space-y-6">
          <section className="product-panel p-5 rounded-xl border border-border bg-card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <FileText size={16} className="text-muted-foreground" />
                <span>Candidate Text Editor</span>
              </h2>
              <span className="text-[11px] font-mono text-muted-foreground">
                Original Hash: {docTextQuery.data?.text_hash?.slice(0, 12) || "none"}…
              </span>
            </div>

            <textarea
              aria-label="Candidate document text"
              rows={12}
              value={injectedText}
              onChange={e => setInjectedText(e.target.value)}
              className="w-full p-3 font-mono text-xs rounded-lg border border-border bg-muted/40 text-foreground focus:ring-1 focus:ring-primary leading-relaxed"
              placeholder="Load or paste adversarial candidate text here..."
            />

            <div className="flex items-center justify-between text-[11px] text-muted-foreground mt-2">
              <span>Length: {injectedText.length} characters</span>
              <button
                type="button"
                onClick={() => setInjectedText(originalText)}
                className="hover:underline text-primary"
              >
                Reset to original
              </button>
            </div>
          </section>
        </div>
      </div>

      {/* Diff & Candidate Hash Inspection Output */}
      {candidate && (
        <section aria-live="polite" className="product-panel mt-6 p-6 rounded-xl border border-emerald-500/30 bg-card shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-4 border-b border-border">
            <div className="flex items-center gap-2">
              <div className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              <h2 className="text-sm font-semibold text-foreground">Traceable Candidate Generated</h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 font-bold">
                DIFF READY
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/control/judge/$auditId"
                params={{ auditId: activeAuditId }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Gavel size={13} />
                <span>Evaluate with Judge WOW</span>
                <ChevronRight size={13} />
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-muted/60 border border-border">
              <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1">Original Hash (SHA-256)</span>
              <span className="text-foreground break-all">{candidate.original_hash}</span>
            </div>
            <div className="p-3 rounded-lg bg-muted/60 border border-border">
              <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1">Candidate Hash (SHA-256)</span>
              <span className="text-foreground break-all">{candidate.candidate_hash}</span>
            </div>
          </div>

          {/* Unified Diff Box */}
          <div className="rounded-lg border border-border bg-muted/70 overflow-hidden text-xs font-mono">
            <div className="px-3 py-2 bg-muted border-b border-border text-[11px] text-muted-foreground flex justify-between">
              <span>UNIFIED DIFF (--- original +++ candidate)</span>
              <span>{candidate.diff.length} lines</span>
            </div>
            <div className="p-3 max-h-80 overflow-y-auto space-y-0.5 select-text">
              {candidate.diff.map((line, idx) => {
                const isAdd = line.startsWith("+") && !line.startsWith("+++")
                const isDel = line.startsWith("-") && !line.startsWith("---")
                const isHeader = line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++")
                return (
                  <div
                    key={idx}
                    className={`px-2 py-0.5 rounded ${
                      isAdd
                        ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-medium"
                        : isDel
                        ? "bg-red-500/15 text-red-700 dark:text-red-300 font-medium"
                        : isHeader
                        ? "text-blue-600 dark:text-blue-400 font-semibold"
                        : "text-muted-foreground"
                    }`}
                  >
                    {line}
                  </div>
                )
              })}
            </div>
          </div>
        </section>
      )}
      <TrialRunner key={`trial-${activeAuditId}`} auditId={activeAuditId} candidateText={injectedText} />
    </fieldset>
  )
}
