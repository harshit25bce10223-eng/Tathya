import { useEffect, useState } from "react"

const parts = [
  {
    name: "Golden mandala",
    clip: "polygon(evenodd,17% 10%,82% 10%,82% 60%,17% 60%,17% 10%,23% 20%,23% 52%,74% 52%,74% 20%,23% 20%)",
    delay: 0,
  },
  {
    name: "T monogram",
    clip: "polygon(18% 24%,66% 24%,66% 34%,50% 34%,50% 59%,38% 59%,38% 29%,18% 36%)",
    delay: 160,
  },
  {
    name: "Document",
    clip: "polygon(evenodd,50% 33%,65% 33%,70% 40%,70% 59%,50% 59%,50% 33%,58% 44%,58% 53%,67% 53%,67% 44%,58% 44%)",
    delay: 350,
  },
  {
    name: "Checkmark",
    clip: "polygon(58% 44%,67% 44%,67% 53%,58% 53%)",
    delay: 600,
  },
  {
    name: "Peacock feather",
    clip: "polygon(65% 36%,65% 13%,85% 3%,85% 27%)",
    delay: 780,
  },
  {
    name: "Golden orbit",
    clip: "polygon(23% 45%,39% 39%,39% 44%,26% 52%,39% 57%,55% 57%,68% 50%,73% 39%,67% 36%,72% 33%,77% 38%,73% 49%,60% 57%,40% 60%,24% 55%)",
    delay: 1000,
  },
  { name: "Wordmark", clip: "inset(57% 6% 21% 6%)", delay: 1200 },
  { name: "Hindi tagline", clip: "inset(78% 6% 15% 6%)", delay: 1400 },
  { name: "Verification tagline", clip: "inset(85% 6% 8% 6%)", delay: 1550 },
]
export function BrandSplash({ preview = false }: { preview?: boolean }) {
  const [replay, setReplay] = useState(0)
  const [visible, setVisible] = useState(
    () =>
      preview ||
      (window.location.pathname !== "/splash" &&
        !sessionStorage.getItem("tathya-splash-seen")),
  )
  useEffect(() => {
    if (preview || !visible) return
    const timer = setTimeout(
      () => {
        sessionStorage.setItem("tathya-splash-seen", "1")
        setVisible(false)
      },
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? 100
        : 2600,
    )
    return () => clearTimeout(timer)
  }, [preview, visible])
  if (!visible) return null
  return (
    <div
      className={`brand-splash ${preview ? "splash-preview" : ""}`}
      role="status"
      aria-label="Welcome to Tathya"
    >
      <div className="splash-ambient" aria-hidden="true" />
      <div className="splash-art" key={replay} aria-hidden="true">
        <svg aria-hidden="true" className="splash-orbit" viewBox="0 0 500 500">
          <circle cx="250" cy="250" r="238" />
          <circle className="orbit-trace" cx="250" cy="250" r="238" />
        </svg>
        {parts.map((part) => (
          <img
            key={part.name}
            alt=""
            src="/assets/images/tathya-logo.png"
            className="splash-part"
            style={{
              clipPath: part.clip,
              animationDelay: `${part.delay}ms`,
              filter:
                part.name === "Golden mandala"
                  ? "url(#brand-gold)"
                  : "url(#brand-paper)",
            }}
          />
        ))}
        <img
          className="splash-complete"
          src="/assets/images/tathya-logo.png"
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
