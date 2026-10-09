import { createFileRoute, redirect } from "@tanstack/react-router"
import { UsersService } from "@/client"
import { AdminPage } from "@/components/Admin/AdminPage"

export const Route = createFileRoute("/_layout/admin")({
  component: AdminPage,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Admin - Tathya" }],
  }),
})
