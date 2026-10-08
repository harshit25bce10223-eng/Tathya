import {
  Archive,
  BookOpen,
  ChartNoAxesCombined,
  LayoutDashboard,
  Library,
  ListChecks,
  Upload,
  Users,
} from "lucide-react"
import { isReviewer } from "@/api/audits"
import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [
  { icon: Upload, title: "New audit", path: "/submit" },
  { icon: LayoutDashboard, title: "Control center", path: "/control" },
  { icon: Archive, title: "Audit archive", path: "/control/audits" },
  { icon: Library, title: "Sources & truth", path: "/control/sources" },
  { icon: BookOpen, title: "Trust policies", path: "/control/policies" },
  {
    icon: ChartNoAxesCombined,
    title: "Metrics & drift",
    path: "/control/metrics",
  },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const reviewerItems = isReviewer(currentUser)
    ? [
        ...baseItems,
        { icon: ListChecks, title: "Review queue", path: "/control/queue" },
      ]
    : baseItems

  const items = currentUser?.is_superuser
    ? [
        ...reviewerItems,
        { icon: Users, title: "Governance & admin", path: "/control/admin" },
      ]
    : reviewerItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
