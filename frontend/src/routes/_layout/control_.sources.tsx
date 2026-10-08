import { createFileRoute } from "@tanstack/react-router"
import { SourcesPage } from "@/components/Audits/ControlPages"
export const Route = createFileRoute("/_layout/control_/sources")({
  component: SourcesPage,
  head: () => ({ meta: [{ title: "Sources - Tathya" }] }),
})
