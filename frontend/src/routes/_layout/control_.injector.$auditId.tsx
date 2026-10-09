import { createFileRoute } from "@tanstack/react-router"
import { InjectorWorkspace } from "@/components/Phase6/InjectorWorkspace"
export const Route = createFileRoute("/_layout/control_/injector/$auditId")({
  validateSearch: (search: Record<string, unknown>) => ({ scenario: typeof search.scenario === "string" ? search.scenario : "" }),
  component: () => {
    const { auditId } = Route.useParams()
    return <InjectorWorkspace auditId={auditId} />
  },
  head: () => ({ meta: [{ title: "Jhooth Injector - Tathya" }] }),
})