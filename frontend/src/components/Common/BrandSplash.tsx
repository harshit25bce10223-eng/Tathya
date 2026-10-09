import logoImage from "@/assets/brand/tathya-logo-v2.png"
import { useEffect, useState } from "react"

const parts = [
  { name: "Verified T mark", clip: "inset(0 72% 0 0)", delay: 0 },
  { name: "Tathya wordmark", clip: "inset(0 0 24% 28%)", delay: 300 },
  { name: "Every fact, checked", clip: "inset(74% 0 0 28%)", delay: 600 },
]
export function BrandSplash({ preview = false }: { preview?: boolean }) {
  const [replay, setReplay] = useState(0)
  const [visible, setVisible] = useState(
    () => preview || (window.location.pathname !== "/splash" && !sessionStorage.getItem("tathya-splash-seen")),
  )
  useEffect(() => {
    if (preview || !visible) return
    sessionStorage.setItem("tathya-splash-seen", "1")
    const surface = document.querySelector("#application-surface") as HTMLElement | null
    if (surface) surface.inert = true
    const timer = setTimeout(
      () => {
        setVisible(false)
      },
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? 100
        : 2600,
    )
    return () => { clearTimeout(timer); if (surface) surface.inert = false }
  }, [preview, visible])
  if (!visible) return null
  return (
    <div
      className={`brand-splash ${preview ? "splash-preview" : ""}`}
      role="status"
      aria-label="Welcome to Tathya"
    >
      {!preview && <button autoFocus type="button" className="splash-skip" onClick={() => setVisible(false)}>Skip introduction</button>}
      <div className="splash-ambient" aria-hidden="true" />
      <div className="splash-art" key={replay} aria-hidden="true">
        {parts.map((part) => (
          <img
            key={part.name}
            alt=""
            src={logoImage}
            className="splash-part"
            style={{
              clipPath: part.clip,
              animationDelay: `${part.delay}ms`,
            }}
          />
        ))}
        <img
          className="splash-complete"
          src={logoImage}
          alt=""
        />
      </div>
      <span className="splash-caption">सही जानकारी · भरोसे के साथ</span>
      <span className="splash-signature">
        AGNITIA <span>·</span> THE FOUNDATION OF TRUST
      </span>
      {preview && (
        <div className="splash-actions">
          <button
            type="button"
            className="back-link"
            onClick={() => setReplay((value) => value + 1)}
          >
            Replay animation
          </button>
          <a className="primary-link" href="/login">
            Continue to sign in
          </a>
        </div>
      )}
    </div>
  )
}
