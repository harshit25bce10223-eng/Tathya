import { createFileRoute } from "@tanstack/react-router"
import { Investigation } from "@/components/Audits/Investigation"
import { ReviewerGate } from "@/components/Audits/ReviewerGate"
export const Route = createFileRoute("/_layout/control_/workspace/$auditId")({
  component: Workspace,
  head: () => ({ meta: [{ title: "Investigation - Tathya" }] }),
})
function Workspace() {
  const { auditId } = Route.useParams()
  return (
    <ReviewerGate>
      <Investigation auditId={auditId} />
    </ReviewerGate>
  )
}
