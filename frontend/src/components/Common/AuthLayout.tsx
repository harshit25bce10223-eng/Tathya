import { Check, ShieldCheck } from "lucide-react"
import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth-layout">
      <aside className="auth-story">
        <Logo className="h-9" asLink={false} />
        <div className="auth-story-body">
          <div className="story-label">
            <span /> CLARITY. EVIDENCE. TRUST.
          </div>
          <h2 className="font-editorial">
            Every fact,
            <br />
            <em>checked.</em>
          </h2>
          <p className="story-description">
            For the decisions that matter,
            <br />
            start with the facts that stand up.
          </p>
          <div className="evidence-note">
            <div className="flex items-center justify-between">
              <span className="text-xs tracking-widest">
                THE VERIFICATION JOURNEY
              </span>
              <ShieldCheck size={20} />
            </div>
            <div className="mt-6 space-y-4">
              {[
                "Bring your documents together",
                "Trace claims back to evidence",
                "Review with confidence",
              ].map((text, i) => (
                <div key={text} className="flex items-center gap-3">
                  <span className="note-step">{i + 1}</span>
                  <span className="text-sm">{text}</span>
                  <Check size={14} className="ml-auto opacity-50" />
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="story-footer">
          <span>तथ्य / The foundation of trust.</span>
          <span>AGNITIA</span>
        </div>
      </aside>
      <section className="auth-form-side">
        <header className="flex items-center justify-between">
          <Logo className="h-8 lg:hidden" asLink={false} />
          <div className="ml-auto">
            <Appearance />
          </div>
        </header>
        <div className="flex flex-1 items-center justify-center py-12">
          <div className="w-full max-w-sm">{children}</div>
        </div>
        <footer className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <ShieldCheck size={14} /> Tathya · Every fact, checked.
        </footer>
      </section>
    </div>
  )
}
