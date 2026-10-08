import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowRight,
  FileText,
  FolderOpen,
  Settings2,
  ShieldCheck,
} from "lucide-react"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({ meta: [{ title: "Overview - Tathya" }] }),
})

function Dashboard() {
  const { user } = useAuth()
  const name = user?.full_name?.trim().split(" ")[0]
  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="eyebrow">WORKSPACE OVERVIEW</span>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Welcome{name ? `, ${name}` : ""}.
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            A clear view of your workspace. A considered next step.
          </p>
        </div>
        <Link
          to="/items"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Open items <ArrowRight size={16} />
        </Link>
      </div>
      <section className="overview-hero">
        <div className="relative z-10 max-w-xl">
          <div className="mb-6 flex items-center gap-2 text-xs font-medium text-teal-200">
            <ShieldCheck size={17} /> THE TATHYA APPROACH
          </div>
          <h2 className="font-editorial text-4xl leading-tight sm:text-5xl">
            Confidence begins
            <br />
            with a checked fact.
          </h2>
          <p className="mt-5 max-w-md text-sm leading-7 text-teal-100/80">
            Keep your information organised, your evidence close, and your
            decisions thoughtful.
          </p>
          <div className="mt-8 flex flex-wrap gap-3 text-xs text-teal-100">
            <span>01 · Claims</span>
            <span className="opacity-40">/</span>
            <span>02 · Evidence</span>
            <span className="opacity-40">/</span>
            <span>03 · Review</span>
          </div>
        </div>
        <div className="hero-seal" aria-hidden="true">
          <ShieldCheck strokeWidth={1} />
          <span>तथ्य</span>
          <small>EVERY FACT, CHECKED</small>
        </div>
      </section>
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Your workspace</h2>
          <span className="text-xs text-muted-foreground">Start here</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Link to="/items" className="workspace-card group">
            <span className="workspace-icon">
              <FolderOpen size={22} />
            </span>
            <div className="mt-6 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Manage items</h3>
              <ArrowRight
                size={18}
                className="text-primary transition-transform group-hover:translate-x-1"
              />
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Create, organise and update the items in your workspace.
            </p>
          </Link>
          <Link to="/settings" className="workspace-card group">
            <span className="workspace-icon amber">
              <Settings2 size={22} />
            </span>
            <div className="mt-6 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Make it yours</h3>
              <ArrowRight
                size={18}
                className="text-primary transition-transform group-hover:translate-x-1"
              />
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Update your profile, password and account preferences.
            </p>
          </Link>
        </div>
      </section>
      <aside className="flex items-start gap-3 rounded-lg border border-border bg-card px-5 py-4 text-sm">
        <FileText size={20} className="mt-0.5 shrink-0 text-primary" />
        <div>
          <p className="font-medium">Built around evidence.</p>
          <p className="mt-1 leading-6 text-muted-foreground">
            Document audits and trust passports are being integrated. Your
            available tools are listed above.
          </p>
        </div>
      </aside>
    </div>
  )
}
