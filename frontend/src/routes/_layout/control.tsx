import { createFileRoute } from "@tanstack/react-router"
import { AuditList } from "@/components/Audits/AuditList"
export const Route = createFileRoute("/_layout/control")({
  component: () => <AuditList />,
  head: () => ({ meta: [{ title: "Control center - Tathya" }] }),
})
