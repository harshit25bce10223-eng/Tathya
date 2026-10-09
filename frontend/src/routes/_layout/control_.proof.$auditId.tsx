import { createFileRoute } from "@tanstack/react-router"
import { ProofSandbox } from "@/components/Phase6/ProofSandbox"
export const Route = createFileRoute("/_layout/control_/proof/$auditId")({
  component: () => {
    const { auditId } = Route.useParams()
    return <ProofSandbox auditId={auditId} />
  },
  head: () => ({ meta: [{ title: "Proof Sandbox - Tathya" }] }),
})