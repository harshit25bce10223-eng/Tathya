import { createFileRoute } from "@tanstack/react-router"
import { JudgeWorkspace } from "@/components/Phase6/JudgeWorkspace"
export const Route = createFileRoute("/_layout/control_/judge/$auditId")({
  component: () => {
    const { auditId } = Route.useParams()
    return <JudgeWorkspace auditId={auditId} />
  },
  head: () => ({ meta: [{ title: "Judge WOW - Tathya" }] }),
})