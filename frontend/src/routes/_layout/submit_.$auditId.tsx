import { createFileRoute } from "@tanstack/react-router"
import { AuditResult } from "@/components/Audits/AuditResult"
export const Route = createFileRoute("/_layout/submit_/$auditId")({
  component: Result,
  head: () => ({ meta: [{ title: "Audit result - Tathya" }] }),
})
function Result() {
  const { auditId } = Route.useParams()
  return <AuditResult auditId={auditId} />
}
