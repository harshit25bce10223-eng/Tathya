import { createFileRoute } from "@tanstack/react-router"
import { PoliciesPage } from "@/components/Audits/ControlPages"
export const Route = createFileRoute("/_layout/control_/policies")({
  component: PoliciesPage,
  head: () => ({ meta: [{ title: "Policies - Tathya" }] }),
})
