import { useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertCircle, Loader2 } from "lucide-react"
import { useEffect, useRef } from "react"
import { AuditApiError, auditApi, isRunning } from "@/api/audits"
import { Button } from "@/components/ui/button"

export function StatusPill({ status }: { status: string }) {
  const tone = ["completed", "verified", "fixed", "dismissed"].includes(
    status.toLowerCase(),
  )
    ? "positive"
    : ["failed", "critical", "high"].includes(status.toLowerCase())
      ? "danger"
      : "neutral"
  return (
    <span className={`status-pill ${tone}`}>
      <span />
      {status.replace(/_/g, " ")}
    </span>
  )
}
export function QueryState({
  loading,
  error,
  retry,
}: {
  loading: boolean
  error: Error | null
  retry: () => void
}) {
  if (loading)
    return (
      <div className="panel-state" role="status">
        <Loader2 className="animate-spin" size={20} />
        Loading your workspace…
      </div>
    )
  if (!error) return null
  const unavailable =
    error instanceof AuditApiError &&
    error.status === 404 &&
    error.message !== "Audit not found"
  return (
    <div className="panel-state" role="alert">
      <AlertCircle size={24} />
      <h2>
        {unavailable
          ? "Audit service is unavailable"
          : "We couldn’t load this view"}
      </h2>
      <p>
        {unavailable
          ? "Your files and results will appear here when the audit service is connected."
          : error.message}
      </p>
      <Button variant="outline" onClick={retry}>
        Try again
      </Button>
    </div>
  )
}
export function useAudit(id: string) {
  const queryClient = useQueryClient()
  const previousStatus = useRef<string | undefined>(undefined)
  const summary = useQuery({
    queryKey: ["audit", id],
    queryFn: () => auditApi.summary(id),
    refetchInterval: (q) =>
      isRunning(q.state.data?.audit.status ?? "") ? 3000 : false,
  })
  const running = isRunning(summary.data?.audit.status ?? "")
  const status = summary.data?.audit.status
  useEffect(() => {
    if (
      previousStatus.current &&
      isRunning(previousStatus.current) &&
      status &&
      !isRunning(status)
    ) {
      queryClient.invalidateQueries({ queryKey: ["audit-flags", id] })
      queryClient.invalidateQueries({ queryKey: ["audit-documents", id] })
      queryClient.invalidateQueries({ queryKey: ["audit-score", id] })
      queryClient.invalidateQueries({ queryKey: ["source-facts", id] })
      queryClient.invalidateQueries({ queryKey: ["policy-results", id] })
      queryClient.invalidateQueries({ queryKey: ["claim-graph", id] })
    }
    previousStatus.current = status
  }, [status, id, queryClient])
  const flags = useQuery({
    queryKey: ["audit-flags", id],
    queryFn: () => auditApi.flags(id),
    enabled: !!summary.data,
    refetchInterval: running ? 3000 : false,
  })
  const documents = useQuery({
    queryKey: ["audit-documents", id],
    queryFn: () => auditApi.documents(id),
    enabled: !!summary.data,
    refetchInterval: running ? 3000 : false,
  })
  return { summary, flags, documents }
}
