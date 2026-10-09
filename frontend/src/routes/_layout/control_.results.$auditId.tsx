import { createFileRoute } from "@tanstack/react-router"
import { ChallengeResultsDashboard } from "@/components/Phase6/ChallengeResults"
export const Route = createFileRoute("/_layout/control_/results/$auditId")({
  component: () => <ChallengeResultsDashboard />,
  head: () => ({ meta: [{ title: "Challenge Results - Tathya" }] }),
})