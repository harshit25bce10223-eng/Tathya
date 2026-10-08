import { createFileRoute } from "@tanstack/react-router"
import { MetricsPage } from "@/components/Audits/ControlPages"
export const Route = createFileRoute("/_layout/control_/metrics")({
  component: MetricsPage,
  head: () => ({ meta: [{ title: "Metrics - Tathya" }] }),
})
