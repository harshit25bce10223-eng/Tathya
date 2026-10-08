import { createFileRoute } from "@tanstack/react-router"
import { AuditList } from "@/components/Audits/AuditList"
import { ReviewerGate } from "@/components/Audits/ReviewerGate"
export const Route = createFileRoute("/_layout/control_/queue")({
  component: () => (
    <ReviewerGate>
      <AuditList queue />
    </ReviewerGate>
  ),
  head: () => ({ meta: [{ title: "Review queue - Tathya" }] }),
})
