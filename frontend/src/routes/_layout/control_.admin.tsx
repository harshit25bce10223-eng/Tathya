import { createFileRoute, redirect } from "@tanstack/react-router"
import { UsersService } from "@/client"
import { Admin } from "./admin"
export const Route = createFileRoute("/_layout/control_/admin")({
  component: Admin,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) throw redirect({ to: "/control" })
  },
  head: () => ({ meta: [{ title: "Governance - Tathya" }] }),
})
