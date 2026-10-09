import { useQuery } from "@tanstack/react-query"
import { policyApi } from "@/api/policies"
import { PolicyDetails } from "./PolicyStudio"
import { QueryState, StatusPill } from "./shared"

export function PolicyAssessment({auditId, completed}: {auditId: string; completed: boolean}) {
  const results = useQuery({queryKey: ["policy-results", auditId], queryFn: () => policyApi.results(auditId), enabled: completed})
  if (!completed) return null
  return <section className="product-panel policy-assessment"><div className="panel-heading"><div><h2>Business policy checks</h2><p>Recorded rules, required values and supporting document quotes.</p></div>{results.data && <StatusPill status={results.data.stale ? "Re-audit required" : "Recorded results"} />}</div><QueryState loading={results.isPending} error={results.error} retry={() => results.refetch()} />
    {results.data?.stale && <p role="status" className="control-note">Policy settings or documents changed since these checks. Re-audit current documents to apply the current rules. Unchecked policy changes cannot receive a complete trust rating.</p>}
    {results.data && !results.data.evaluations.length && <p>{results.data.active_policy_count ? `${results.data.active_policy_count} active policies have not been checked in this audit yet.` : "No typed business policies were applied. Source verification and other recorded findings still determine this score."}</p>}
    {results.data?.evaluations.map(r => <article key={r.policy_id} className="policy-recorded-result"><h3>{r.policy_name} · version {r.policy_version}</h3><p>Checks {r.target === "claim" ? "AI document claims" : "source records"}.</p><PolicyDetails result={r} /></article>)}
  </section>
}
